"""Preserve supplied sources; generate proportional, responsive web delivery files."""
from pathlib import Path
from PIL import Image, ImageOps
import hashlib, json, shutil

root=Path(__file__).resolve().parents[2];web=root/'05_studio'
source=root/'artifacts/vision3/originals';dest=web/'public/studio-media/v3';dest.mkdir(parents=True,exist_ok=True)
brand=web/'public/studio-brand';brand.mkdir(exist_ok=True)
for src,name in [('page1-1-Image15.jpg','full-zh-v3.jpg'),('page1-2-Image16.jpg','full-en-v3.jpg'),('page2-1-Image20.jpg','puppy-v3.jpg')]:
    shutil.copyfile(source/src,brand/name)
assets={};sources={}
for name,src in [('hero-illustration','page3-0-Image23.jpg'),('shop-collage','space-12.jpg')]+[(f'space-{i:02d}',f'space-{i:02d}.jpg') for i in range(1,13)]:
    path=source/src;im=ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    variants=[]
    for width in [640,1280,1920]:
        w=min(width,im.width)
        if any(x['width']==w for x in variants):continue
        resized=im.resize((w,round(im.height*w/im.width)),Image.Resampling.LANCZOS)
        fn=f'{name}-{w}.webp';resized.save(dest/fn,'WEBP',quality=85,method=6)
        variants.append({'src':f'/studio-media/v3/{fn}','width':w})
    assets[name]={'src':variants[min(1,len(variants)-1)]['src'],'width':im.width,'height':im.height,'srcset':', '.join(f"{v['src']} {v['width']}w" for v in variants)}
    sources[name]={'source':src,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'width':im.width,'height':im.height}
(web/'src/media-assets.json').write_text(json.dumps(assets,indent=2)+'\n',encoding='utf8')
(dest/'sources.json').write_text(json.dumps(sources,indent=2)+'\n',encoding='utf8')
print(json.dumps({'assets':len(assets),'bytes':sum(x.stat().st_size for x in dest.iterdir() if x.suffix=='.webp')}))
