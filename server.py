import http.server
import socketserver
import os
import sys
import cgi
import json

PORT = 5000
HOST = "0.0.0.0"
UPLOAD_DIR = "uploads"
METADATA_FILE = "metadata.json"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def get_metadata():
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        if self.path.startswith('/list-media'):
            try:
                metadata = get_metadata()
                files = [f for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))]
                image_exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
                video_exts = ('.mp4', '.webm', '.ogg', '.mov')
                
                query_type = None
                if 'type=image' in self.path: query_type = 'image'
                elif 'type=video' in self.path: query_type = 'video'

                media_list = []
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    m_type = 'image' if ext in image_exts else 'video' if ext in video_exts else None
                    if m_type and (query_type is None or m_type == query_type):
                        media_list.append({
                            'filename': f,
                            'type': m_type,
                            'displayName': metadata.get(f, f)
                        })
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(media_list).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/upload':
            try:
                # Use FieldStorage with a limit to avoid some issues with large files
                # or missing boundaries in some cases. 
                # Also ensure we handle the binary stream correctly.
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST',
                             'CONTENT_TYPE': self.headers['Content-Type'],
                             }
                )

                if 'file' in form:
                    file_item = form['file']
                    custom_name = form.getvalue('customName', '').strip()
                    
                    if file_item.filename:
                        fn = os.path.basename(file_item.filename)
                        # Ensure filename is unique or handle collisions if needed
                        # For now, just write it.
                        with open(os.path.join(UPLOAD_DIR, fn), 'wb') as f:
                            f.write(file_item.file.read())
                        
                        if custom_name:
                            metadata = get_metadata()
                            metadata[fn] = custom_name
                            save_metadata(metadata)
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(b"Success")
                        return
                
                print("Upload failed: 'file' not in form or filename missing")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Failed to upload: No file provided")
            except Exception as e:
                print(f"Upload exception: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Server error: {e}".encode())
        else:
            super().do_POST()

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
