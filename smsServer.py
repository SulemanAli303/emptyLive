import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# Global list to store connected socket clients
socket_clients = []

# Hardcoded username and password for authorization
USERNAME = "sulemanali303"
PASSWORD = "Suleman@12"

# HTTP server to receive POST requests
class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Check Authorization header
        auth_header = self.headers.get('Authorization')
        if not auth_header or not self.is_authorized(auth_header):
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="Access to the server"')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'error', 'message': 'Unauthorized'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        # Read the content length and parse the received data
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        try:
            # Parse the JSON data
            data = json.loads(post_data)

            # Validate the required structure
            if not ("to" in data and "body" in data):
                raise ValueError("Invalid JSON structure. Required keys: 'to', 'body'.")

            # Log the received data
            print(f"Received POST data: {post_data}")

            # Send the data to all connected socket clients
            for client in socket_clients:
                try:
                    client.sendall(post_data.encode('utf-8'))
                except Exception as e:
                    print(f"Failed to send data to a client: {e}")

            # Send an HTTP response back to the client
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'success', 'message': 'Data forwarded to socket clients.'}
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except (json.JSONDecodeError, ValueError) as e:
            # Handle invalid JSON or missing keys
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'error', 'message': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))

    def is_authorized(self, auth_header):
        import base64
        try:
            # Decode the Basic auth header
            auth_type, encoded_credentials = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                return False

            credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = credentials.split(':', 1)

            # Check against hardcoded username and password
            return username == USERNAME and password == PASSWORD
        except Exception as e:
            print(f"Authorization error: {e}")
            return False

# Function to handle socket clients
def handle_socket_client(client_socket, client_address):
    print(f"New socket client connected: {client_address}")
    socket_clients.append(client_socket)
    try:
        while True:
            # Keep the connection alive; the server doesn't expect to receive data
            data = client_socket.recv(1024)
            if not data:
                break
    except Exception as e:
        print(f"Socket client error: {e}")
    finally:
        print(f"Socket client disconnected: {client_address}")
        socket_clients.remove(client_socket)
        client_socket.close()

# Function to start the socket server
def start_socket_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8086))
    server_socket.listen(5)
    print("Socket server running on port 8086...")

    while True:
        client_socket, client_address = server_socket.accept()
        threading.Thread(target=handle_socket_client, args=(client_socket, client_address), daemon=True).start()

# Main function to start the HTTP and socket servers
if __name__ == "__main__":
    # Start the socket server in a separate thread
    threading.Thread(target=start_socket_server, daemon=True).start()

    # Start the HTTP server
    http_server = HTTPServer(('0.0.0.0', 8085), RequestHandler)
    print("HTTP server running on port 8085...")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down servers...")
        http_server.server_close()
