import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, '..');
const repoRoot = resolve(webRoot, '..');
const sourcePath = resolve(repoRoot, '06_backend/pindou/colormap/data/mard_5mm.json');
const outputDir = resolve(webRoot, 'src/assets/colormap');
const paletteOutput = resolve(outputDir, 'mard-5mm.json');
const manifestOutput = resolve(outputDir, 'manifest.json');

const requiredFields = ['brand', 'code', 'name_cn', 'hex', 'rgb', 'category'];

function normalizeRow(row) {
  for (const field of requiredFields) {
    if (row[field] === undefined || row[field] === null || row[field] === '') {
      throw new Error(`MARD 5mm row ${row.code || '<unknown>'} missing ${field}`);
    }
  }
  if (!Array.isArray(row.rgb) || row.rgb.length !== 3) {
    throw new Error(`MARD 5mm row ${row.code} has invalid rgb`);
  }
  return {
    brand: String(row.brand).toUpperCase(),
    code: String(row.code),
    name_cn: String(row.name_cn),
    hex: String(row.hex).toUpperCase(),
    rgb: row.rgb.map((value) => Number(value)),
    category: String(row.category),
    bead_diameter_mm: Number(row.bead_diameter_mm || 5)
  };
}

const rows = JSON.parse(await readFile(sourcePath, 'utf8'));
if (!Array.isArray(rows) || rows.length === 0) {
  throw new Error(`Palette source is empty: ${sourcePath}`);
}

const seen = new Set();
const palette = rows.map(normalizeRow);
for (const row of palette) {
  if (seen.has(row.code)) {
    throw new Error(`Duplicate MARD 5mm color code: ${row.code}`);
  }
  seen.add(row.code);
}

const categories = Array.from(new Set(palette.map((row) => row.category))).sort((left, right) => (
  left.localeCompare(right, 'zh-Hans-CN')
));
const generatedAt = new Date().toISOString();
const manifest = {
  version: 1,
  generated_at: generatedAt,
  source: '06_backend/pindou/colormap/data/mard_5mm.json',
  default_palette: 'mard-5mm',
  palettes: [
    {
      id: 'mard-5mm',
      brand_id: 'mard',
      display_name: 'MARD',
      bead_diameter_mm: 5,
      ui_visible: true,
      file: './mard-5mm.json',
      count: palette.length,
      categories
    }
  ],
  reserved_brand_switching: true
};

await mkdir(outputDir, { recursive: true });
await writeFile(paletteOutput, `${JSON.stringify(palette)}\n`, 'utf8');
await writeFile(manifestOutput, `${JSON.stringify(manifest)}\n`, 'utf8');

console.log(`Generated ${palette.length} MARD colors for web colormap assets.`);
