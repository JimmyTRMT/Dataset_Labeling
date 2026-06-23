"""LAN production launcher. Run: `python run_server.py`.

Serves the app on `http://<this-PC-IP>:8080` via waitress (pure-Python WSGI,
zero-config on Windows). Forces DEBUG=False, prints the auto-detected URL.
"""

import os

# Pin DEBUG=False BEFORE Flask/Config import. Config reads FLASK_DEBUG at
# import time, and load_dotenv() won't override an already-set env var.
os.environ["FLASK_DEBUG"] = "false"

import socket

from waitress import serve

from backend.app import app


HOST = "0.0.0.0"  # listen on every interface
PORT = 8080


def detect_local_ip() -> str:
    """LAN IPv4 of this machine. UDP-socket trick - no packet actually sent."""
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_socket.connect(("8.8.8.8", 80))
        return udp_socket.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        udp_socket.close()


if __name__ == "__main__":
    local_ip = detect_local_ip()
    banner = "=" * 64
    print(banner, flush=True)
    print("  Dataset Labeling Platform  -  production server (waitress)", flush=True)
    print(banner, flush=True)
    print(f"  Server online on port {PORT}", flush=True)
    print(f"  This PC      : http://127.0.0.1:{PORT}", flush=True)
    print(f"  Same Wi-Fi   : http://{local_ip}:{PORT}", flush=True)
    print(flush=True)
    print("  Press Ctrl+C to stop.", flush=True)
    print("  (Windows Firewall may prompt the first time. Allow it on", flush=True)
    print("   private networks so other machines can reach the server.)", flush=True)
    print(banner, flush=True)
    serve(app, host=HOST, port=PORT)
