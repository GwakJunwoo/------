from DataStream import *
import pandas as pd

"""
전략 클래스는 진입 신호(롱/숏/없음)만 생성합니다.
손절/익절 등 청산은 PositionManager에서 관리합니다.
"""

class BaseStrategy:
    def __init__(self):
        self._name = "BaseStrategy"
        self.history = pd.DataFrame()

    def set_parameters(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def rule(self, frame: pd.DataFrame):
        """
        각 전략별로 구현: 진입 신호만 반환 (1: 롱 진입, -1: 숏 진입, None: 신호 없음)
        """
        raise NotImplementedError

    def execute(self, frame: pd.DataFrame):
        return self.rule(frame)

class MomentumStrategy(BaseStrategy):
    """
    N일 모멘텀 전략: 오늘 종가 - N일 전 종가가 0보다 크면 롱, 작으면 숏
    """
    def __init__(self):
        super().__init__()
        self._name = "MomentumStrategy"
        self.set_parameters(interval='1d', target_asset='KTB', lookback=10)

    def rule(self, frame: pd.DataFrame):
        self.history = pd.concat([self.history, frame], ignore_index=True)
        lookback = getattr(self, 'lookback', 10)
        if len(self.history) < lookback + 1:
            return None  # 데이터 부족
        momentum = self.history['close'].iloc[-1] - self.history['close'].iloc[-lookback-1]
        if momentum > 0:
            print(f"[{self._name}] Buy Signal Detected (momentum={momentum:.3f})")
            return 1
        elif momentum < 0:
            print(f"[{self._name}] Sell Signal Detected (momentum={momentum:.3f})")
            return -1
        else:
            return None

class SmaCrossStrategy(BaseStrategy):
    """
    단기/장기 이동평균선 골든/데드크로스 전략
    """
    def __init__(self):
        super().__init__()
        self._name = "SmaCrossStrategy"
        self.set_parameters(interval='1d', target_asset='KTB', short_window=5, long_window=20)

    def rule(self, frame: pd.DataFrame):
        self.history = pd.concat([self.history, frame], ignore_index=True)
        short_window = getattr(self, 'short_window', 5)
        long_window = getattr(self, 'long_window', 20)
        if len(self.history) < long_window:
            return None  # 데이터 부족
        short_ma = self.history['close'].rolling(window=short_window).mean()
        long_ma = self.history['close'].rolling(window=long_window).mean()
        # 골든/데드크로스 판별
        if short_ma.iloc[-2] < long_ma.iloc[-2] and short_ma.iloc[-1] >= long_ma.iloc[-1]:
            print(f"[{self._name}] Buy Signal Detected at {self.history['close'].iloc[-1]}")
            return 1
        elif short_ma.iloc[-2] > long_ma.iloc[-2] and short_ma.iloc[-1] <= long_ma.iloc[-1]:
            print(f"[{self._name}] Sell Signal Detected at {self.history['close'].iloc[-1]}")
            return -1
        else:
            return None
        
    