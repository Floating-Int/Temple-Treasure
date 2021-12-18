import time


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
