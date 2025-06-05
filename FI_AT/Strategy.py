from DataStream import *
import pandas as pd
import numpy as np

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
        

class Hybrid60mStrategy(BaseStrategy):
    """
    60분봉 하이브리드 전략
    ─ 모멘텀, SMA 크로스, RSI 세 가지 지표를 투표 방식으로 결합
    ─ vote_threshold 이상 득표 시 매수/매도 신호 반환
    """
    def __init__(self):
        super().__init__()
        self._name = "Hybrid60mStrategy"
        # 기본 파라미터
        self.set_parameters(
            interval='60min',          # 60분 봉
            target_asset='KTB',        # 자산 티커
            lookback=12,               # 모멘텀용 (12×60 분 ≈ 하루)
            short_window=5,            # 단기 SMA
            long_window=20,            # 장기 SMA
            rsi_window=14,
            overbought=70,
            oversold=30,
            vote_threshold=2           # 3개 중 2표 이상 일치 시 진입
        )

    def _calc_rsi(self, series: pd.Series, window: int) -> float:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=window).mean().iloc[-1]
        avg_loss = loss.rolling(window=window).mean().iloc[-1]
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def rule(self, frame: pd.DataFrame):
        # 히스토리 누적
        self.history = pd.concat([self.history, frame], ignore_index=True)

        lb   = getattr(self, 'lookback', 12)
        sw   = getattr(self, 'short_window', 5)
        lw   = getattr(self, 'long_window', 20)
        rw   = getattr(self, 'rsi_window', 14)
        ob   = getattr(self, 'overbought', 70)
        os   = getattr(self, 'oversold', 30)
        thr  = getattr(self, 'vote_threshold', 2)

        # 데이터 충분성 체크
        min_len = max(lb+1, lw+1, rw+1)
        if len(self.history) < min_len:
            return None

        price_series = self.history['close']

        # === 1) 모멘텀 신호 ===
        momentum_val = price_series.iloc[-1] - price_series.iloc[-lb-1]
        momentum_sig = 1 if momentum_val > 0 else -1 if momentum_val < 0 else 0

        # === 2) SMA 크로스 신호 ===
        short_ma = price_series.rolling(sw).mean()
        long_ma  = price_series.rolling(lw).mean()
        sma_sig  = 1 if short_ma.iloc[-1] > long_ma.iloc[-1] else -1

        # === 3) RSI 신호 ===
        rsi = self._calc_rsi(price_series, rw)
        if rsi < os:
            rsi_sig = 1
        elif rsi > ob:
            rsi_sig = -1
        else:
            rsi_sig = 0

        # === 투표 ===
        vote_sum = momentum_sig + sma_sig + rsi_sig
        if vote_sum >= thr:
            return 1     # 롱 진입
        elif vote_sum <= -thr:
            return -1    # 숏 진입
        else:
            return None  # 신호 없음


class DonchianCloseBreakoutStrategy(BaseStrategy):
    """
    Close 기준 Donchian 돌파 추세추종
    - 최근 dc_window 봉 중 최고 / 최저 종가 돌파 시 진입 (+1 / –1)
    - 포지션 청산(반대 돌파)은 내부 _pos 플래그만 리셋, 신호는 반환하지 않음
    """
    def __init__(self):
        super().__init__()
        self._name = "DonchianCloseBreakoutStrategy"
        self.set_parameters(interval='60min', target_asset='KTB', dc_window=20)
        self._pos = 0  # 1(롱) / -1(숏) / 0(없음)

    def rule(self, frame: pd.DataFrame):
        # 데이터 누적
        self.history = pd.concat([self.history, frame], ignore_index=True)
        N = getattr(self, 'dc_window', 20)

        if len(self.history) < N + 1:
            return None  # 데이터 부족

        # 직전 N봉(Close) 기준 상·하단
        max_c = self.history['close'].rolling(N).max().iloc[-2]
        min_c = self.history['close'].rolling(N).min().iloc[-2]
        price = self.history['close'].iloc[-1]

        # 반대 돌파 → 내부 포지션 종료 (신호 X)
        if self._pos == 1 and price < min_c:
            self._pos = 0
        elif self._pos == -1 and price > max_c:
            self._pos = 0

        # 신규 진입 신호
        if self._pos == 0:
            if price > max_c:
                self._pos = 1
                return 1      # 롱 진입
            if price < min_c:
                self._pos = -1
                return -1     # 숏 진입
        return None


class ZScoreMeanReversionStrategy(BaseStrategy):
    """
    Z-Score 평균회귀
    - Z = (Close - MA) / σ
    - |Z| ≥ threshold 돌파 시 역방향 진입 (+1 / –1)
    - |Z| < exit_band(0.5) → 내부 포지션 종료, 신호 반환 없음
    """
    def __init__(self):
        super().__init__()
        self._name = "ZScoreMeanReversionStrategy"
        self.set_parameters(interval='60min', target_asset='KTB',
                            window=30, threshold=2.0, exit_band=0.5)
        self._pos = 0

    def rule(self, frame: pd.DataFrame):
        self.history = pd.concat([self.history, frame], ignore_index=True)
        W  = getattr(self, 'window', 30)
        K  = getattr(self, 'threshold', 2.0)
        EB = getattr(self, 'exit_band', 0.5)

        if len(self.history) < W + 1:
            return None

        ma  = self.history['close'].rolling(W).mean().iloc[-1]
        std = self.history['close'].rolling(W).std().iloc[-1]
        if std == 0:
            return None
        z = (self.history['close'].iloc[-1] - ma) / std

        # 평균 복귀 → 내부 포지션 종료
        if self._pos != 0 and abs(z) < EB:
            self._pos = 0

        # 신규 진입 신호
        if self._pos == 0:
            if z >  K:
                self._pos = -1      # 과매수 → 숏
                return -1
            if z < -K:
                self._pos = 1       # 과매도 → 롱
                return 1
        return None

