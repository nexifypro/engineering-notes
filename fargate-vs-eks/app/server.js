// The reference workload: a small HTTP service that does a little CPU work per request,
// so autoscaling has something to react to, and exposes /healthz for both platforms.
const http = require("node:http");
const { createHash } = require("node:crypto");

const PORT = process.env.PORT || 8080;
const VERSION = process.env.APP_VERSION || "v1";
const started = Date.now();

const server = http.createServer((req, res) => {
  if (req.url === "/healthz") {
    res.writeHead(200, { "content-type": "application/json" });
    return res.end(JSON.stringify({ ok: true, version: VERSION, uptime_s: Math.round((Date.now() - started) / 1000) }));
  }
  // ~1-2 ms of hashing per request: enough to make CPU-based scaling observable under load.
  let digest = "seed";
  for (let i = 0; i < 2000; i++) digest = createHash("sha256").update(digest).digest("hex");
  res.writeHead(200, { "content-type": "application/json" });
  res.end(JSON.stringify({ version: VERSION, digest: digest.slice(0, 16), host: process.env.HOSTNAME || "local" }));
});

process.on("SIGTERM", () => server.close(() => process.exit(0)));
server.listen(PORT, () => console.log(`listening on ${PORT} (${VERSION})`));
