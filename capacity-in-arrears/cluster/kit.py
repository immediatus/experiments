"""Cluster experiment kit. Standard library only. NOT yet run on a real cluster.

Three experiments, one manifest command each:

  python3 kit.py manifests [--start-delay 90] [--target 50] [--max 50]
                                   [--max-queue-s 0] > exp.yaml          # CPU HPA (Parts 1, 3, 4)
  python3 kit.py signals --signal first|ingress|pair > exp.yaml  # KEDA on demand rates (Part 3 F3, F4)
  python3 kit.py queue --delay 60 --window 300 > exp.yaml        # KEDA on a backlog (Part 2)
  python3 kit.py record --deploy hp --hpa hp --out hpa.csv       # polls kubectl every 5 s

Cluster setup on kind (needs docker, kind v0.30.0, kubectl, helm on your machine). Versions are
pinned to the series' specimen: Kubernetes v1.34.0, metrics-server v0.8.1, KEDA 2.19.0. The queue runs
need up to 100 consumer pods on one node, above kind's default of 110 pods per node once
system pods are counted, so create the cluster with a higher limit:

  cat > kind.yaml <<'K'
  kind: Cluster
  apiVersion: kind.x-k8s.io/v1alpha4
  nodes:
  - role: control-plane
    kubeadmConfigPatches:
    - |
      kind: KubeletConfiguration
      maxPods: 250
  K
  kind create cluster --config kind.yaml \
    --image kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a
  kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.8.1/components.yaml
  kubectl -n kube-system patch deploy metrics-server --type=json \
    -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
  helm repo add kedacore https://kedacore.github.io/charts && helm repo update
  helm install keda kedacore/keda --namespace keda --create-namespace --version 2.19.0
  kubectl create configmap hp-server --from-file=server.py --from-file=meter.py \
    --from-file=broker.py --from-file=consumer.py
  NODE=$(docker inspect -f '{{.NetworkSettings.Networks.kind.IPAddress}}' kind-control-plane)

CPU runs (Parts 1, 3 F1-F2, 4):
  python3 kit.py manifests > exp.yaml && kubectl apply -f exp.yaml
  python3 kit.py record --deploy hp --hpa hp --out hpa.csv &
  python3 loadgen.py $NODE 30080 --rate 20 --spike 5 --spike-start 120 --spike-len 300 \
          --timeout 10 --retries 2 --duration 3600 --out load.csv

Signal runs (Part 3 F3 and F4). The load generator reports its counts to the meter, and
KEDA scales the service on the meter's first-attempt rate, ingress rate, or both:
  python3 kit.py signals --signal first > exp.yaml && kubectl apply -f exp.yaml
  python3 kit.py record --deploy hp --hpa keda-hpa-hp --out hpa.csv &
  python3 loadgen.py $NODE 30080 --rate 20 --spike 5 --spike-start 120 --spike-len 7200 \
          --timeout 10 --retries 2 --duration 7320 --meter $NODE:30081 --out load.csv

Queue runs (Part 2). The broker generates demand itself, 50 messages a second stepping to
200 at 600 s; each consumer takes 10 a second after a 90 s start delay, so 20 pods are
needed. The threshold is set from the standing delay: T = delay x 10 messages per pod.
  python3 kit.py queue --delay 60 --window 300 > exp.yaml && kubectl apply -f exp.yaml
  python3 kit.py record --deploy consumer --hpa keda-hpa-consumer \
          --metrics http://$NODE:30090/metrics --out queue.csv
Run each queue configuration for at least five hours and read the last hour; the model's
predictions are for the last hour of a 20 h run. Delete everything between runs
(kubectl delete -f exp.yaml) so the broker restarts at its equilibrium backlog.

kind has no cluster autoscaler, so provisioning dead time is emulated by START_DELAY
before the pod listens or consumes. Sized for a 16-core node: each service pod requests and
is limited to 250m and one request costs 25 ms of CPU, so one pod serves 10 req/s. Four pods
at a 50% target carry 20 req/s, and the replica ceiling of 50 is 12.5 cores of pods. With that
ceiling, overshoot is observable up to a 5x step (20 pods needed); a 10x step needs 40
pods and its predicted overshoot would be clipped at 50. Consumers sleep rather than burn
CPU, so 100 of them fit on the same node. Note: kubectl port-forward pins traffic to one
pod; use the NodePort for load that must spread across pods.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request

SERVICE = """apiVersion: apps/v1
kind: Deployment
metadata: {{name: hp}}
spec:
  replicas: {min}
  selector: {{matchLabels: {{app: hp}}}}
  template:
    metadata: {{labels: {{app: hp}}}}
    spec:
      terminationGracePeriodSeconds: 1
      containers:
      - name: hp
        image: python:3.12-alpine
        command: ["python3", "/app/server.py"]
        env:
        - {{name: WORK_MS, value: "{work_ms}"}}
        - {{name: START_DELAY, value: "{start_delay}"}}
        - {{name: MAX_QUEUE_S, value: "{max_queue_s}"}}
        ports: [{{containerPort: 8080}}]
        readinessProbe: {{tcpSocket: {{port: 8080}}, periodSeconds: 2, failureThreshold: 30}}
        resources:
          requests: {{cpu: {request}m}}
          limits: {{cpu: {limit}m}}
        volumeMounts: [{{name: app, mountPath: /app}}]
      volumes: [{{name: app, configMap: {{name: hp-server}}}}]
