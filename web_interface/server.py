#!/usr/bin/env python3
"""
Simple HTTP Server for AI-Transcribe Web Interface
Простой HTTP сервер для веб-интерфейса AI-Transcribe
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

# Конфигурация
PORT = 8080
DIRECTORY = Path(__file__).parent

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP обработчик с поддержкой CORS"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        # Обычная обработка для всех путей
        super().do_GET()

def main():
    """Запуск сервера"""
    # Переходим в директорию с веб-файлами
    os.chdir(DIRECTORY)
    
    # Создаем сервер
    with socketserver.TCPServer(("0.0.0.0", PORT), CORSHTTPRequestHandler) as httpd:
        print(f"�� Запуск веб-сервера AI-Transcribe на порту {PORT}")
        print(f"📁 Директория: {DIRECTORY}")
        print(f"🌐 Локальный доступ: http://localhost:{PORT}")
        print(f"🌐 Сетевой доступ: http://0.0.0.0:{PORT}")
        print("⏹️  Для остановки нажмите Ctrl+C")
        
        # Автоматически открыть браузер
        try:
            webbrowser.open(f'http://localhost:{PORT}')
        except:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Сервер остановлен")

if __name__ == "__main__":
    main() 