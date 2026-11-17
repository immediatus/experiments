# The environment every check in this repository runs in: the Python CI lints with, the pinned lint
# tool, Java and TLC for the TLA+ specifications, and the .NET SDK and P for the P models. Running an
# experiment needs only Python; the rest is for the checks that would otherwise be skipped.
FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

# Java for TLC; ICU for the .NET runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless libicu72 \
    && rm -rf /var/lib/apt/lists/*

# TLC: tla2tools.jar of the release the specifications were checked with, pinned by checksum.
RUN mkdir -p /opt/tla \
    && curl -fsSL "https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar" -o /opt/tla/tla2tools.jar \
    && echo "e1f11b75c4b5bc4478ba0ac5cb6ae28e40a01b0016bc33e0aa97da22dfdbcd7f  /opt/tla/tla2tools.jar" | sha256sum -c -
ENV TLA2TOOLS=/opt/tla/tla2tools.jar

# .NET 8, the runtime P 3.1.0 targets.
ENV DOTNET_ROOT=/usr/share/dotnet \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1
RUN curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && bash /tmp/dotnet-install.sh --channel 8.0 --install-dir "$DOTNET_ROOT" \
    && ln -s "$DOTNET_ROOT/dotnet" /usr/local/bin/dotnet \
    && rm /tmp/dotnet-install.sh

# P, the version the models were checked with, installed where every user finds it.
RUN dotnet tool install P --version 3.1.0 --tool-path /opt/p \
    && ln -s /opt/p/p /usr/local/bin/p
