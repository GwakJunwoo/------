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
        self.history = pd.DataFrame()  # 과거 데이터 누적용

    def rule(self, frame: pd.DataFrame):
        # frame은 "신규 데이터 1개 row"만 들어온다고 가정
        # 과거 데이터 누적
        self.history = pd.concat([self.history, frame], ignore_index=True)

        window = 5
        recent_frame = self.history.tail(window * 2)
        std_moving_average = recent_frame['close'].rolling(window=window).mean()
        threshold = recent_frame['close'].rolling(window=window).max().iloc[-1] * 0.8

        # 데이터가 20개 미만이면 신호 없음(None) 반환
        if len(recent_frame) < window or pd.isna(std_moving_average.iloc[-1]):
            return None

        if std_moving_average.iloc[-1] >= threshold:
            print(f"[{self._name}] Buy Signal Detected at {std_moving_average.iloc[-1]}")
            return 1
        elif std_moving_average.iloc[-1] <= -threshold:
            print(f"[{self._name}] Sell Signal Detected at {std_moving_average.iloc[-1]}")
            return -1
        else:
            return None
        
class SmaCrossStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self._name = "SmaCrossStrategy"
        self.set_parameters(interval='1d', target_asset='KTB')
        self.history = pd.DataFrame()

    def rule(self, frame: pd.DataFrame):
        # frame은 "신규 데이터 1개 row"만 들어온다고 가정
        self.history = pd.concat([self.history, frame], ignore_index=True)

        short_window = 5
        long_window = 20

        if len(self.history) < long_window:
            return None  # 데이터 부족

        short_ma = self.history['close'].rolling(window=short_window).mean()
        long_ma = self.history['close'].rolling(window=long_window).mean()

        # 직전 시점과 현재 시점의 MA 차이로 골든/데드크로스 판별
        if short_ma.iloc[-2] < long_ma.iloc[-2] and short_ma.iloc[-1] >= long_ma.iloc[-1]:
            print(f"[{self._name}] Buy Signal Detected at {self.history['close'].iloc[-1]}")
            return 1
        elif short_ma.iloc[-2] > long_ma.iloc[-2] and short_ma.iloc[-1] <= long_ma.iloc[-1]:
            print(f"[{self._name}] Sell Signal Detected at {self.history['close'].iloc[-1]}")
            return -1
        else:
            return None