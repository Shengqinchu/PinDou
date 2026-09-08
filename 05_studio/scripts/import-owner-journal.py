"""Import owner-provided, already retrieved post JSON. No generated or rewritten copy.

Usage: python scripts/import-owner-journal.py <raw-post-directory>
Requires requests and Pillow. Raw files contain {source, note}; expected author is fixed.
Network reads are only the image URLs exposed in the supplied post's public state.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json, sys, hashlib
import requests
from PIL import Image

web=Path(__file__).resolve().parents[1]
raw=Path(sys.argv[1]).resolve()
catalog_path=web/'src/content/journal-posts.json'
catalog=json.loads(catalog_path.read_text(encoding='utf8'))
items=[json.loads(p.read_text(encoding='utf8')) for p in raw.glob('*.json') if p.name!='results.json']
for item in items:
    assert item['note']['user']['userId']=='65f8375c000000000b00c921', 'Unexpected author'
media=web/'public/studio-journal';media.mkdir(exist_ok=True)
jobs=[(item,index,image) for item in items for index,image in enumerate(item['note']['imageList'])]
def fetch(job):
    item,index,source=job
    url=source.get('urlDefault') or next(x['url'] for x in source['infoList'] if x['imageScene']=='WB_DFT')
    url=url.replace('http://','https://')
    response=requests.get(url,timeout=40,headers={'Referer':'https://www.xiaohongshu.com/', 'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'})
    response.raise_for_status()
    picture=Image.open(BytesIO(response.content));picture.verify()
    ext={'JPEG':'jpg','PNG':'png','WEBP':'webp'}[picture.format]
    name=f"{item['note']['noteId']}-{index+1:02d}.{ext}"
    (media/name).write_bytes(response.content)
    return item['note']['noteId'],index,{'src':'studio-journal/'+name,'width':picture.width,'height':picture.height,'sha256':hashlib.sha256(response.content).hexdigest()}
with ThreadPoolExecutor(max_workers=6) as pool: downloaded=list(pool.map(fetch,jobs))
new=[]
for item in sorted(items,key=lambda x:x['note'].get('time',0),reverse=True):
    note=item['note'];ident=note['noteId']
    photos=[photo for key,_,photo in sorted(downloaded,key=lambda x:x[1]) if key==ident]
    assert len(photos)==len(note['imageList'])
    new.append({'id':ident,'title':note['title'],'body':note['desc'],'kind':'full','source':item['source'],'published_at':note.get('time'),'images':photos,'body_sha256':hashlib.sha256(note['desc'].encode()).hexdigest()})
ids={post['id'] for post in new}
catalog['posts']=new+[post for post in catalog['posts'] if post['id'] not in ids]
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'imported_posts':len(new),'imported_images':len(downloaded),'total_posts':len(catalog['posts']),'media_bytes':sum((media/Path(p['src']).name).stat().st_size for _,_,p in downloaded)},indent=2))
