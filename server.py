import http.server
import socketserver
import socket
import sys

PORT = 5000
HOST = "0.0.0.0"

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

# Allow port reuse to avoid "Address already in use" errors
socketserver.TCPServer.allow_reuse_address = True

def run_server():
    try:
        with socketserver.TCPServer((HOST, PORT), NoCacheHandler) as httpd:
            print(f"Serving at http://{HOST}:{PORT}")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 98:
            print(f"Port {PORT} is busy, server is likely already running.")
            # Keep the process alive if we think the server is running elsewhere
            # to prevent workflow from flapping, or just exit gracefully
            sys.exit(0)
        else:
            print(f"Server error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    run_server()