---
apiVersion: v1
kind: Service
metadata: {{name: hp}}
spec:
  type: NodePort
  selector: {{app: hp}}
  ports: [{{port: 8080, targetPort: 8080, nodePort: 30080}}]
"""

CPU_HPA = """---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: {{name: hp}}
spec:
  scaleTargetRef: {{apiVersion: apps/v1, kind: Deployment, name: hp}}
  minReplicas: {min}
  maxReplicas: {max}
  metrics:
  - type: Resource
    resource: {{name: cpu, target: {{type: Utilization, averageUtilization: {target}}}}}
"""

METER = """---
apiVersion: apps/v1
kind: Deployment
metadata: {name: meter}
spec:
  replicas: 1
  selector: {matchLabels: {app: meter}}
  template:
    metadata: {labels: {app: meter}}
    spec:
      containers:
      - name: meter
        image: python:3.12-alpine
        command: ["python3", "/app/meter.py"]
        ports: [{containerPort: 8081}]
        resources: {requests: {cpu: 100m}}
        volumeMounts: [{name: app, mountPath: /app}]
      volumes: [{name: app, configMap: {name: hp-server}}]
---
apiVersion: v1
kind: Service
metadata: {name: meter}
spec:
  type: NodePort
  selector: {app: meter}
  ports: [{port: 8081, targetPort: 8081, nodePort: 30081}]
"""

TRIGGER = """  - type: metrics-api
    metricType: AverageValue
    metadata:
      url: "http://meter.{ns}.svc.cluster.local:8081/metrics"
      format: json
      valueLocation: "{loc}"
      targetValue: "{value}"
"""

SCALED_HP = """---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata: {{name: hp}}
spec:
  scaleTargetRef: {{name: hp}}
  pollingInterval: 15
  minReplicaCount: {min}
  maxReplicaCount: {max}
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown: {{stabilizationWindowSeconds: 300}}
  triggers:
"""

QUEUE = """apiVersion: apps/v1
kind: Deployment
metadata: {{name: broker}}
spec:
  replicas: 1
  selector: {{matchLabels: {{app: broker}}}}
  template:
    metadata: {{labels: {{app: broker}}}}
    spec:
      containers:
      - name: broker
        image: python:3.12-alpine
        command: ["python3", "/app/broker.py"]
        env:
        - {{name: RATE0, value: "{rate0}"}}
        - {{name: RATE1, value: "{rate1}"}}
        - {{name: STEP_AT, value: "{step_at}"}}
        - {{name: START_BACKLOG, value: "{start_backlog}"}}
        ports: [{{containerPort: 8090}}]
        resources: {{requests: {{cpu: 200m}}}}
        volumeMounts: [{{name: app, mountPath: /app}}]
      volumes: [{{name: app, configMap: {{name: hp-server}}}}]
---
apiVersion: v1
kind: Service
metadata: {{name: broker}}
spec:
  type: NodePort
  selector: {{app: broker}}
  ports: [{{port: 8090, targetPort: 8090, nodePort: 30090}}]
---
apiVersion: apps/v1
kind: Deployment
metadata: {{name: consumer}}
spec:
  replicas: {start_pods}
  selector: {{matchLabels: {{app: consumer}}}}
  template:
    metadata: {{labels: {{app: consumer}}}}
    spec:
      terminationGracePeriodSeconds: 1
      containers:
      - name: consumer
        image: python:3.12-alpine
        command: ["python3", "/app/consumer.py"]
        env:
        - {{name: BROKER, value: "http://broker.{ns}.svc.cluster.local:8090"}}
        - {{name: RATE, value: "{rate}"}}
        - {{name: START_DELAY, value: "{start_delay}"}}
        resources: {{requests: {{cpu: 10m, memory: 32Mi}}}}
        volumeMounts: [{{name: app, mountPath: /app}}]
      volumes: [{{name: app, configMap: {{name: hp-server}}}}]
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata: {{name: consumer}}
spec:
  scaleTargetRef: {{name: consumer}}
  pollingInterval: 15
  minReplicaCount: 1
  maxReplicaCount: {max}
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown: {{stabilizationWindowSeconds: {window}}}
  triggers:
  - type: metrics-api
    metricType: AverageValue
    metadata:
      url: "http://broker.{ns}.svc.cluster.local:8090/metrics"
      format: json
      valueLocation: "backlog"
      targetValue: "{threshold}"
