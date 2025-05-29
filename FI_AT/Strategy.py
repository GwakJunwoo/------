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
            #print(f"[{self._name}] Buy Signal Detected (momentum={momentum:.3f})")
            return 1
        elif momentum < 0:
            #print(f"[{self._name}] Sell Signal Detected (momentum={momentum:.3f})")
            return -1
        else:
            return None
        
class RateOfChangeStrategy(BaseStrategy):
    """
    ROC(변화율, Rate of Change) 기반 모멘텀 전략:
    - ROC가 양수(임계값 이상)이면 매수, 음수(임계값 이하)이면 매도
    """
    def __init__(self):
        super().__init__()
        self._name = "RateOfChangeStrategy"
        self.set_parameters(interval='1d', target_asset='KTB', roc_window=10, threshold=0)

    def rule(self, frame: pd.DataFrame):
        self.history = pd.concat([self.history, frame], ignore_index=True)
        roc_window = getattr(self, 'roc_window', 10)
        threshold = getattr(self, 'threshold', 0)
        if len(self.history) < roc_window + 1:
            return None  # 데이터 부족
        prev_price = self.history['close'].iloc[-roc_window-1]
        curr_price = self.history['close'].iloc[-1]
        if prev_price == 0:
            return None
        roc = (curr_price - prev_price) / prev_price * 100  # %
        if roc > threshold:
            return 1  # 매수
        elif roc < -threshold:
            return -1  # 매도
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
        short_window = getattr(self, 'short_window', 3)
        long_window = getattr(self, 'long_window', 12)
        if len(self.history) < long_window:
            return None  # 데이터 부족
        short_ma = self.history['close'].rolling(window=short_window).mean()
        long_ma = self.history['close'].rolling(window=long_window).mean()
        # 골든/데드크로스 판별
        if short_ma.iloc[-2] < long_ma.iloc[-2] and short_ma.iloc[-1] >= long_ma.iloc[-1]:
            #print(f"[{self._name}] Buy Signal Detected at {self.history['close'].iloc[-1]}")
            return 1
        elif short_ma.iloc[-2] > long_ma.iloc[-2] and short_ma.iloc[-1] <= long_ma.iloc[-1]:
            #print(f"[{self._name}] Sell Signal Detected at {self.history['close'].iloc[-1]}")
            return -1
        else:
            return None

class MeanReversionStrategy(BaseStrategy):
    """
    단순 평균회귀 전략: 종가가 N일 이동평균보다 K% 이상 위/아래에 있으면 매도/매수
    """
    def __init__(self):
        super().__init__()
        self._name = "MeanReversionStrategy"
        self.set_parameters(interval='1d', target_asset='KTB', window=20, threshold=0.02)  # 2% 이탈

    def rule(self, frame: pd.DataFrame):
        self.history = pd.concat([self.history, frame], ignore_index=True)
        window = getattr(self, 'window', 20)
        threshold = getattr(self, 'threshold', 0.02)
        if len(self.history) < window:
            return None  # 데이터 부족
        ma = self.history['close'].rolling(window=window).mean().iloc[-1]
        price = self.history['close'].iloc[-1]
        if price > ma * (1 + threshold):
            # 가격이 평균보다 threshold% 이상 높으면 매도(숏)
            return -1
        elif price < ma * (1 - threshold):
            # 가격이 평균보다 threshold% 이상 낮으면 매수(롱)
            return 1
        else:
            return None
    
class RsiStrategy(BaseStrategy):
    """
    RSI(상대강도지수) 기반 전략: RSI가 70 이상이면 매도, 30 이하이면 매수
    """
    def __init__(self):
        super().__init__()
        self._name = "RsiStrategy"
        self.set_parameters(interval='1d', target_asset='KTB', window=14, overbought=70, oversold=30)

    def rule(self, frame: pd.DataFrame):
        self.history = pd.concat([self.history, frame], ignore_index=True)
        window = getattr(self, 'window', 14)
        overbought = getattr(self, 'overbought', 70)
        oversold = getattr(self, 'oversold', 30)
        if len(self.history) < window + 1:
            return None  # 데이터 부족

        delta = self.history['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=window).mean().iloc[-1]
        avg_loss = loss.rolling(window=window).mean().iloc[-1]
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        if rsi > overbought:
            # 과매수: 매도 신호
            return -1
        elif rsi < oversold:
            # 과매도: 매수 신호
            return 1
        else:
            return None
        
class BollingerBandStrategy(BaseStrategy):
    """
    볼린저 밴드 전략: 상단 돌파시 매도, 하단 돌파시 매수
    """
    def __init__(self):
        super().__init__()
        self._name = "BollingerBandStrategy"
        self.set_parameters(interval='1d', target_asset='KTB', window=20, num_std=2)

    def rule(self, frame: pd.DataFrame):
        self.history = pd.concat([self.history, frame], ignore_index=True)
        window = getattr(self, 'window', 20)
        num_std = getattr(self, 'num_std', 2)
        if len(self.history) < window:
            return None
        ma = self.history['close'].rolling(window=window).mean().iloc[-1]
        std = self.history['close'].rolling(window=window).std().iloc[-1]
        upper = ma + num_std * std
        lower = ma - num_std * std
        price = self.history['close'].iloc[-1]
        if price > upper:
            return -1  # 매도
        elif price < lower:
            return 1   # 매수
        else:
            return None
        

class MomentumMeanReversionSwitchStrategy(BaseStrategy):
    """
    모멘텀/평균회귀 결합 전략:
    - 최근 변동성(표준편차)이 임계값 이상이면 모멘텀 전략 사용
    - 변동성이 임계값 미만이면 평균회귀 전략 사용
    """
    def __init__(self):
        super().__init__()
        self._name = "MomentumMeanReversionSwitchStrategy"
        self.set_parameters(
            interval='1d', target_asset='KTB',
            lookback=10,  # 모멘텀용
            meanrev_window=20, meanrev_threshold=0.02,  # 평균회귀용
            vol_window=20, vol_threshold=0.01  # 변동성 판단용
        )
        self.momentum = MomentumStrategy()
        self.meanrev = MeanReversionStrategy()

    def rule(self, frame: pd.DataFrame):
        # 히스토리 누적
        self.history = pd.concat([self.history, frame], ignore_index=True)
        vol_window = getattr(self, 'vol_window', 20)
        vol_threshold = getattr(self, 'vol_threshold', 0.01)

        if len(self.history) < vol_window:
            return None  # 데이터 부족

        # 최근 vol_window 구간의 표준편차(변동성)
        recent_std = self.history['close'].rolling(window=vol_window).std().iloc[-1]
        # 전략 파라미터 동기화
        self.momentum.set_parameters(lookback=getattr(self, 'lookback', 10))
        self.meanrev.set_parameters(window=getattr(self, 'meanrev_window', 20), threshold=getattr(self, 'meanrev_threshold', 0.02))

        # 변동성이 높으면 모멘텀, 낮으면 평균회귀
        if recent_std >= vol_threshold:
            return self.momentum.rule(frame)
        else:
            return self.meanrev.rule(frame)