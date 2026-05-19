"""Run with `python run_server.py` to expose the app on the local Wi-Fi
network. Other PCs on the same network can then reach it at
`http://<this-PC-IP>:8080`.

This script:
  * forces DEBUG=False (we are in internal-production mode);
  * loads the `.env` file via the same path used by the dev runner;
  * detects the machine's LAN IPv4 and prints a ready-to-share URL;
  * serves the app with waitress, a pure-Python WSGI server that runs
    cleanly on Windows without extra setup.
"""

import os

# Force production mode BEFORE any Flask / Config code is imported. Config
# reads FLASK_DEBUG at import time, and load_dotenv() does not override an
# env var that is already set, so writing it here pins the runtime to
# DEBUG=False even if `.env` happens to say otherwise.
os.environ["FLASK_DEBUG"] = "false"

import socket

from waitress import serve

from backend.app import app


HOST = "0.0.0.0"  # listen on every interface so the LAN can reach us
PORT = 8080


# Returns the LAN IPv4 of this machine. The trick is to open a UDP socket
# to a public address: the OS picks the matching local interface, which we
# can then read off the socket itself. No packet is actually sent. Falls
# back to 127.0.0.1 when the machine is offline or in a restricted setup.
def detect_local_ip() -> str:
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
    # (Windows services, Docker, etc.) and not attached to a real terminal.
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
