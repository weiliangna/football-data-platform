import { execFileSync } from "node:child_process"
import { readdirSync, readFileSync, statSync } from "node:fs"

const tsc = process.platform === "win32" ? "tsc.cmd" : "tsc"
execFileSync(tsc, ["-p", "tsconfig.json", "--noEmit"], { stdio: "inherit", shell: process.platform === "win32" })
function walk(dir) { return readdirSync(dir).flatMap((name) => { const path = `${dir}/${name}`; return statSync(path).isDirectory() ? walk(path) : [path] }) }
const files = walk("src").filter((file) => /\.(ts|css)$/.test(file))
for (const file of files) {
  const source = readFileSync(file, "utf8")
  if (source.includes("dangerouslySetInnerHTML")) throw new Error(`${file}: forbidden token dangerouslySetInnerHTML`)
  if (source.includes("\uFFFD")) throw new Error(`${file}: replacement character detected`)
}
console.log(`Lint complete: ${files.length} files checked`)
