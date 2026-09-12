"""Prepare the owner's approved Kitty example, without generating a paid artwork."""
from pathlib import Path
import json,shutil
root=Path(__file__).resolve().parents[2]
fixture=Path(__file__).parent/'fixtures/generator-tutorial'
out=root/'artifacts/generator-integration';out.mkdir(parents=True,exist_ok=True)
data=json.loads((fixture/'kitty-pattern.json').read_text(encoding='utf-8'))
palette={c['code']:c for c in data['palette_used']}
grid=[[palette[code] if code else None for code in row] for row in data['grid']]
counts={code:sum(cell==code for row in data['grid'] for cell in row) for code in palette}
assert len(grid)==104 and all(len(row)==104 for row in grid)
assert counts==data['color_counts'] and sum(counts.values())==6062
pattern={'grid':grid,'palette_used':data['palette_used'],'color_counts':counts,
         'bead_total':6062,'brand':'MARD','no_bead_mask':[[c is None for c in row] for row in grid],
         'image_url':'/qa/pattern.png','metadata':{'labeled_image_url':'/qa/pattern.png'}}
(out/'tutorial-pattern.json').write_text(json.dumps(pattern,ensure_ascii=False),encoding='utf-8')
shutil.copyfile(fixture/'kitty-preview.png',out/'tutorial-pattern.png')
print(json.dumps({'example':'Kitty','size':'104x104','beads':6062,'colours':len(palette),'paid_requests':0}))
