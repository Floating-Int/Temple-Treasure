import sys
import threading
import socket
import time
import os
from typing import Any


__version__ = "2.1.1"
__author__ = "FloatingInt"


class ClientInfo:
    """Used to store information about clients and game data associated.
    Use method 'clear' to wipe socket related information.
    Game data is never wiped
    """

    def __init__(self, id: int, x: int, y: int) -> None:
        """Client object to store client info

        Args:
            id (int): if of client on server
            x (int): x position
            y (int): y position
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


class Structure:
    """Base class for structures to interact with on the map

    Returns:
        Structure: subclass object of Structure
    """
    symbol = "^"  # error symbol

    def __init__(self, id: int, color: str, x: int, y: int) -> None:
        self.id = id
        self.color = color
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return self.color + self.symbol + "\u001b[0m"


class Goal(Structure):
    """Structure: Goal
    """
    symbol = "?"


class Key(Structure):
    """Structure: Key
    """
    symbol = "!"


class Door(Structure):
    """Structure: Door
    """
    symbol = "&"


class Server:
    """Server to handle requests from clients and broadcasting of updates.
    The middleman (serverside implementation)
    """

    def __init__(self, server_size: int = 2, host: str = "vps.i-h.no", port: int = 5050) -> None:
        """Init Server and automatically start it

        Args:
            server_size (int, optional): maximum allowed clients. Defaults to 2.
            host (str, optional): server host. Defaults to "vps.i-h.no".
            port (int, optional): server port. Defaults to 5050.
        """
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
        # set keys, doors and goal manually, for now...
        self.keys = [
            Key(1, "\u001b[32m", 4, 8),
            Key(2, "\u001b[35m", 3, 4),
            Key(3, "\u001b[33m", 17, 8),
            Key(4, "\u001b[34m", 45, 1),
            Key(5, "\u001b[36m", 13, 1)
        ]
        self.doors = [
            Door(1, "\u001b[32m", 8, 4),
            Door(2, "\u001b[35m", 5, 6),
            Door(3, "\u001b[33m", 37, 2),
            Door(4, "\u001b[34m", 21, 3),
            Door(5, "\u001b[36m", 52, 7)
        ]
        self.goal = Goal(-1, "\u001b[35m", 55, 2)
        self.objects = self.keys + self.doors + [self.goal]
        for obj in self.objects:
            x, y = obj.x, obj.y
            self.content[y][x] = obj.color + obj.symbol + "\u001b[0m"
        # ---

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

        # server commands
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
                        # tell client to disconnect
                        # clear later
                        self.rpc_send(self.clients[client_id], "kick", 1)
                        # FIXME: send msg to client so it disconnects
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

    def handle_clients(self) -> None:
        """Accepts client connections and starts a thread to handle recieve
        """
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
            except ConnectionError:
                client.clear()  # clear info

            def func(): self.handle_recv(client)  # lambda
            threading.Thread(target=func).start()  # looping
            print(f"-- Client [{client.address[1]}] has connected --")

    def shutdown(self) -> None:
        """Shutdown procedural to shutdown Server
        """
        self.running = False
        # dummy join so cancel self.socket.accept
        print(f"Client size, size ({len(self.clients)})")
        print("- Making dummy")
        dummysock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("- Connecting dummy")
        try:
            dummysock.connect((self.host, self.port))
            time.sleep(0.1)
            print("= Connected dummy")
        except ConnectionRefusedError:
            print("- Connection failed, continuing")
        # clear all sockets (including dummy)
        print(f"- Clearing clients, size ({len(self.clients)})")
        for client in self.clients:
            if client.socket != None:
                client.socket.close()
        # close socket
        self.socket.close()
        print("== Server shutdown ==")

    def stringify(self, content: list) -> str:
        """Stringifies content from 2D array (with str elements)

        Args:
            content (list): content to stringify

        Returns:
            str: content as one string
        """
        first, *rest = content
        value = "".join(first)
        for line in rest:
            value += "\n" + "".join(line)
        return value

    def handle_recv(self, client: ClientInfo) -> None:
        """Separate thread to handle recieve.
        One thread per client

        Args:
            client (ClientInfo): client object to store data in
        """
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

    def handle_request(self, client: ClientInfo, request: str) -> None:
        """Decision tree to determine what do do with a request from client

        If the server does not respond, the request is treated as declined

        Format of argument request: f"{attr}${value}"

        Args:
            client (ClientInfo): client object to store data in
            request (str): request as string
        """
        cid, attr, value, *_rest = request.split("$")
        print(cid, attr, value)
        # if _rest:
        #     print("REST", _rest)
        client = self.clients[int(cid) - 1]

        # x-axis
        if attr.startswith("x"):
            try:
                # clamp between 1 and -1. won't be 0
                num = min(max(int(value), -1), 1)
                curr = self.content[client.y][client.x + num]
            except IndexError:
                return  # ignores error

            if curr == " ":
                # edit last pos
                self.content[client.y][client.x] = curr
                self.content[client.y][client.x + num] = str(client.id)
                client.x += num

            elif Key.symbol in curr:
                for key in self.keys:
                    print((key.x, key.y), (client.x + num, client.y))
                    if (key.x, key.y) == (client.x + num, client.y):
                        client.inventory.append(key)
                        break
                self.content[client.y][client.x] = " "
                self.content[client.y][client.x + num] = str(client.id)
                client.x += num
                print(client.id, "gained key:", client.inventory)

            elif Door.symbol in curr:
                for door in self.doors:
                    if (door.x, door.y) == (client.x + num, client.y):
                        # got current door
                        for item in client.inventory:
                            if type(item) == Key:
                                if door.id == item.id:
                                    # do stuff
                                    client.inventory.remove(item)
                                    self.content[client.y][client.x] = " "
                                    self.content[
                                        client.y][client.x + num] = str(client.id)
                                    client.x += num
                                    break
                        break

            elif Goal.symbol in curr:
                self.content[client.y][client.x] = " "
                self.content[client.y][client.x + num] = str(client.id)
                client.x += num
                message = f"{'finished'}${1}"
                self.broadcast(message)
                print("= Game finished!")

        # y-axis
        elif attr.startswith("y"):
            try:
                # clamp between 1 and -1. won't be 0
                num = min(max(int(value), -1), 1)
                curr = self.content[client.y + num][client.x]
            except IndexError:
                return  # ignore error. ignore request

            if curr == " ":
                # edit last pos
                self.content[client.y][client.x] = curr
                self.content[client.y + num][client.x] = str(client.id)
                client.y += num

            elif Key.symbol in curr:
                for key in self.keys:
                    print((key.x, key.y), (client.x, client.y + num))
                    if (key.x, key.y) == (client.x, client.y + num):
                        client.inventory.append(key)
                        break
                self.content[client.y][client.x] = " "
                self.content[client.y + num][client.x] = str(client.id)
                client.y += num
                print(client.id, "gained key:", client.inventory)

            elif Door.symbol in curr:
                for door in self.doors:
                    if (door.x, door.y) == (client.x, client.y + num):
                        # got current door
                        for item in client.inventory:
                            if type(item) == Key:
                                if door.id == item.id:
                                    # do stuff
                                    client.inventory.remove(item)
                                    self.content[client.y][client.x] = " "
                                    self.content[
                                        client.y + num][client.x] = str(client.id)
                                    client.y += num
                                    break
                        break

            elif Goal.symbol in curr:
                self.content[client.y][client.x] = " "
                self.content[client.y + num][client.x] = str(client.id)
                client.y += num
                message = f"{'finished'}${1}"
                self.broadcast(message)
                print("= Game finished!")

        # broadcast content to all clients (updated version)
        message = "content$" + self.stringify(self.content)
        self.broadcast(message)

    def broadcast(self, message: str) -> None:
        """Broadcasts a message to all clients.
        Message is recieved as bytes

        Format: f"{attr}${value}"

        Args:
            message (str): message to broadcast
        """
        data = bytes(message, "utf-8")
        for client in self.clients:
            if client.socket == None:
                continue
            try:
                client.socket.send(data)
            except ConnectionError:
                client.clear()  # clear info

    def rpc_send(self, client: ClientInfo, attr: str, value: Any) -> None:
        """Send a message to a spesific client.

        Format: f"{attr}${value}"

        Args:
            client (ClientInfo):  client object to store data in
            attr (str): name of attribute to update
            value (str): value to update atribute to
        """
        if client.socket == None:
            return
        try:
            message = f"{attr}${value}"
            data = bytes(message, "utf-8")
            client.socket.send(data)
        except ConnectionError:
            client.clear()  # clear info


if __name__ == "__main__":
    # init
    server = Server(2, host="127.0.0.1")
