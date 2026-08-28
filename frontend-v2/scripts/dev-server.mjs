import * as http from "node:http"
import { createServer } from "node:http"
import { createReadStream, existsSync, statSync } from "node:fs"
import { extname, join, normalize } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(fileURLToPath(new URL("..", import.meta.url)), "dist")
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml" }

function proxy(req, res) {
  const upstream = http.request({ hostname: "127.0.0.1", port: 8000, path: req.url, method: req.method, headers: { ...req.headers, host: "127.0.0.1:8000" } }, (response) => { res.writeHead(response.statusCode || 502, response.headers); response.pipe(res) })
  upstream.on("error", () => { if (!res.headersSent) res.writeHead(502, { "content-type": "application/json" }); res.end(JSON.stringify({ code: 502, msg: "本地 API 暂不可用" })) })
  req.pipe(upstream)
}

createServer((req, res) => {
  if (req.url?.startsWith("/api/")) return proxy(req, res)
  const raw = decodeURIComponent((req.url || "/").split("?")[0])
  const candidate = normalize(join(root, raw === "/" ? "index.html" : raw.slice(1)))
  const file = candidate.startsWith(root) && existsSync(candidate) && statSync(candidate).isFile() ? candidate : join(root, "index.html")
  res.setHeader("content-type", mime[extname(file)] || "application/octet-stream")
  createReadStream(file).pipe(res)
}).listen(3000, "127.0.0.1", () => console.log("football-data-center preview: http://localhost:3000/"))