class AdaptiveZScoreMeanRev(BaseStrategy):
    """
    EWMA·MADM 기반 σ + 적응형 threshold + ATR stop/tp + max hold
    """
    def __init__(self):
        super().__init__()
        self._name = "AdaptiveZScoreMeanRev"
        self.set_parameters(interval='60min',
                            λ=0.04, pct_high=0.9, pct_low=0.1,
                            exit_band=0.3, stop_atr=2.0,
                            tp_atr=4.0, max_bar=48)
        self._pos = 0
        self._entry_px, self._entry_bar = None, None

    def _atr(self, series, w=14):
        hi_lo = series.diff().abs()
        return hi_lo.rolling(w).mean().iloc[-1]

    def rule(self, frame: pd.DataFrame):
        self.history = pd.concat([self.history, frame], ignore_index=True)
        if len(self.history) < 250:  # 최소 학습 구간
            return None

        price = self.history['close']
        λ = self.λ

        ewma = price.ewm(alpha=λ).mean().iloc[-1]
        ewstd = np.sqrt(
            (price.pow(2).ewm(alpha=λ).mean().iloc[-1]) - ewma**2
        )
        mad = (price - ewma).abs().ewm(alpha=λ).mean().iloc[-1] * 1.253
        σ = 0.5*ewstd + 0.5*mad

        # z-score 전체 시계열 계산
        z_series = (price - price.ewm(alpha=λ).mean()) / σ

        # 최근 250개 z-score의 quantile로 적응형 threshold 계산
        hi_q = z_series.tail(250).quantile(self.pct_high)
        lo_q = z_series.tail(250).quantile(self.pct_low)

        z = (price.iloc[-1] - ewma) / σ

        # ===== exit =====
        if self._pos and (abs(z) < self.exit_band or
                          self.history.index[-1] - self._entry_bar >= self.max_bar):
            self._pos = 0
            self._entry_px = self._entry_bar = None

        # ===== entry =====
        if self._pos == 0:
            if z > hi_q:
                self._pos = -1
                self._entry_px = price.iloc[-1]
                self._entry_bar = self.history.index[-1]
                return -1
            if z < lo_q:
                self._pos = 1
                self._entry_px = price.iloc[-1]
                self._entry_bar = self.history.index[-1]
                return 1
        return None
    
class ZScoreLayeredMeanRev(BaseStrategy):
    """
    다단 진입·트레일 스톱을 갖춘 Z-Score 평균회귀
      • k1 돌파 → ½ 사이즈 진입, k2 돌파 → 나머지 ½
      • |Z| < exit_band 또는 |Z| > k2+trail_step ⇒ 내부 청산 (신호 없음)
    반환값:  1 / -1 / None   (청산= None)
    """
    def __init__(self):
        super().__init__()
        self._name = "ZScoreLayeredMeanRev"
        self.set_parameters(interval='60min', target_asset='KTB',
                            window=20, k1=1.5, k2=2.2,
                            exit_band=0.25, trail_step=0.4)
        self._pos  = 0      # 1, -1, 0
        self._size = 0.0    # 0, 0.5, 1.0

    def rule(self, frame: pd.DataFrame):
        # 데이터 누적
        self.history = pd.concat([self.history, frame], ignore_index=True)

        W  = getattr(self, 'window', 20)
        k1 = getattr(self, 'k1', 1.5)
        k2 = getattr(self, 'k2', 2.2)
        EB = getattr(self, 'exit_band', 0.25)
        ts = getattr(self, 'trail_step', 0.4)

        if len(self.history) < W + 1:
            return None

        price = self.history['close']
        ma  = price.rolling(W).mean().iloc[-1]
        std = price.rolling(W).std().iloc[-1]
        if std == 0:
            return None
        z = (price.iloc[-1] - ma) / std

        # ── 청산: 평균 복귀 or 손절선 초과  ──────────────────
        if self._pos != 0 and (abs(z) < EB or abs(z) > k2 + ts):
            self._pos  = 0
            self._size = 0.0
            return None        # 청산 신호는 내보내지 않음

        # ── 신규·추가 진입 ───────────────────────────────
        if self._pos == 0 and abs(z) > k1:
            # ½ 사이즈 진입
            self._pos  = 1 if z < 0 else -1
            self._size = 0.5
            return self._pos        # 첫 진입

        if self._size == 0.5 and (
            (self._pos == 1 and z < -k2) or (self._pos == -1 and z > k2)
        ):
            # 나머지 ½ 진입
            self._size = 1.0
            return self._pos        # 추가 진입

        return None

class VotingEnsembleStrategy(BaseStrategy):
    """
    여러 전략의 신호를 투표로 결합하는 앙상블 전략
    - 각 전략의 신호(1, -1, None)를 받아서
    - threshold 이상 득표 시 진입 신호 반환
    """
    def __init__(self, vote_threshold=2):
        super().__init__()
        self._name = "VotingEnsembleStrategy"
        self.strategies = [MomentumStrategy(), SmaCrossStrategy() , RsiStrategy()]  # [전략 인스턴스 리스트]
        self.vote_threshold = vote_threshold

    def rule(self, frame: pd.DataFrame):
        # 각 전략에 동일한 frame을 전달
        votes = []
        for strat in self.strategies:
            sig = strat.rule(frame)
            if sig is not None:
                votes.append(sig)
        if not votes:
            return None
        # 득표 집계
        long_votes = votes.count(1)
        short_votes = votes.count(-1)
        if long_votes >= self.vote_threshold:
            return 1
        elif short_votes >= self.vote_threshold:
            return -1
        else:
            return None