"""Produce immutable shipped defaults; published owner overrides stay in SQLite."""
from pathlib import Path
from PIL import Image
import json

root=Path(__file__).resolve().parents[2];web=root/'05_studio';src=web/'src'
assets=json.loads((src/'media-assets.json').read_text(encoding='utf8'))
for path in (web/'public/studio-media').glob('*'):
    if path.suffix.lower() not in ('.jpg','.png','.webp'):continue
    with Image.open(path) as im:width,height=im.size
    assets.setdefault(path.stem,{'src':'/studio-media/'+path.name,'width':width,'height':height})
for key,filename in [('brand-zh','full-zh-v3.jpg'),('brand-en','english-mark-20260908.jpg'),('brand-en-contact','english-contact-20260908.jpg'),('brand-puppy','puppy-v3.jpg'),('owner-avatar','xiaogou-shuangji-avatar.png')]:
    with Image.open(web/'public/studio-brand'/filename) as im:width,height=im.size
    assets[key]={'src':'/studio-brand/'+filename,'width':width,'height':height}
for key,filename in [('arrival-entrance','building-entrance-20260908.jpg'),('parking-entrance','parking-entrance-20260908.jpg'),('parking-location','visitor-parking-20260908.jpg')]:
    with Image.open(web/'public/studio-media/arrival'/filename) as im:width,height=im.size
    assets[key]={'src':'/studio-media/arrival/'+filename,'width':width,'height':height}
(src/'media-assets.json').write_text(json.dumps(assets,indent=2)+'\n',encoding='utf8')
documents={}
for path in (src/'content').glob('*.json'):
    if path.stem in ('approved','studio-profile'):continue
    data=json.loads(path.read_text(encoding='utf8'))
    if isinstance(data,dict):
        pairs={k:v for k,v in data.items() if isinstance(v,list) and len(v)==2 and all(isinstance(t,str) for t in v)}
        if pairs:documents[path.stem]=pairs
documents['media']=assets
(root/'06_studio/content-defaults.json').write_text(json.dumps(documents,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
journal=json.loads((src/'content/journal-posts.json').read_text(encoding='utf8'))
journal['posts']=[p for p in journal['posts'] if p.get('kind')=='full' and p.get('date','')>'2026-06-24']
(root/'06_studio/journal-defaults.json').write_text(json.dumps(journal,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'modules':len(documents),'media':len(assets),'posts':len(journal['posts'])}))
