import threading
import time
import socket
import sys
import os
import keyboard


class Clock:
    def __init__(self, tps):
        self.tps = tps
        self.last = time.time()

    def tick(self):
        now = time.time()
        tick_rate = 1.0 / self.tps
        diff = now - self.last
        recover = tick_rate - diff
        if recover > 0:
            time.sleep(recover)
        self.last = time.time()


class App:

    def __init__(self, host="vps.i-h.no", port=5050):
        self.running = True
        self.port = port
        self.host = host
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:  # try to connect to server
            self.connecting = True  # loading decoration
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
            raw = self.socket.recv(1024).decode("utf-8")
            index, server_size, content = raw.split("$")
            if index == "":
                raise ConnectionResetError
            else:
                self.cid = int(index)  # from server
                self.server_size = int(server_size)
                self.update(content)  # content is single string
        except ConnectionResetError:
            self.running = False
            self.connecting = False
            self.socket.close()
            print("\n-- Disconnected from server --")
            exit()

        def func(item):
            return list(item)
        self.content = list(map(func, content.split("\n")))

        if self.cid > self.server_size:
            self.running = False
            self.socket.close()
            print("\n\u001b[30;1m-- \u001b[37;1mServer is full \u001b[30;1m--")
            print(
                "\u001b[30;1m==  \u001b[31;1mDisconnected  \u001b[30;1m==\u001b[0m")
            exit()

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

    def update(self, content):
        print(content, end="\u001b[9A\r")

    def rpc_send(self, attr: str, value):
        string = f"{self.cid}${attr}${value}"
        data = bytes(string, "utf-8")
        try:
            self.socket.send(data)
        except ConnectionResetError:
            self.running = False
            self.socket.close()
            time.sleep(0.5)
            print(
                "\u001b[30;1m-- \u001b[31;1mDisconnected or kicked \u001b[30;1m--\u001b[0m\n")

    def rpc_listen(self):
        while self.running:
            try:
                msg = self.socket.recv(1024)  # is bytes
                if not msg:  # if empty msg
                    continue
                self.on_recv(msg.decode("utf-8"))
            except ConnectionResetError as error:
                self.running = False
                self.socket.close()
                if type(error) is ConnectionResetError:
                    time.sleep(0.5)
                    print(
                        "\u001b[30;1m-- \u001b[37;1mDisconnected or kicked \u001b[30;1m--\u001b[0m\n")
                    return
                else:
                    self.running = False
                    self.socket.close()
                    time.sleep(0.5)
                    print(
                        f"\u001b[31;1m[Error] \u001b[37;1mEncountered unknow bug\u001b[0m")
                    return

    def on_recv(self, message: str):
        """Receives information from server as one string.
        Message is then split on '$' to unpack attr and value

        Args:
            message (str): message received
        """
        try:
            # rest is either possible duplicant or possibly double message combined
            attr, value, *_rest = message.split("$")
        except ValueError:
            return  # ignore error. ignore request
        if attr.startswith("content"):
            self.content = value
            self.update(value)
        elif attr.startswith("kick"):
            self.running = False
            self.socket.close()
            time.sleep(0.5)
            print(
                "\u001b[30;1m-- \u001b[31;1mKicked from server \u001b[30;1m--\u001b[0m\n")
        elif attr.startswith("finished"):
            print("\u001b[3B\u001b[62C" + "\u001b[32;1m" +
                  "Finished" + "\u001b[0m" + "\u001b[3A", end="\r")

    def mainloop(self):
        clock = Clock(8)
        while self.running:
            clock.tick()
            # y-axis
            if keyboard.is_pressed("w"):
                self.rpc_send("y", -1)
            if keyboard.is_pressed("s"):
                self.rpc_send("y", 1)
            # x-axis
            if keyboard.is_pressed("a"):
                self.rpc_send("x", -1)
            if keyboard.is_pressed("d"):
                self.rpc_send("x", 1)


if __name__ == "__main__":
    # activate ANSI ESCAPE codes
    os.system("")
    # init
    app = App(port=5050, host="127.0.0.1")
