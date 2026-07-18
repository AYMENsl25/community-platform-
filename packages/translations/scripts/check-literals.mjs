import console from "node:console";
import { globSync, readFileSync } from "node:fs";
import process from "node:process";
import { URL } from "node:url";
import ts from "typescript";

const sourceRoot = new URL("../../../apps/web/src/", import.meta.url);
const files = globSync("**/*.tsx", { cwd: sourceRoot }).filter(
  (file) => !file.includes(".test.") && !file.includes("/test/"),
);
const visibleCharacters = /[A-Za-zÀ-ÿ؀-ۿ]/u;
const visibleAttributes = new Set([
  "alt",
  "aria-description",
  "aria-label",
  "placeholder",
  "title",
]);
const violations = [];

for (const file of files) {
  const source = readFileSync(new URL(file, sourceRoot), "utf8");
  const tree = ts.createSourceFile(
    file,
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  function visit(node) {
    if (ts.isJsxText(node) && visibleCharacters.test(node.getText(tree)))
      violations.push(
        `${file}:${tree.getLineAndCharacterOfPosition(node.getStart(tree)).line + 1}`,
      );
    if (
      ts.isJsxExpression(node) &&
      node.expression &&
      (ts.isStringLiteral(node.expression) ||
        ts.isNoSubstitutionTemplateLiteral(node.expression)) &&
      visibleCharacters.test(node.expression.text)
    )
      violations.push(
        `${file}:${tree.getLineAndCharacterOfPosition(node.getStart(tree)).line + 1}`,
      );
    if (
      ts.isJsxAttribute(node) &&
      visibleAttributes.has(node.name.getText(tree)) &&
      node.initializer
    ) {
      const initializer = ts.isJsxExpression(node.initializer)
        ? node.initializer.expression
        : node.initializer;
      if (
        initializer &&
        (ts.isStringLiteral(initializer) ||
          ts.isNoSubstitutionTemplateLiteral(initializer)) &&
        visibleCharacters.test(initializer.text)
      )
        violations.push(
          `${file}:${tree.getLineAndCharacterOfPosition(node.getStart(tree)).line + 1}`,
        );
    }
    ts.forEachChild(node, visit);
  }
  visit(tree);
}

if (violations.length) {
  console.error(
    `Visible literals must use translation keys:\n${violations.join("\n")}`,
  );
  process.exit(1);
}
console.log(
  `Translation literal check passed (${files.length} production TSX files).`,
);
