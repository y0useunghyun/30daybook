# 로컬 미리보기 서버: 질감을 한꺼번에 받아도 연결이 안 끊기게. python3 serve.py (30daybook 폴더에서)
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
class Server(ThreadingHTTPServer): request_queue_size = 256
Server(('127.0.0.1', 8030), SimpleHTTPRequestHandler).serve_forever()
