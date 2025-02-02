import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import base64
import json
import sqlite3
import time

# Database Setup
def init_db():
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            subject TEXT,
            status TEXT,
            timestamp INTEGER
        )
    ''')
    conn.commit()
    conn.close()
init_db()
# Global list to store connected socket clients
socket_clients = []
message_queue = []
lock = threading.Lock()

# Hardcoded username and password for authorization
USERNAME = "sulemanali303"
PASSWORD = "Suleman@12"
HOST_SERVER = "0.0.0.0"

# Function to add message to the database
def add_message_to_db(content,subject, status="pending"):
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (content,subject, status, timestamp) VALUES (?, ? ,?, ?)", (content,subject, status, int(time.time())))
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return message_id

# Function to update message status in the database
def update_message_status(message_id, status):
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET status = ? WHERE id = ?", (status, message_id))
    conn.commit()
    conn.close()

# HTTP server to receive POST and GET requests
class RequestHandler(BaseHTTPRequestHandler):
    def send_errors(self,error,code):
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response_body = {
            "isSuccess":False,
            "message":error
        }
        self.wfile.write(json.dumps(response_body).encode('utf-8'))
    def write_response(self,data,message):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response_body = {
            "isSuccess":True,
            "message":message,
            "data":data
        }
        self.wfile.write(json.dumps(response_body).encode('utf-8'))

    def do_POST(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not self.is_authorized(auth_header):
            self.send_errors("Not Authorized",401)
            return
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            message_data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_errors("Invalid JSON",400)
            return
        if self.path.startswith('/send-sms'):
            message_content = message_data.get('message')
            subject = message_data.get('to')
            if message_content:
                message_id = add_message_to_db(message_content,subject)
                data = {
                    "message_id" : message_id,
                    "message_content":message_content,
                    "message_subject":subject
                }
                with lock:
                    if socket_clients:
                        for client in socket_clients:
                            try:
                                client.sendall(json.dumps(data).encode('utf-8'))
                                update_message_status(message_id, 'sent_device')
                            except:
                                socket_clients.remove(client)
                    else:
                        message_queue.append((message_id, message_content,subject))
                self.write_response(data,"Message received and sent to modem")
            else:
                self.send_errors("Missing message content",400)
        elif self.path.startswith('/update-sms'):
            message_id = message_data.get('message_id')
            message_status = message_data.get('message_status')
            if message_id and message_status:
                with lock:
                    update_message_status(message_id,message_status)
                    self.write_response(message_data,"Message status updated")
            else:
                self.send_errors("Missing message content",400)
        else:
            self.send_errors("Request Not Found",404)
    def do_GET(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not self.is_authorized(auth_header):
            self.send_errors("Not Authorized",401)
            return
        if self.path.startswith('/fetch-sms'):
            query = self.path.split('?')[-1]
            params = dict(qc.split('=') for qc in query.split('&') if '=' in qc)
            page = int(params.get('page', 1))
            limit = int(params.get('limit', 10))
            offset = (page - 1) * limit
            conn = sqlite3.connect('messages.db')
            cursor = conn.cursor()
            # Get total count of messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_record = cursor.fetchone()[0]
            # Fetch messages in descending order of `id`
            cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
            messages = cursor.fetchall()
            conn.close()
            # Prepare JSON response
            response = {
                "messages": messages,  # Ensure messages are in expected format (list of dicts if needed)
                "currentPage": page,
                "limit": limit,
                "totalRecord": total_record,
                "currentCount": len(messages)
            }
            self.write_response(response, "Messages fetched successfully")
        else:
            self.send_errors("Request Not Found",404)

    def is_authorized(self, auth_header):
        try:
            auth_type, encoded_credentials = auth_header.split(' ')
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded_credentials.split(':')
            print(username,password,encoded_credentials)
            return username == USERNAME and password == PASSWORD
        except Exception:
            return False

# Function to handle socket client
def handle_client(client_socket):
    with lock:
        socket_clients.append(client_socket)
    while True:
        try:
            response = client_socket.recv(1024000).decode('utf-8')
            if response:
                json_data = json.JSONDecoder().decode(response)
                message_id = json_data.get("message_id")
                status = json_data.get("message_status")
                update_message_status(int(message_id), status.strip())
        except:
            with lock:
                socket_clients.remove(client_socket)
            break

# Function to accept socket connections
def start_socket_server():
    server_host = HOST_SERVER
    server_port = 8086
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_host, server_port))
    server_socket.listen(5)

    print(f"Socket server listening on {server_host}:{server_port}")

    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,)).start()

# Function to retry sending queued messages
def retry_queued_messages():
    while True:
        with lock:
            for message in list(message_queue):
                message_id, message_content,subject = message
                current_time = int(time.time())
                conn = sqlite3.connect('messages.db')
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp FROM messages WHERE id = ?", (message_id,))
                timestamp = cursor.fetchone()[0]
                conn.close()
                data = {
                    "message_id" : message_id,
                    "message_content": message_content,
                    "message_subject": subject
                }
                if current_time - timestamp > 1200:  # 20 minutes timeout
                    update_message_status(message_id, 'timeout')
                    message_queue.remove(message)
                elif socket_clients:
                    for client in socket_clients:
                        try:
                            client.sendall(json.dumps(data).encode('utf-8'))
                            update_message_status(message_id, 'sent_device')
                            message_queue.remove(message)
                        except:
                            socket_clients.remove(client)
        time.sleep(10)

# Start servers and retry thread
threading.Thread(target=start_socket_server, daemon=True).start()
threading.Thread(target=retry_queued_messages, daemon=True).start()
http_server = HTTPServer((HOST_SERVER, 8085), RequestHandler)
print("HTTP server running on port 8080")
http_server.serve_forever()

