import http.server
import socketserver
import os
import sys
import cgi
import json
import logging

# Configure logging to see errors in the console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return {}
    return {}

def save_metadata(metadata):
    try:
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f)
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")

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
                logger.error(f"Error listing media: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/upload':
            try:
                # Log headers for debugging
                logger.info(f"Upload request received. Content-Type: {self.headers.get('Content-Type')}")
                
                # Check for multipart/form-data
                content_type = self.headers.get('Content-Type', '')
                if 'multipart/form-data' not in content_type:
                    logger.error("Invalid Content-Type for upload")
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Invalid Content-Type")
                    return

                # Manually parse using cgi
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST',
                             'CONTENT_TYPE': content_type,
                             }
                )

                file_field = form['file'] if 'file' in form else None
                
                if file_field is not None and file_field.filename:
                    filename = os.path.basename(file_field.filename)
                    custom_name = form.getvalue('customName', '').strip()
                    
                    logger.info(f"Saving file: {filename} with custom name: {custom_name}")
                    
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    with open(file_path, 'wb') as f:
                        f.write(file_field.file.read())
                    
                    if custom_name:
                        metadata = get_metadata()
                        metadata[filename] = custom_name
                        save_metadata(metadata)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b"Success")
                    logger.info("Upload successful")
                    return
                else:
                    logger.error("No file found in the request")
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"No file provided")
            except Exception as e:
                logger.error(f"Upload exception: {e}", exc_info=True)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Server error: {e}".encode())
        else:
            super().do_POST()

socketserver.TCPServer.allow_reuse_address = True

def run_server():
    try:
        with socketserver.TCPServer((HOST, PORT), NoCacheHandler) as httpd:
            logger.info(f"Serving at http://{HOST}:{PORT}")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 98:
            logger.warning(f"Port {PORT} is busy, server is likely already running.")
            sys.exit(0)
        else:
            logger.error(f"Server error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    run_server()
