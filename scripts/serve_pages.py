"""Serve the generated website with its production project-path prefix."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / '.ai/scratch/pages/output'
PREFIX = '/kokoroTTS'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_head(self):
        self._range_remaining = None
        self._range_supported = False
        request_path = urlsplit(self.path).path
        if request_path in ('/', PREFIX):
            self.send_response(302)
            self.send_header('Location', PREFIX + '/')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if not request_path.startswith(PREFIX + '/'):
            self.send_error(404)
            return
        self.path = self.path[len(PREFIX):]
        path = Path(self.translate_path(self.path))
        self._range_supported = path.is_file()
        requested_range = self.headers.get('Range', '')
        # Native Ogg/Opus players inspect the end of the file to establish duration.
        # Ignore multipart/conditional ranges and return the complete representation.
        if (self.command != 'GET' or not self._range_supported
                or not requested_range.startswith('bytes=')
                or ',' in requested_range or self.headers.get('If-Range')):
            return super().send_head()

        try:
            file = path.open('rb')
        except OSError:
            self.send_error(404, 'File not found')
            return
        try:
            stat = os.fstat(file.fileno())
            size = stat.st_size
            try:
                first, separator, last = requested_range[6:].partition('-')
                if not separator or not (first or last):
                    raise ValueError
                if first:
                    start = int(first)
                    end = min(int(last), size - 1) if last else size - 1
                else:
                    suffix = int(last)
                    if suffix <= 0:
                        raise ValueError
                    start, end = max(0, size - suffix), size - 1
                if start < 0 or start >= size or end < start:
                    raise ValueError
            except ValueError:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                file.close()
                return

            file.seek(start)
            self._range_remaining = end - start + 1
            self.send_response(206)
            self.send_header('Content-Type', self.guess_type(str(path)))
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.send_header('Content-Length', str(self._range_remaining))
            self.send_header('Last-Modified', self.date_time_string(stat.st_mtime))
            self.end_headers()
            return file
        except BaseException:
            file.close()
            raise

    def end_headers(self):
        if getattr(self, '_range_supported', False):
            self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def copyfile(self, source, outputfile):
        if self._range_remaining is None:
            return super().copyfile(source, outputfile)
        remaining = self._range_remaining
        while remaining:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


if __name__ == '__main__':
    print('Serving http://127.0.0.1:9006' + PREFIX + '/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 9006), Handler).serve_forever()
