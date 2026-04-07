import socket
import threading

class ClientHandler:
    def __init__(self, client_socket, address, server):
        self.client = client_socket
        self.address = address
        self.server = server
        self.running = True

    def start(self):
        thread = threading.Thread(target=self.handle)
        thread.start()

    def handle(self):
        print(f"Cliente conectado: {self.address}")

        while self.running:
            try:
                message = self.client.recv(1024)

                if not message:
                    break

                self.server.broadcast(message, self)

            except Exception as e:
                print(f"Erro com {self.address}: {e}")
                break

        self.disconnect()

    def send(self, message):
        try:
            self.client.send(message)
        except:
            self.disconnect()

    def disconnect(self):
        if self.running:
            self.running = False
            print(f"Cliente desconectado: {self.address}")
            self.server.remove_client(self)
            self.client.close()


class ChatServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.lock = threading.Lock()

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"Servidor rodando em {self.host}:{self.port}")

        while True:
            client_socket, address = self.server.accept()
            client_handler = ClientHandler(client_socket, address, self)

            with self.lock:
                self.clients.append(client_handler)

            client_handler.start()

    def broadcast(self, message, sender):
        with self.lock:
            for client in self.clients.copy():
                if client != sender:
                    client.send(message)

    def remove_client(self, client):
        with self.lock:
            if client in self.clients:
                self.clients.remove(client)


if __name__ == "__main__":
    server = ChatServer()
    server.start()