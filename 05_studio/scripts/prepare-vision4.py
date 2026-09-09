"""Extract supplied process illustrations; preserve source bytes and image ratios."""
from pathlib import Path
import json,hashlib,io
import fitz
from PIL import Image,ImageOps
root=Path(__file__).resolve().parents[2]
source=Path(r'D:/Users/123/WeChat/xwechat_files/wxid_ax9ox7wnmntu22_e3b0/temp/RWTemp/2026-09/688eae86b942311f85fe4277a30b5789/拼豆流程.pdf')
out=root/'05_studio/public/studio-media/v4';out.mkdir(parents=True,exist_ok=True)
originals=root/'artifacts/vision4/originals';originals.mkdir(parents=True,exist_ok=True)
doc=fitz.open(source);manifest=[]
asset_path=root/'05_studio/src/media-assets.json';assets=json.loads(asset_path.read_text(encoding='utf8'))
for key,xref in [('pattern',12),('tools',17),('making',24),('ironing',28),('findings',29),('finishes',33),('packaging',34)]:
    data=doc.extract_image(xref);raw=data['image'];(originals/f'{key}.{data["ext"]}').write_bytes(raw)
    im=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('RGB');im.thumbnail((1400,1600),Image.Resampling.LANCZOS)
    target=out/f'process-{key}.webp';im.save(target,'WEBP',quality=90,method=6)
    assets[f'process-{key}']={'src':'/studio-media/v4/'+target.name,'width':im.width,'height':im.height}
    manifest.append({'name':key,'pdf_xref':xref,'source_sha256':hashlib.sha256(raw).hexdigest(),'web_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'width':im.width,'height':im.height})
asset_path.write_text(json.dumps(assets,indent=2)+'\n',encoding='utf8')
(out/'sources.json').write_text(json.dumps({'pdf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'images':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Prepared',len(manifest),'process images')
