import pandas as pd

class DataProvider:
    def get_data(self, interval=None, target_asset=None):
        raise NotImplementedError

class HistoricalDataStream(DataProvider):
    def __init__(self):
        self.data = pd.DataFrame()

    def get_data(self, interval, target_asset):
    # 조건에 맞는 DataFrame slice를 반환
        return self.data[(self.data['interval'] == interval) & 
                         (self.data['asset'] == target_asset)]
    
class MockDataProvider(DataProvider):
    def get_data(self, interval, target_asset):
        # 테스트용 DataFrame 반환
        return pd.DataFrame({})