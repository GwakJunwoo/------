from DataStream import *
from SignalHub import *
from Strategy import *
from Position import PositionManager
from typing import List
import time

class Execution:
    def __init__(self, signal_hub: SignalHub, position_manager: PositionManager):
        self.signal_hub = signal_hub
        self.position_manager = position_manager

    def run(self):
        raise NotImplementedError("run method must be implemented in subclasses")

class BacktestExecution(Execution):
    def __init__(self, signal_hub: SignalHub, position_manager: PositionManager, interval: float = 0.1):
        super().__init__(signal_hub, position_manager)
        #self.interval = interval  # seconds between steps

    def run(self):
        data_stream = self.signal_hub._data_stream
        # 원본 데이터 따로 저장
        original_data = data_stream.data.copy()
        total_len = len(original_data)
        for idx in range(total_len):
            # 원본에서 슬라이스
            data_stream.data = original_data.iloc[:idx+1]
            self.signal_hub.notify_strategies()
            # time.sleep(self.interval)

class LiveExecution(Execution):
    def __init__(self, signal_hub: SignalHub, position_manager: PositionManager, poll_interval: float = 1.0):
        super().__init__(signal_hub, position_manager)
        self.poll_interval = poll_interval

    def run(self):
        while True:
            self.signal_hub.notify_strategies()
            time.sleep(self.poll_interval)