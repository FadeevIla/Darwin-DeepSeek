# core/health_server.py
"""HTTP-сервер для healthcheck (Render, Docker)."""
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Darwin is alive!")

    def log_message(self, format, *args):
        pass  # Отключаем логи запросов


def start_health_server():
    """Запускает health-сервер в отдельном потоке."""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread