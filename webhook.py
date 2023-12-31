"""
webhook.py — optional GitHub webhook for auto doc re-indexing.
Run alongside the bot: python webhook.py
Then add a webhook in your GitHub repo pointing to http://your-server:8080/webhook
"""

import hashlib
import hmac
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from rag.pipeline import index_docs

logger = logging.getLogger(__name__)
SECRET = os.getenv("WEBHOOK_SECRET", "").encode()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook":
            self.send_response(404); self.end_headers(); return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if SECRET:
            sig = self.headers.get("X-Hub-Signature-256", "")
            expected = "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                self.send_response(403); self.end_headers(); return

        if self.headers.get("X-GitHub-Event") == "push":
            logger.info("GitHub push — triggering doc re-index")
            try:
                index_docs()
            except Exception as ex:
                logger.error(f"Re-index failed: {ex}")

        self.send_response(200); self.end_headers()

    def log_message(self, *_): pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.getenv("WEBHOOK_PORT", "8080"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