"""


def service(a):
    return SERVICE.format(start_delay=a.start_delay, min=a.min, request=a.request_millicores,
                          limit=a.limit_millicores or a.request_millicores, work_ms=a.work_ms, max_queue_s=a.max_queue_s)


def signals(a):
    """KEDA ScaledObject on the meter's rates. The per-pod target is the target share of one
    pod's rate: a pod limited to L millicores serves L / WORK_MS requests a second at full use
    (250m and 25 ms give 10), times target / 100. With two triggers the HPA takes the larger
    recommendation."""
    per_pod = (a.limit_millicores or a.request_millicores) / a.work_ms * a.target / 100.0
    locs = {'first': ['first'], 'ingress': ['ingress'], 'pair': ['first', 'ingress']}[a.signal]
    return (service(a) + METER + SCALED_HP.format(min=a.min, max=a.max)
            + ''.join(TRIGGER.format(loc=loc, value='%g' % per_pod, ns=a.namespace) for loc in locs))


def queue(a):
    """Threshold from the standing delay (Definition 4): T = delay x per-pod rate. The broker
    starts at the equilibrium backlog T x RATE0 / c with RATE0 / c pods, as the model does."""
    threshold = round(a.delay * a.rate)
    return QUEUE.format(rate0=a.rate0, rate1=a.rate1, step_at=a.step_at, start_backlog=round(threshold * a.rate0 / a.rate),
                        start_pods=max(1, round(a.rate0 / a.rate)), rate=a.rate, start_delay=a.start_delay,
                        max=a.max, window=a.window, threshold=threshold, ns=a.namespace)


def record(a):
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('t,spec_replicas,ready_replicas,hpa_current,hpa_desired,metric,source\n')
        t0 = time.time()
        while True:
            try:
                d = json.loads(subprocess.check_output(['kubectl', '-n', a.namespace, 'get', 'deploy', a.deploy, '-o', 'json']))
                h = json.loads(subprocess.check_output(['kubectl', '-n', a.namespace, 'get', 'hpa', a.hpa, '-o', 'json']))
                metric = []
                for m in h.get('status', {}).get('currentMetrics') or []:
                    cur = (m.get('resource') or m.get('external') or {}).get('current', {})
                    metric.append(str(cur.get('averageUtilization', cur.get('averageValue', ''))))
                src = ''
                if a.metrics:
                    src = urllib.request.urlopen(a.metrics, timeout=2).read().decode().replace(',', ';')
                f.write('%d,%s,%s,%s,%s,%s,%s\n' % (time.time() - t0, d['spec'].get('replicas'), d['status'].get('readyReplicas', 0),
                                                    h['status'].get('currentReplicas'), h['status'].get('desiredReplicas'),
                                                    '|'.join(metric), src))
                f.flush()
            except Exception as e:
                print('poll failed:', e, file=sys.stderr)
            time.sleep(5)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('cmd', choices=['manifests', 'signals', 'queue', 'record'])
    p.add_argument('--start-delay', type=int, default=90)
    p.add_argument('--target', type=int, default=50)
    p.add_argument('--max', type=int, default=None, help='replica ceiling; default 50, or 100 for queue')
    p.add_argument('--min', type=int, default=4)
    p.add_argument('--request-millicores', type=int, default=250)
    p.add_argument('--work-ms', type=int, default=25)
    p.add_argument('--limit-millicores', type=int, default=0, help='0 means equal to the request')
    p.add_argument('--max-queue-s', type=float, default=0)
    p.add_argument('--signal', choices=['first', 'ingress', 'pair'], default='first')
    p.add_argument('--delay', type=float, default=60, help='queue: standing delay T/c in seconds')
    p.add_argument('--window', type=int, default=300, help='queue: scale-down stabilization window in seconds')
    p.add_argument('--rate', type=int, default=10, help='queue: messages a second per consumer pod')
    p.add_argument('--rate0', type=float, default=50)
    p.add_argument('--rate1', type=float, default=200)
    p.add_argument('--step-at', type=float, default=600)
    p.add_argument('--deploy', default='hp')
    p.add_argument('--hpa', default='hp')
    p.add_argument('--metrics', default='', help='URL whose JSON is logged with each row')
    p.add_argument('--namespace', default='default', help='namespace the manifests are applied in (service DNS names use it)')
    p.add_argument('--out', default='hpa.csv')
    a = p.parse_args()
    if a.max is None:
        a.max = 100 if a.cmd == 'queue' else 50
    if a.cmd == 'manifests':
        print(service(a) + CPU_HPA.format(target=a.target, max=a.max, min=a.min))
    elif a.cmd == 'signals':
        print(signals(a))
    elif a.cmd == 'queue':
        print(queue(a))
    else:
        record(a)
