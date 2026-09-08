// One-time extraction of legacy dictionaries. No string values are rewritten.
import fs from "node:fs";
import path from "node:path";
import ts from "typescript";
import { createHash } from "node:crypto";
const base = path.resolve("src");
const tasks = [
  ["state.ts", "products"],
  ["state.ts", "gallery"],
  ["commerce.ts", "messages"],
  ["commerce.ts", "labels"],
  ["ui.ts", "labels"],
  ["components/StudioCarousel.vue", "photos"],
  ["components/admin/SchedulePanel.vue", "labels"],
];
function value(n) {
  if (ts.isAsExpression(n) || ts.isParenthesizedExpression(n))
    return value(n.expression);
  if (ts.isStringLiteral(n) || ts.isNumericLiteral(n))
    return ts.isStringLiteral(n) ? n.text : Number(n.text);
  if (n.kind === ts.SyntaxKind.NullKeyword) return null;
  if (n.kind === ts.SyntaxKind.TrueKeyword) return true;
  if (n.kind === ts.SyntaxKind.FalseKeyword) return false;
  if (ts.isArrayLiteralExpression(n)) return n.elements.map(value);
  if (ts.isObjectLiteralExpression(n))
    return Object.fromEntries(
      n.properties.map((p) => [p.name.text, value(p.initializer)]),
    );
  throw Error("Nonliteral " + n.getText());
}
for (const [file, variable] of tasks) {
  const loc = path.join(base, file);
  let original = fs.readFileSync(loc, "utf8");
  const offset = file.endsWith(".vue")
    ? original.indexOf(">", original.indexOf("<script")) + 1
    : 0;
  const code = original.slice(
    offset,
    file.endsWith(".vue") ? original.indexOf("</script>") : undefined,
  );
  const tree = ts.createSourceFile(
    "content.ts",
    code,
    ts.ScriptTarget.Latest,
    true,
  );
  let found;
  function visit(n) {
    if (ts.isVariableDeclaration(n) && n.name.getText(tree) === variable)
      found = n;
    ts.forEachChild(n, visit);
  }
  visit(tree);
  if (!found) {
    console.log("No data declaration", file, variable);
    continue;
  }
  if (
    ts.isIdentifier(found.initializer) ||
    (ts.isAsExpression(found.initializer) &&
      ts.isIdentifier(found.initializer.expression))
  )
    continue;
  const data = value(found.initializer),
    name =
      "data-" +
      file.replace(/\.(ts|vue)$/, "").replaceAll("/", "-") +
      "-" +
      variable;
  fs.writeFileSync(
    path.join(base, "content", name + ".json"),
    JSON.stringify(data, null, 2) + "\n",
  );
  const identifier = "content" + variable[0].toUpperCase() + variable.slice(1);
  const cast = found.type?.getText(tree).includes("Record")
    ? " as " + found.type.getText(tree)
    : "";
  original =
    original.slice(0, offset + found.initializer.getStart(tree)) +
    identifier +
    cast +
    original.slice(offset + found.initializer.end);
  const rel = path
    .relative(path.dirname(loc), path.join(base, "content", name + ".json"))
    .replaceAll("\\", "/");
  const imp = `import ${identifier} from "${rel.startsWith(".") ? rel : "./" + rel}";\n`;
  original = file.endsWith(".vue")
    ? original.replace(/(<script[^>]*>)/, "$1\n" + imp)
    : imp + original;
  fs.writeFileSync(loc, original);
}
// Typed navigation objects retain icon imports; their bilingual labels move to the catalog.
const file = "components/CommerceManager.vue",
  loc = path.join(base, file);
let text = fs.readFileSync(loc, "utf8");
const catalog = path.join(base, "content/components-CommerceManager.json"),
  entries = JSON.parse(fs.readFileSync(catalog, "utf8"));
text = text.replace(/zh:\s*"([^"\n]+)",\s*en:\s*"([^"\n]+)"/g, (_, zh, en) => {
  const key =
    "nav_" +
    createHash("sha256")
      .update(zh + en)
      .digest("hex")
      .slice(0, 8);
  entries[key] = [zh, en];
  return `zh: copyText.${key}[0], en: copyText.${key}[1]`;
});
fs.writeFileSync(loc, text);
fs.writeFileSync(catalog, JSON.stringify(entries, null, 2) + "\n");
