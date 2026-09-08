// One-time migration / explicit editorial approval tool. Never run --approve in a build.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import ts from "typescript";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = path.join(root, "src");
const target = path.join(source, "content");
const archive = path.resolve(root, "../02_product/copy");
const literal = String.raw`(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')`;
const expression = new RegExp(
  String.raw`\btr\(\s*(${literal})\s*,\s*(${literal})\s*,?\s*\)`,
  "g",
);
const walk = (dir) =>
  fs
    .readdirSync(dir, { withFileTypes: true })
    .flatMap((e) =>
      e.isDirectory()
        ? e.name === "content"
          ? []
          : walk(path.join(dir, e.name))
        : /\.(vue|ts)$/.test(e.name)
          ? [path.join(dir, e.name)]
          : [],
    );
const strings = (match) =>
  ts
    .createSourceFile(
      "copy.ts",
      `const entry=[${match[1]},${match[2]}]`,
      ts.ScriptTarget.Latest,
    )
    .statements[0].declarationList.declarations[0].initializer.elements.map(
      (n) => n.text,
    );
const digest = (v) =>
  crypto.createHash("sha256").update(JSON.stringify(v)).digest("hex");
const files = walk(source);
const metadata=()=>{
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  return {title:html.match(/<title>(.*?)<\/title>/s)?.[1],description:html.match(/name="description"\s+content="([^"]*)"/)?.[1]};
};
fs.mkdirSync(target, { recursive: true });
fs.mkdirSync(archive, { recursive: true });
if (process.argv.includes("--capture-baseline")) {
  const dest = path.join(archive, "STUDIO_COPY_BE46A3D.json");
  if (fs.existsSync(dest)) throw new Error("Baseline is immutable");
  const data = Object.fromEntries(
    files.map((f) => [
      path.relative(source, f).replaceAll("\\", "/"),
      Array.from(fs.readFileSync(f, "utf8").matchAll(expression), strings),
    ]),
  );
  fs.writeFileSync(
    dest,
    JSON.stringify(
      {
        revision: "be46a3d",
        description:
          "Before VISION2. Exact static tr() text pairs, including accessible names.",
        files: data,
      },
      null,
      2,
    ) + "\n",
  );
  console.log("Archived exact copy baseline");
} else if (process.argv.includes("--migrate")) {
  let total = 0;
  for (const file of files) {
    let input = fs.readFileSync(file, "utf8");
    const name = path
      .relative(source, file)
      .replaceAll("\\", "/")
      .replace(/\.(vue|ts)$/, "")
      .replaceAll("/", "-");
    const existing = path.join(target, name + ".json");
    const entries = fs.existsSync(existing)
      ? JSON.parse(fs.readFileSync(existing, "utf8"))
      : {};
    let additions = 0;
    input = input.replace(expression, (...args) => {
      const pair = strings(args);
      let key =
        pair[1]
          .toLowerCase()
          .replace(/[^a-z0-9 ]/g, "")
          .trim()
          .split(/\s+/)
          .slice(0, 7)
          .join("_") || "label";
      key += "_" + digest(pair).slice(0, 6);
      entries[key] = pair;
      total++;
      additions++;
      return `say(copyText.${key})`;
    });
    if (!additions) continue;
    fs.writeFileSync(
      path.join(target, name + ".json"),
      JSON.stringify(entries, null, 2) + "\n",
    );
    let relative = path
      .relative(path.dirname(file), target)
      .replaceAll("\\", "/");
    if (!relative.startsWith(".")) relative = "./" + relative;
    const contentImport = input.includes("import copyText from ")
      ? ""
      : `import copyText from "${relative}/${name}.json";\n`;
    let stateRelative = path
      .relative(path.dirname(file), path.join(source, "state"))
      .replaceAll("\\", "/");
    if (!stateRelative.startsWith(".")) stateRelative = "./" + stateRelative;
    const imports =
      contentImport +
      (path.basename(file) === "state.ts" ||
      /import\s*\{[^}]*\bsay\b/.test(input)
        ? ""
        : `import { say } from "${stateRelative}";\n`);
    if (file.endsWith(".vue"))
      input = input.replace(/(<script[^>]*>)/, "$1\n" + imports);
    else input = imports + input;
    fs.writeFileSync(file, input);
  }
  console.log(`Modularized ${total} static bilingual expressions`);
} else if (process.argv.includes("--approve")) {
  const approval = process.argv
    .find((v) => v.startsWith("--source="))
    ?.slice(9);
  if (!approval)
    throw new Error("Provide an explicit owner instruction source");
  const hashes = {};
  for (const f of fs
    .readdirSync(target)
    .filter((f) => f.endsWith(".json") && f !== "approved.json")) {
    const data = JSON.parse(fs.readFileSync(path.join(target, f), "utf8"));
    hashes[f] = digest(data);
  }
  fs.writeFileSync(
    path.join(target, "approved.json"),
    JSON.stringify({ source: approval, metadata: metadata(), hashes }, null, 2) + "\n",
  );
  console.log(`Approved ${Object.keys(hashes).length} modules for ${approval}`);
} else if (process.argv.includes('--render-catalog')) {
  const lines=['# Studio 当前文案目录','','内容来源与修改权限见 STUDIO_COPY_RULES.md；本目录由内容模块导出，不在组件内重复维护。每项键名固定，内容不得随设计修正变动。',''];
  for(const file of fs.readdirSync(target).filter(f=>f.endsWith('.json')&&f!=='approved.json')) {
    const data=JSON.parse(fs.readFileSync(path.join(target,file),'utf8'));
    lines.push('## '+file,'','| 键 | 中文 | English |','|---|---|---|');
    for(const [key,value] of Object.entries(data)) {
      const safe=v=>String(v).replaceAll('|','\\|').replaceAll('\n','<br>');
      if(Array.isArray(value)&&value.length===2&&value.every(v=>typeof v==='string'))lines.push(`| ${key} | ${safe(value[0])} | ${safe(value[1])} |`);
      else if(typeof value==='string')lines.push(`| ${key} | ${safe(value)} | |`);
    }
    lines.push('');
  }
  fs.writeFileSync(path.join(archive,'STUDIO_COPY_CATALOG.md'),lines.join('\n')+'\n');
  console.log('Rendered current copy catalog');
} else {
  const approved = JSON.parse(
    fs.readFileSync(path.join(target, "approved.json"), "utf8"),
  );
  const errors = [];
  if(digest(approved.metadata)!==digest(metadata()))errors.push('Unapproved page metadata change');
  const actual = fs
    .readdirSync(target)
    .filter((f) => f.endsWith(".json") && f !== "approved.json");
  for (const f of actual)
    if (
      approved.hashes[f] !==
      digest(JSON.parse(fs.readFileSync(path.join(target, f), "utf8")))
    )
      errors.push("Unapproved copy change: " + f);
  for (const f of Object.keys(approved.hashes))
    if (!actual.includes(f)) errors.push("Missing approved module: " + f);
  for (const f of files)
    if (Array.from(fs.readFileSync(f, "utf8").matchAll(expression)).length)
      errors.push("Inline static copy: " + path.relative(source, f));
  for(const f of files) {
    const code=fs.readFileSync(f,'utf8').split('\n').filter(line=>!line.includes('replace(/\\[话题\\]#/g')).join('\n');
    if(/\p{Script=Han}/u.test(code))errors.push('Chinese copy outside the content modules: '+path.relative(source,f));
  }
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(
    `Copy contract OK: ${actual.length} modules, approved source ${approved.source}`,
  );
}
