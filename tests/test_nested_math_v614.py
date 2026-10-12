import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SAMPLES=[r'\[$$CPI=1+0.2\times0.4\times3$$\]',r'\[$$CPI=\frac{\text{Total Clock Cycles}}{\text{Instruction Count}}$$\]']
def normalize(s):
    return re.sub(r'\\\[\s*\$\$([\s\S]*?)\$\$\s*\\\]',lambda m:'$$'+m.group(1)+'$$',s)
def test_both_examples():
    for s in SAMPLES:
        out=normalize(s)
        assert out.startswith('$$') and out.endswith('$$')
        assert r'\[' not in out and r'\]' not in out
        assert out[2:-2]==s[4:-4]
def test_editor_reader_shared_normalization():
    for name in ('composite_editor','composite_reader'):
        html=(ROOT/'components'/name/'index.html').read_text()
        assert 'bvMathNormalizeNested(hrcNormalizeSource(md))' in html
        assert 'if(index%2)return part' in html
