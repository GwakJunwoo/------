from typing import List, Dict, DefaultDict
from Strategy import *
from Position import *
from DataStream import *
import numpy as np
import pandas as pd

class SignalHub:
    def __init__(self, data_stream: DataProvider, position_manager: PositionManager):
        self._strategies: List[BaseStrategy] = []
        self._data_stream = data_stream
        self._position_manager = position_manager

    def add_strategy(self, strategy: BaseStrategy):
        self._strategies.append(strategy)

    def remove_strategy(self, strategy: BaseStrategy):
        self._strategies.remove(strategy)

    def notify_strategies(self):
        for strategy in self._strategies:
            interval = getattr(strategy, 'interval', '1d')
            target_asset = getattr(strategy, 'target_asset', 'KTB')
            frame = self._data_stream.get_data(interval=interval, target_asset=target_asset)
            if frame.empty:
                continue
            signal = strategy.rule(frame)
            if signal is not None:
                price = frame['close'].iloc[-1]
                self._position_manager.update_position(
                    getattr(strategy, '_name', strategy.__class__.__name__),
                    signal,
                    price
                )