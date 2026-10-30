"""The SVG renderer draws any figure specification as a standalone, deterministic document."""
import html
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import svg  # noqa: E402

NS = '{http://www.w3.org/2000/svg}'


def spec(**axes):
    s = dict(id='chart-test', h=240, ml=[40, 50], mr=[14, 50], mt=24, mb=42,
             X=dict(lo=1, hi=100, log=True, ticks=[[1, '1'], [10, '10'], [100, '100']], title='window, w = W/τ'),
             Y=dict(lo=0, hi=1, ticks=[[0, '0'], [0.5, '0.5'], [1, '1.0']], title='Φ(w) ≥ 0 & < e'),
             els=[dict(t='hband', y0=0.8, y1=1, c='a'), dict(t='rect', x0=2, x1=5, y0=0, y1=1, c='c', al=0.1),
                  dict(t='vline', x=10, c='ink', dash=True), dict(t='hline', y=0.5, c='g', w=1.5),
                  dict(t='band', pts=[[1, 0.1, 0.3], [100, 0.2, 0.6]], c='b', edge=True),
                  dict(t='line', pts=[[1, 0.2], [10, 0.5], [100, 0.9]], c='b', mk=3, open=True),
                  dict(t='pt', x=10, y=0.5), dict(t='pt', x=20, y=0.5, open=True, c='d'),
                  dict(t='txt', x=10, y=0.5, s='label <one>', n='short', al='left', bl='top', b=True)])
    s.update(axes)
    return svg.Figure('test', s, 'aria text', 'Pods ordered after a 3x step, on a doubling scale. The rest of the caption.')


class SvgTest(unittest.TestCase):

    def test_wellformed_with_title_and_desc(self):
        root = ET.fromstring(svg.render(spec()))
        self.assertEqual(root.tag, NS + 'svg')
        self.assertEqual(root.find(NS + 'title').text, 'Pods ordered after a 3x step, on a doubling scale')
        self.assertEqual(root.find(NS + 'desc').text, 'aria text')

    def test_every_element_type_is_drawn(self):
        out = svg.render(spec())
        self.assertIn(html.escape('label <one>', quote=False), out)
        self.assertNotIn('short', out)                        # narrow labels are for the canvas only
        self.assertEqual(out.count('<circle'), 5)             # three markers, two points

    def test_both_palettes_and_an_opaque_background(self):
        out = svg.render(spec())
        self.assertIn('prefers-color-scheme: dark', out)
        self.assertIn('#1565c0', out)
        self.assertIn('#8ab4f8', out)
        self.assertIn('class="f-bg"', out)

    def test_deterministic(self):
        self.assertEqual(svg.render(spec()), svg.render(spec()))

    def test_log_axis_position(self):
        out = svg.render(spec())
        circles = list(ET.fromstring(out).iter(NS + 'circle'))
        # plot from x = 50 to 700 - 50 = 650; x = 10 on a 1..100 log axis is the middle: 350
        self.assertEqual([c.get('cx') for c in circles if c.get('r') == '4'][0], '350.00')

    def test_text_baselines_are_arithmetic(self):
        out = svg.render(spec())
        self.assertNotIn('dominant-baseline', out)
        t = [t for t in ET.fromstring(out).iter(NS + 'text') if t.text == 'label <one>'][0]
        # anchor y = 24 + 174 * (1 - 0.5) = 111, top baseline +0.8 em at 11 px
        self.assertEqual(float(t.get('y')), 111 + 8.8)

    def test_utf8_round_trip(self):
        out = svg.render(spec())
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'f.svg')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(out)
            with open(path, 'rb') as f:
                self.assertEqual(f.read().decode('utf-8'), out)
        self.assertIn('Φ(w) ≥ 0 &amp; &lt; e', out)

    def test_unknown_element_type_is_an_error(self):
        bad = spec()
        bad.spec['els'].append(dict(t='arrow'))
        with self.assertRaises(ValueError):
            svg.render(bad)


if __name__ == '__main__':
    unittest.main()
