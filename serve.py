import http.server
import socketserver
import os
import sys

PORT = 3000

class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and disable aggressive caching for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def guess_type(self, path):
        # Ensure correct MIME type for ES modules and CSS
        if path.endswith('.js'):
            return 'application/javascript'
        if path.endswith('.css'):
            return 'text/css'
        if path.endswith('.json'):
            return 'application/json'
        return super().guess_type(path)

def run():
    # Ensure UTF-8 output on Windows
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    web_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(web_dir)
    
    for attempt_port in [3000, 3001, 8000, 8080]:
        try:
            with socketserver.TCPServer(("", attempt_port), CustomHTTPHandler) as httpd:
                print("=" * 60)
                print(f"[Veduka AI] Event Marketplace - Phase 1 Preview Server Running")
                print(f">> Local URL: http://localhost:{attempt_port}")
                print(f">> Network:   http://127.0.0.1:{attempt_port}")
                print("=" * 60)
                sys.stdout.flush()
                httpd.serve_forever()
        except OSError:
            continue

if __name__ == '__main__':
    run()
