import { readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const generatedRoots = [
  path.join(root, "lib", "api-client-react", "src", "generated"),
  path.join(root, "lib", "api-zod", "src", "generated"),
];

async function generatedFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const filePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await generatedFiles(filePath)));
    } else if (entry.isFile() && filePath.endsWith(".ts")) {
      files.push(filePath);
    }
  }

  return files;
}

for (const generatedRoot of generatedRoots) {
  await stat(generatedRoot);
  for (const filePath of await generatedFiles(generatedRoot)) {
    const content = await readFile(filePath, "utf8");
    const normalized = `${content.replace(/[ \t\r\n]+$/u, "")}\n`;
    if (normalized !== content) {
      await writeFile(filePath, normalized);
    }
  }
}