from typing import List, Dict, DefaultDict
from Strategy import *
from DataStream import *
import numpy as np
import pandas as pd

class SignalHub:
    def __init__(self, DataStream: DataProvider):
        self._strategies = List(BaseStrategy)        
        self._DataStream = DataStream

    def add_strategy(self, Strategy: BaseStrategy):
        Strategy.set_DataStream(self._DataStream)
        self._strategies.append(Strategy)

    def remove_strategy(self, Strategy: BaseStrategy):
        self._strategies.remove(Strategy)

    def init_strategies(self):
        for strategy in self._strategies:
            strategy.set_dataStream(self._DataStream)
            # strategy.set_parameters()

    def nofity_strategies(self):
        # newData = DataStream.get_data() 
        for strategy in self._strategies: strategy.execute()