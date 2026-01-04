import http.server
import socketserver
import os
import sys
import cgi

PORT = 5000
HOST = "0.0.0.0"
UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        if self.path == '/list-uploads':
            try:
                files = [f for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))]
                # Basic filter for images
                image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
                images = [f for f in files if f.lower().endswith(image_extensions)]
                
                import json
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(images).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/upload':
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST',
                         'CONTENT_TYPE': self.headers['Content-Type'],
                         }
            )

            if 'file' in form:
                file_item = form['file']
                if file_item.filename:
                    # Clean filename to prevent path traversal
                    fn = os.path.basename(file_item.filename)
                    with open(os.path.join(UPLOAD_DIR, fn), 'wb') as f:
                        f.write(file_item.file.read())
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"Success")
                    return

            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Failed to upload")
        else:
            super().do_POST()

# Allow port reuse
socketserver.TCPServer.allow_reuse_address = True

def run_server():
    try:
        with socketserver.TCPServer((HOST, PORT), NoCacheHandler) as httpd:
            print(f"Serving at http://{HOST}:{PORT}")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 98:
            print(f"Port {PORT} is busy, server is likely already running.")
            sys.exit(0)
        else:
            print(f"Server error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    run_server()
