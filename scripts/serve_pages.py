"""Serve the generated website with its production project-path prefix."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / '.ai/scratch/pages/output'
PREFIX = '/kokoroTTS'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == '/' or self.path == PREFIX:
            self.send_response(302)
            self.send_header('Location', PREFIX + '/')
            self.end_headers()
            return
        if not urlsplit(self.path).path.startswith(PREFIX + '/'):
            self.send_error(404)
            return
        self.path = self.path[len(PREFIX):]
        super().do_GET()


if __name__ == '__main__':
    print('Serving http://127.0.0.1:9006' + PREFIX + '/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 9006), Handler).serve_forever()
