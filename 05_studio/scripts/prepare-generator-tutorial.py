"""Offline tutorial fixture, using the existing Standard pattern algorithm."""
from pathlib import Path
import json,sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'06_backend'))
from pindou.pattern.builder import PatternBuilder
from pindou.pattern.exporter import PatternExporter
from pindou.providers.base import SizePreset
out=root/'artifacts/generator-integration';out.mkdir(parents=True,exist_ok=True)
sheet=PatternBuilder().build(SizePreset('52x52'),raw_image=(root/'01_research/tech/test_inputs/cartoon_synthetic.png').read_bytes(),mode='script')
(out/'tutorial-pattern.json').write_text(json.dumps(sheet.to_frontend_dict(),ensure_ascii=False),encoding='utf-8')
(out/'tutorial-pattern.png').write_bytes(PatternExporter().to_labeled_grid_png(sheet))
print(json.dumps({'beads':sheet.bead_total,'colours':len(sheet.palette_used),'paid_requests':0}))
