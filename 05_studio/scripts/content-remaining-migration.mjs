import fs from "node:fs";
import path from "node:path";
import ts from "typescript";
import crypto from "node:crypto";
const root = path.resolve("src");
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
const literal = String.raw`(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')`;
const notification = new RegExp(
  String.raw`\bnotify\(\s*(${literal})\s*,\s*(${literal})`,
  "g",
);
for (const file of walk(root)) {
  let text = fs.readFileSync(file, "utf8"),
    imports = [];
  const name = path
    .relative(root, file)
    .replaceAll("\\", "/")
    .replace(/\.(vue|ts)$/, "")
    .replaceAll("/", "-");
  const out = path.join(root, "content", name + ".json");
  const entries = fs.existsSync(out)
    ? JSON.parse(fs.readFileSync(out, "utf8"))
    : {};
  let changed = false;
  const add = (pair) => {
    changed = true;
    const key =
      "message_" +
      crypto
        .createHash("sha256")
        .update(JSON.stringify(pair))
        .digest("hex")
        .slice(0, 8);
    entries[key] = pair;
    return key;
  };
  text = text.replace(notification, (_, zh, en) => {
    const ast = ts.createSourceFile(
      "copy.ts",
      `const x=[${zh},${en}]`,
      ts.ScriptTarget.Latest,
    );
    const pair =
      ast.statements[0].declarationList.declarations[0].initializer.elements.map(
        (n) => n.text,
      );
    const key = add(pair);
    return `notify(copyText.${key}[0], copyText.${key}[1]`;
  });
  text = text.replace(
    /\btr\(\s*`([^`]+)`\s*,\s*`([^`]+)`\s*,?\s*\)/g,
    (_, zh, en) => {
      const expressions = [];
      const format = (s) =>
        s.replace(/\$\{([^}]+)\}/g, (_, expr) => {
          let i = expressions.indexOf(expr);
          if (i < 0) i = expressions.push(expr) - 1;
          return `{v${i}}`;
        });
      const key = add([format(zh), format(en)]);
      if (!text.includes("import { formatCopy }")) imports.push("formatCopy");
      return `formatCopy(copyText.${key}, {${expressions.map((s, i) => `v${i}: ${s}`).join(", ")}})`;
    },
  );
  // Remaining branching copy is extracted verbatim as strings; the existing branches stay unchanged.
  const replacements =
    {
      "admin.ts": [
        "已标记完成",
        "订单已更新",
        "Marked as fulfilled",
        "Order updated",
      ],
      "components/ReleaseNotice.vue": [
        "工作台有更新，请先保存当前更改，再重新载入。",
        "页面有更新，方便时重新载入即可。",
        "An update is ready. Save your changes before reloading.",
        "An updated page is ready when you are.",
      ],
      "pages/Order.vue": [
        "付款已收到，到店座位已确认。带着你的期待，我们工作室见。",
        "付款已收到，订单已确认。请联系店主安排到店自提。",
        "Payment received and your studio seats are confirmed. Bring a little inspiration. We will see you here.",
        "Payment received and your order is confirmed. Contact the host to arrange studio pickup.",
      ],
      "components/CommerceManager.vue": ["英文", "中文"],
    }[path.relative(root, file).replaceAll("\\", "/")] || [];
  for (const value of replacements) {
    const quoted = JSON.stringify(value);
    if (text.includes(quoted)) {
      const key =
        "literal_" +
        crypto.createHash("sha256").update(value).digest("hex").slice(0, 8);
      entries[key] = value;
      changed = true;
      text = text.replaceAll(quoted, `copyText.${key}`);
    }
  }
  if (!changed) continue;
  fs.writeFileSync(out, JSON.stringify(entries, null, 2) + "\n");
  let prefix = "";
  if (!text.includes("import copyText from ")) {
    let relative = path.relative(path.dirname(file), out).replaceAll("\\", "/");
    if (!relative.startsWith(".")) relative = "./" + relative;
    prefix += `import copyText from "${relative}";\n`;
  }
  if (imports.length) {
    let relative = path
      .relative(path.dirname(file), path.join(root, "state"))
      .replaceAll("\\", "/");
    if (!relative.startsWith(".")) relative = "./" + relative;
    prefix += `import { ${[...new Set(imports)].join(", ")} } from "${relative}";\n`;
  }
  text = file.endsWith(".vue")
    ? text.replace(/(<script[^>]*>)/, "$1\n" + prefix)
    : prefix + text;
  fs.writeFileSync(file, text);
}
