import threading
import time
import socket
import sys
import os
import keyboard
from clock import Clock
import traceback


class App:

    def __init__(self, host="vps.i-h.no", port=5050):
        self.running = True
        self.port = port
        self.host = host
        # first thing to grab from server
        # NOTE: bool(0) == False
        self.client_id = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:  # try to connect to server
            self.connecting = True  # decoration
            sys.stdout.write(
                "\u001b[30;1m-- \u001b[32;1mConnecting to \u001b[37;1m" + self.host + "\u001b[0m")
            threading.Thread(target=self.visual_loading,
                             name="Loading").start()
            sys.stdout.flush()
            self.socket.connect((self.host, self.port))
            self.connecting = False  # connected successfully
            time.sleep(0.25)
            print(
                f"\u001b[30;1m== \u001b[32;1mConnected to server \u001b[37;1m{self.host}\u001b[0m")
        except ConnectionRefusedError:
            self.connecting = False
            self.running = False
            time.sleep(0.25)
            print(
                "\u001b[31;1m[Error] \u001b[0m\u001b[35mServer could not be found!\u001b[0m")
            self.socket.close()  # close socket
            print(
                "\u001b[30;1m-- \u001b[37;1mExited program\u001b[30;1m --\u001b[0m")
            exit()  # exit program

        try:  # get client index from server
            index, server_size, * \
                _ = self.socket.recv(1024).decode("utf-8").split()
            if index == "":
                raise ConnectionResetError
            else:
                self.client_id = int(index)  # from server
                self.server_size = int(server_size)
        except ConnectionResetError:
            self.running = False
            self.connecting = False
            self.socket.close()
            print("\n-- Disconnected from server --")
            exit()

        with open("map.txt", "r") as f:  # read map from file
            def func(item):
                return list(item)
            self.content = list(map(func, f.readlines()))
        # player like info
        for line in self.content:
            if str(self.client_id) in line:
                self.player_y = self.content.index(line)
                self.player_x = line.index(str(self.client_id))
                break
        if not hasattr(self, "player_x"):
            self.running = False
            self.socket.close()
            print("\n\u001b[30;1m-- \u001b[37;1mServer is full \u001b[30;1m--")
            print(
                "\u001b[30;1m==  \u001b[31;1mDisconnected  \u001b[30;1m==\u001b[0m")
            exit()
        self.inventory = []

        self.update()
        threading.Thread(target=self.rpc_listen, name="RPC Listen").start()
        self.mainloop()

    def visual_loading(self):
        i = 0
        sys.stdout.write("\u001b[30;1m")
        while self.connecting:
            sys.stdout.write(".")
            i += 1
            if i % 3 == 0:
                i = 0
                n = 3
                sys.stdout.write(f"\u001b[{n}D")
                sys.stdout.write(" " * n)
                sys.stdout.write(f"\u001b[{n}D")
            sys.stdout.flush()
            time.sleep(0.1)
        print("." * (3 - i) + "\u001b[0m")  # also newline

    def update(self):
        first, *rest = self.content
        sys.stdout.write("".join(first))
        for line in rest:
            sys.stdout.write("".join(line))
        sys.stdout.write(f"\u001b[{len(self.content) -1}A\r")

    def rpc_send(self, attr):
        string = f"{self.client_id} {attr} {getattr(self, attr)}"
        data = bytes(string, "utf-8")
        self.socket.send(data)

    def rpc_listen(self):
        while self.running:
            try:
                msg = self.socket.recv(1024)  # is bytes
                if not msg:  # if empty msg
                    continue
                self.on_recv(msg.decode("utf-8"))
            except Exception as error:
                time.sleep(1)
                print(
                    f"Client [{self.client_id}] had an unexpected error: {error}")
                traceback.print_exc()
                time.sleep(5)
                return

    def on_recv(self, msg):
        cid, attr, value, *_ = msg.split()
        #setattr(self.clients[cid], attr, value)
        # player like info
        for line in self.content:
            if str(cid) in line:
                player_y = self.content.index(line)
                player_x = line.index(str(cid))
                break
        try:
            # NOTE: ALLWAYS EMPTY STRING
            assert player_x
            self.content[player_y][player_x] = " "
            if attr == "player_x":
                player_x = int(value)
            elif attr == "player_y":
                player_y = int(value)
            self.content[player_y][player_x] = str(cid)
        except (NameError, IndexError) as error:
            time.sleep(1)
            print(error, end="")
            time.sleep(3)
            return

    def mainloop(self):
        clock = Clock(16)
        while self.running:
            # y
            old_y = self.player_y
            if keyboard.is_pressed("w"):
                self.player_y -= 1
            if keyboard.is_pressed("s"):
                self.player_y += 1
            curr = self.content[self.player_y][self.player_x]
            if curr == " ":
                # edit last pos
                self.content[old_y][self.player_x] = curr
                self.content[self.player_y][self.player_x] = str(
                    self.client_id)
                self.rpc_send("player_y")
            else:
                self.player_y = old_y
            # x
            old_x = self.player_x
            if keyboard.is_pressed("a"):
                self.player_x -= 1
            if keyboard.is_pressed("d"):
                self.player_x += 1
            curr = self.content[self.player_y][self.player_x]
            if curr == " ":
                # edit last pos
                self.content[self.player_y][old_x] = curr
                self.content[self.player_y][self.player_x] = str(
                    self.client_id)
                self.rpc_send("player_x")
            else:
                self.player_x = old_x
            self.update()
            clock.tick()


if __name__ == "__main__":
    # activate ANSI ESCAPE codes
    os.system("")
    # init
    app = App(port=5050)
