import pandas as pd

class DataProvider:
    def __init__(self):
        self.data = None

    def get_data(self, interval=None, target_asset=None):
        raise NotImplementedError

class HistoricalDataStream(DataProvider):
    def __init__(self):
        self.data = pd.DataFrame()

    def get_data(self, interval, target_asset):
    # 조건에 맞는 DataFrame slice를 반환
        return self.data[(self.data['interval'] == interval) & 
                         (self.data['asset'] == target_asset)]
    
class MockDataStream(DataProvider):
    def __init__(self, interval, target_asset):
        super().__init__()
        path = f"C:/Users/infomax/Desktop/FI AT/------/FI_AT/data/{target_asset}_{interval}.csv"
        try:
            self.data = pd.read_csv(path)
        except FileNotFoundError:
            print(f"Data file {path} not found.")
            self.data = pd.DataFrame()
        self._current_idx = 0
        self.interval = interval
        self.target_asset = target_asset

    def get_data(self, interval=None, target_asset=None):
        filtered = self.data
        if self._current_idx < len(filtered):
            # "신규 데이터 1개 row만 반환"
            result = filtered.iloc[[self._current_idx]]
            self._current_idx += 1
            return result
        else:
            return pd.DataFrame()  # 끝나면 빈 데이터프레임

    def reset(self):
        self._current_idx = 0