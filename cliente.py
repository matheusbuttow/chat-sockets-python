import socket
import threading

class ChatClient:
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        self.client.connect((self.host, self.port))
        print("Conectado ao servidor!")

        threading.Thread(target=self.receive).start()
        threading.Thread(target=self.send).start()

    def receive(self):
        while True:
            try:
                message = self.client.recv(1024)

                if not message:
                    break

                print("\nMensagem:", message.decode('utf-8'))

            except Exception as e:
                print("Erro:", e)
                break

        self.client.close()

    def send(self):
        while True:
            try:
                message = input()
                self.client.send(message.encode('utf-8'))
            except:
                break


if __name__ == "__main__":
    client = ChatClient()
    client.start()