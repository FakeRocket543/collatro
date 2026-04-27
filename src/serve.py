"""collatro.serve — HTTP API for browser access."""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from src.run import run


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/check":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            text = body.get("text", "")
            theme = body.get("theme", "slate")
            if not text:
                self._json(400, {"error": "missing 'text'"})
                return
            result = run(text, theme=theme)
            self._json(200, {"ok": True, "claims": result})
        else:
            self._json(404, {"error": "not found"})

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"error": "not found"})

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[collatro] {args[0]}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Collatro HTTP API")
    parser.add_argument("--port", "-p", type=int, default=9001)
    args = parser.parse_args()
    server = HTTPServer(("", args.port), Handler)
    print(f"🔍 Collatro API running on http://localhost:{args.port}")
    print(f"   POST /api/check {{\"text\": \"...\", \"theme\": \"sky\"}}")
    server.serve_forever()


if __name__ == "__main__":
    main()
