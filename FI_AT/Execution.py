from DataStream import *
from SignalHub import *
from Strategy import *
from typing import List
import time

class Execution:
    def __init__(self, signal_hub: SignalHub):
        self.signal_hub = signal_hub

    def run(self):
        raise NotImplementedError("run method must be implemented in subclasses")

class BacktestExecution(Execution):
    def __init__(self, signal_hub: SignalHub, interval: float = 0.1):
        super().__init__(signal_hub)
        #self.interval = interval  # seconds between steps

    def run(self):
        # DataStream 내부의 data를 한 줄씩 feed하는 방식
        data_stream = self.signal_hub._data_stream
        total_len = len(data_stream.data)
        for idx in range(total_len):
            data_stream.data = data_stream.data.iloc[:idx+1]
            self.signal_hub.notify_strategies()
            # time.sleep(self.interval)

class LiveExecution(Execution):
    def __init__(self, signal_hub: SignalHub, poll_interval: float = 1.0):
        super().__init__(signal_hub)
        self.poll_interval = poll_interval

    def run(self):
        while True:
            self.signal_hub.notify_strategies()
            time.sleep(self.poll_interval)