import threading
import socket


class Server:

    def __init__(self, server_size: int = 2, host: str = "vps.i-h.no", port: int = 5050):
        self.running = True
        self.port = port
        self.host = host
        self.server_size = server_size
        self.clients = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print("-- Server startup --")
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            print("Server is running...")
        except Exception as error:
            print("Server error:", error)  # DEBUG
            self.shutdown()
            print("-- Server shutdown --")
        self.running = True
        threading.Thread(target=self.handle_client).start()  # looping

    def handle_client(self):
        while self.running:
            try:
                client = self.socket.accept()
            except socket.timeout:
                continue
            try:
                clientsocket, _address = client
                msg = str(len(self.clients) + 1) + " " + str(self.server_size)
                clientsocket.send(bytes(msg, "utf-8"))
            except BrokenPipeError:
                self.clients.remove(client)
            self.clients.append(client)  # keep track of new client
            def func(): self.handle_recv(client)  # lambda
            threading.Thread(target=func).start()  # looping
            print(f"-- Client [{client[1][1]}] has connected --")

    def shutdown(self):
        self.running = False
        for client in self.clients:
            clientsocket, _address = client
            clientsocket.close()
        self.socket.close()
        print("-- Server shutdown --")

    def handle_recv(self, client):
        # NOTE: this is old code that is a placeholder
        clientsocket, address = client
        while self.running:
            try:
                msg = clientsocket.recv(1024)  # is bytes
                if not msg:  # if empty msg
                    continue
            except Exception as error:
                print(
                    f"Client [{address[1]}] had an unexpected error: {error}")
                if client in self.clients:
                    self.clients.remove(client)
                return
            index = self.clients.index(client)
            self.broadcast(client, msg)
            print(f"[{address[1]}]", msg.decode("utf-8"))
            #print(f"[{index}]", msg.decode("utf-8"))

    def broadcast(self, sender, message):  # message is bytes
        for client in self.clients:
            if client == sender:
                continue
            clientsocket, _address = client
            try:
                clientsocket.send(message)
            except BrokenPipeError:
                self.clients.remove(client)


if __name__ == "__main__":
    # init
    server = Server(2, host="127.0.0.1")
