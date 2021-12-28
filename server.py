import sys
import threading
import socket
import time
import os


class ClientInfo:
    def __init__(self, id: int, x: float, y: float):
        """Client object to store client info

        Args:
            id (int): if of client on server
            x (float): x position
            y (float): y position
        """
        self.id = id
        self.x = x
        self.y = y
        self.inventory = []
        self.socket = None
        self.address = None

    def clear(self):
        """Clears socket object and address
        """
        if self.socket != None:
            self.socket.close()
            self.socket = None
        self.address = None


class Server:

    def __init__(self, server_size: int = 2, host: str = "vps.i-h.no", port: int = 5050):
        self.running = True
        self.port = port
        self.host = host
        self.server_size = server_size
        # make client containers
        self.clients = []
        # read map data and get player pos
        with open("./map.txt", "r") as f:
            self.content = []
            for line in f.readlines():
                self.content.append(list(line.rstrip()))
        for index in range(self.server_size):
            cid = index + 1
            for line in self.content:
                if str(cid) in line:
                    y = self.content.index(line)
                    x = line.index(str(cid))
                    # NOTE: might give error if not on map
                    client = ClientInfo(cid, x, y)
                    self.clients.append(client)
                    break
        # connect
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(
                "\u001b[30;1m-- \u001b[32;1mServer startup \u001b[30;1m--\u001b[0m")
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            print(
                "\u001b[30;1m== \u001b[32;1mServer is running\u001b[30;1m...\u001b[0m")
        except Exception as error:
            print("Server error:", error)  # DEBUG
            self.shutdown()
        # start server
        self.running = True
        threading.Thread(target=self.handle_clients).start()  # looping
        while self.running:
            string = input("")
            do_shutdown = False
            try:
                if string.startswith("exit"):
                    do_shutdown = True
                elif string.startswith("kick"):
                    client_id = int(string.split(" ")[1]) - 1
                    if self.clients[client_id].socket != None:
                        print(
                            f"- Kicking client [{self.clients[client_id].address[1]}]")
                        # cause error later
                        # clear later
                        self.clients[client_id].socket.close()
                    else:
                        print(
                            f"= Client {client.id} has no socket object assigned")
                elif string.startswith("list"):
                    for client in self.clients:
                        print("-", "Client", client.id, client.address)
                elif string.startswith("cls"):
                    os.system("cls")
                    print(
                        "\u001b[30;1m-- \u001b[32;1mServer \u001b[30;1m--\u001b[0m")
                else:
                    print("| [Invalid]", string)
            except (TypeError, IndexError) as error:
                print("[Error]", type(error).__name__, error)
            # shutdown
            if do_shutdown:
                self.shutdown()

    def handle_clients(self):
        while self.running:
            try:
                client = self.socket.accept()
            except socket.timeout:
                continue
            try:
                clientsocket, address = client
                index = 0
                for client in self.clients:
                    if client.socket != None:
                        index += 1
                msg = "$".join([
                    str(index + 1),
                    str(self.server_size),
                    self.stringify(self.content)
                ])
                clientsocket.send(bytes(msg, "utf-8"))
                # keep track of new client socket in existing ClientInfo obj
                for client in self.clients:
                    if client.socket == None:
                        client.address = address
                        client.socket = clientsocket
                        break
            except BrokenPipeError:
                client.clear()  # clear info

            def func(): self.handle_recv(client)  # lambda
            threading.Thread(target=func).start()  # looping
            print(f"-- Client [{client.address[1]}] has connected --")

    def shutdown(self):
        self.running = False
        # dummy join so cancel self.socket.accept
        print(f"Client size, size ({len(self.clients)})")
        print("- Making dummy")
        dummysock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("- Connecting dummy")
        try:
            dummysock.connect((self.host, self.port))
            time.sleep(0.1)
            print("- Connected dummy")
        except ConnectionRefusedError:
            print("- Connection failed, continuing")
        # clear all sockets (including dummy)
        print(f"- Clearing clients, size ({len(self.clients)})")
        for client in self.clients:
            if client.socket != None:
                client.socket.close()
        # close socket
        self.socket.close()
        print("-- Server shutdown --")

    def stringify(self, content: list[list[str, ...], ...]) -> str:
        """Stringifies content from 2D array (with str elements)

        Args:
            content (list[list[str, ...], ...]): content to stringify

        Returns:
            str: content as one string
        """
        first, *rest = content
        value = "".join(first)
        for line in rest:
            value += "\n" + "".join(line)
        return value

    def handle_recv(self, client):
        while self.running:
            try:
                request = client.socket.recv(1024)  # is bytes
                if not request:  # if empty request
                    continue
            except (Exception, ConnectionAbortedError) as error:
                if type(error) is ConnectionAbortedError:
                    print(f"= Client [{client.address[1]}] has disconnected")
                    client.clear()
                elif client in self.clients:
                    print(
                        f"= Client [{client.address[1]}] had an unexpected error: {type(error).__name__}")
                    client.clear()  # clear info
                return
            self.handle_request(client, request.decode("utf-8"))

    def handle_request(self, client, request):
        cid, attr, value, *_rest = request.split("$")
        print(cid, attr, value)
        # if _rest:
        #     print("REST", _rest)
        client = self.clients[int(cid) - 1]
        if attr.startswith("x"):
            try:
                curr = self.content[client.y][client.x + int(value)]
            except IndexError:
                return  # ignores error
            if curr == " ":
                # edit last pos
                self.content[client.y][client.x] = curr
                self.content[client.y][client.x + int(value)] = str(client.id)
                client.x += int(value)
        elif attr.startswith("y"):
            try:
                curr = self.content[client.y + int(value)][client.x]
            except IndexError:
                return  # ignores error
            if curr == " ":
                # edit last pos
                self.content[client.y][client.x] = curr
                self.content[client.y + int(value)][client.x] = str(client.id)
                client.y += int(value)
        # broadcast content
        message = "content$" + self.stringify(self.content)
        self.broadcast(client, bytes(message, "utf-8"))

    def broadcast(self, sender, message: bytes):  # message is bytes
        for client in self.clients:
            # if client == sender:
            #    continue
            if client.socket == None:
                continue
            try:
                client.socket.send(message)
            except BrokenPipeError:
                client.clear()  # clear info

    def rpc_send(self, client, message: str):
        if client.socket == None:
            return
        try:
            message = bytes(message, "utf-8")
            client.socket.send(message)
        except BrokenPipeError:
            client.clear()  # clear info


if __name__ == "__main__":
    # init
    server = Server(2, host="127.0.0.1")
