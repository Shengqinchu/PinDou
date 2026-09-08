"""Build OFL Xiaolai heading webfonts. Core first; other Han glyphs load by range.

Source is the unmodified v3.126 release, archived in artifacts/vision3/research.
The full source is never loaded by a customer's browser.
"""
from pathlib import Path
import hashlib
import json
import re
from fontTools import subset
from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parents[2]
web = root / '05_studio'
source = root / 'artifacts/vision3/research/Xiaolai-Regular.ttf'
font = TTFont(source)
available = set(font.getBestCmap())
core = set(range(32, 127)) | {ord(c) for c in '属于你的全新拼豆手作体验来吧让我们走进小屋日记详细信息'}
for page in (web/'src').rglob('*.vue'):
    text = page.read_text(encoding='utf8')
    modules = {}
    for name, rel in re.findall(r'import (\w+) from [\"\']([^\"\']*content/[^\"\']+\.json)[\"\']', text):
        path = (page.parent/rel).resolve()
        modules[name] = json.loads(path.read_text(encoding='utf8'))
    for heading in re.findall(r'<h[1-6]\b[^>]*>(.*?)</h[1-6]>', text, re.S):
        for name, key in re.findall(r'(\w+)\.(\w+)', heading):
            value = modules.get(name, {}).get(key)
            if isinstance(value, list):
                core.update(ord(c) for c in ''.join(str(x) for x in value))
journal = json.loads((web/'src/content/journal-posts.json').read_text(encoding='utf8'))
for post in journal['posts']:
    core.update(ord(c) for c in post['title'])
core &= available
remaining = sorted(cp for cp in available-core if 0x3000 <= cp <= 0x9fff or 0xff00 <= cp <= 0xffef)
groups = [sorted(core)] + [remaining[i:i+512] for i in range(0,len(remaining),512)]
dest = web/'public/studio-fonts'; dest.mkdir(exist_ok=True)
css=[]; manifest=[]
for i, points in enumerate(groups):
    part=TTFont(source)
    options=subset.Options(); options.flavor='woff2'; options.recalc_timestamp=False
    cutter=subset.Subsetter(options=options); cutter.populate(unicodes=points); cutter.subset(part)
    part.flavor='woff2'
    from io import BytesIO
    buf=BytesIO();part.save(buf);data=buf.getvalue()
    name=f'xiaolai-{i:02d}-{hashlib.sha256(data).hexdigest()[:10]}.woff2'
    (dest/name).write_bytes(data)
    intervals=[];start=end=points[0]
    for cp in points[1:]:
        if cp==end+1:end=cp
        else:
            intervals.append(f'U+{start:X}'+(f'-{end:X}' if end!=start else ''));start=end=cp
    intervals.append(f'U+{start:X}'+(f'-{end:X}' if end!=start else ''))
    ranges=','.join(intervals)
    css.append('@font-face { font-family: "PinDou Hand SC"; font-style: normal; font-weight: 400; font-display: swap; '+f'src: url("/studio-fonts/{name}") format("woff2"); unicode-range: {ranges};'+' }')
    manifest.append({'file':name,'bytes':len(data),'glyphs':len(points),'core':i==0})
(web/'src/styles/handwriting-fonts.css').write_text('\n'.join(css)+'\n',encoding='utf8')
(dest/'manifest.json').write_text(json.dumps({'source':'https://github.com/lxgw/kose-font/releases/tag/v3.126','sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'parts':manifest},indent=2)+'\n',encoding='utf8')
(dest/'OFL.txt').write_bytes((root/'artifacts/vision3/research/Xiaolai-OFL.txt').read_bytes())
print(json.dumps({'core':manifest[0],'parts':len(manifest),'total_bytes':sum(x['bytes'] for x in manifest)}))
