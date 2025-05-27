from typing import List, Dict, DefaultDict
from Strategy import *
from DataStream import *
import numpy as np
import pandas as pd

class SignalHub:
    def __init__(self, data_stream: DataProvider):
        self._strategies: List[BaseStrategy] = []
        self._data_stream = data_stream

    def add_strategy(self, strategy: BaseStrategy):
        self._strategies.append(strategy)

    def remove_strategy(self, strategy: BaseStrategy):
        self._strategies.remove(strategy)

    def notify_strategies(self):
        for strategy in self._strategies:
            interval = getattr(strategy, 'interval', '1d')
            target_asset = getattr(strategy, 'target_asset', 'KTB')
            frame = self._data_stream.get_data(interval=interval, target_asset=target_asset)
            strategy.execute(frame)