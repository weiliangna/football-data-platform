import { execFileSync } from "node:child_process"
import { cpSync, mkdirSync, rmSync } from "node:fs"

const tsc = process.platform === "win32" ? "tsc.cmd" : "tsc"
const options = { stdio: "inherit", shell: process.platform === "win32" }
rmSync("dist", { recursive: true, force: true })
mkdirSync("dist", { recursive: true })
execFileSync(tsc, ["-p", "tsconfig.json"], options)
cpSync("index.html", "dist/index.html")
cpSync("src/styles.css", "dist/styles.css")
console.log("Build complete: dist/")
