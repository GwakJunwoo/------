from DataStream import *
import pandas as pd

"""
1. 전략 마다 사용할 파라미터가 사전 정의 되어야함
2. DataStream을 통해 새로운 데이터가 들어오면, 사전 정의된 파라미터 명세 대로 추출해야함

"""

# git test

class BaseStrategy:
    def __init__(self):
        self._DataStream = None
        pass

    def execute(self, newData):
        # 새로운 데이터에 대한 업데이
        INTERVAL = getattr(self, 'interval', '1d')
        TARGET_ASSET = getattr(self, 'target_asset', 'KTB')

        if self._DataStream is not None:
            # DataStream의 내부 DataFrame을 직접 참조
            frame = self._DataStream.get_data(interval=INTERVAL, target_asset=TARGET_ASSET)
        else:
            print("DataStream is not set.")
            return

        signal = self.rule(frame)

        if signal is not None:
            if signal == "1":
                # Buy Signal Buy Execution
                pass
            elif signal == "-1":
                # Sell Signal Sell Execution
                pass
            else:
                # No Signal
                pass

    def set_dataStream(self, DataStream: DataProvider):
        self._DataStream = DataStream

    def set_parameters(self, **kwargs):
        # 전략에 필요한 파라미터 설정
        # time period
        for key, value in kwargs.items():
            setattr(self, key, value)

class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self._name = "MomentumStrategy"

    def rule(self, frame):
        # parameter setting
        self.set_parameters(interval='1d')
        self.set_parameters(target_asset='KTB')

        window = 5

        recent_frame = frame.tail(window * 2)

        std_moving_average = recent_frame['close'].rolling(window=20).mean()
        threshold = 0.02

        # 예시: 마지막 값만 비교
        if std_moving_average.iloc[-1] >= threshold:
            return "1"
        elif std_moving_average.iloc[-1] <= -threshold:
            return "-1"
        else:
            return None
