from DataStream import *
import pandas as pd

"""
1. 전략 마다 사용할 파라미터가 사전 정의 되어야함
2. DataStream을 통해 새로운 데이터가 들어오면, 사전 정의된 파라미터 명세 대로 추출해야함

"""

import pandas as pd

class BaseStrategy:
    def __init__(self):
        pass

    def execute(self, frame: pd.DataFrame):
        signal = self.rule(frame)
        if signal is not None:
            if signal > 0:
                # Buy Signal Buy Execution
                pass
            elif signal < 0:
                # Sell Signal Sell Execution
                pass
            else:
                # No Signal
                pass

    def set_parameters(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self._name = "MomentumStrategy"
        self.set_parameters(interval='1d', target_asset='KTB')

    def rule(self, frame: pd.DataFrame):
        window = 5
        recent_frame = frame.tail(window * 2)
        std_moving_average = recent_frame['close'].rolling(window=20).mean()
        threshold = 0.02

        if std_moving_average.iloc[-1] >= threshold:
            return 1
        elif std_moving_average.iloc[-1] <= -threshold:
            return -1
        else:
            return None