from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os, webbrowser, threading

root = Path(__file__).resolve().parent / "web"
os.chdir(root)
address = "http://127.0.0.1:8765"
server = ThreadingHTTPServer(("127.0.0.1", 8765), SimpleHTTPRequestHandler)
threading.Timer(0.8, lambda: webbrowser.open(address)).start()
print("Open", address, "• Press Ctrl+C to stop")
server.serve_forever()
