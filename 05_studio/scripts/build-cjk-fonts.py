"""Build small, self-hosted Chinese UI fonts from the licensed Google Fonts sources."""
import hashlib
import json
import argparse
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

web = Path(__file__).resolve().parents[1]
source_dir = web.parent / "artifacts/studio-refinement/font-sources"
output = web / "src/assets/fonts"
output.mkdir(parents=True, exist_ok=True)
licenses = web / "public/font-licenses"
licenses.mkdir(parents=True, exist_ok=True)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--extend-copy', action='append', default=[], help='Extend existing subsets with a named content module, preserving all current glyphs')
options_cli = parser.parse_args()
if options_cli.extend_copy:
    modules = [(web / 'src/content' / (name + '.json')) for name in options_cli.extend_copy]
    text = ''.join(p.read_text(encoding='utf8') for p in modules)
else:
    text = "".join(p.read_text(encoding="utf8") for p in (web / "src").rglob("*") if p.suffix in {".vue", ".ts", ".json"})
# Include all static UI CJK characters, punctuation and common numerals used in dates.
characters = {ord(c) for c in text if ord(c) > 127}
characters.update(range(0x3000, 0x3040))
characters.update(range(0xFF00, 0xFFEF))
if options_cli.extend_copy:
    for name in ('pindou-serif-sc.woff2', 'pindou-sans-sc.woff2'):
        with TTFont(output / name) as existing:
            characters.update(existing.getBestCmap())
manifest = {"characters": len(characters), "fonts": []}
for upstream, family, filename, expected in [
    ("NotoSerifSC", "PinDou Serif SC", "pindou-serif-sc.woff2", "050080d9255a86808f2945bffac582b31ef32bc36411ce29563b4961670c66f9"),
    ("NotoSansSC", "PinDou Sans SC", "pindou-sans-sc.woff2", "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da"),
]:
    source = source_dir / f"{upstream}-variable.ttf"
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise SystemExit(f"Unexpected source font checksum: {source}")
    font = TTFont(source, recalcTimestamp=False)
    options = subset.Options()
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    options.layout_features = ["*"]
    sub = subset.Subsetter(options=options)
    sub.populate(unicodes=characters)
    sub.subset(font)
    # Distinguish the UI subset from the upstream full font; retain license metadata.
    for name in font["name"].names:
        if name.nameID in (1, 4, 16):
            name.string = family.encode(name.getEncoding())
        elif name.nameID == 6:
            name.string = family.replace(" ", "").encode(name.getEncoding())
    font.flavor = "woff2"
    target = output / filename
    font.save(target)
    (licenses / f"{upstream}-OFL.txt").write_bytes((source_dir / f"{upstream}-OFL.txt").read_bytes())
    manifest["fonts"].append({"family": family, "upstream": upstream, "source_sha256": expected, "file": filename, "bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
(output / "manifest.json").write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf8"))
print(json.dumps(manifest, ensure_ascii=False, indent=2))
