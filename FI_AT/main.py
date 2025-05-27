from DataStream import MockDataStream
from Strategy import MomentumStrategy, SmaCrossStrategy
from Position import PositionManager
from SignalHub import SignalHub
from Execution import BacktestExecution

# 1. 데이터 스트림 준비 (Mock)
data_stream = MockDataStream('1d', 'KTB')

# 2. 포지션 매니저 준비
position_manager = PositionManager()

# 3. SignalHub 생성
signal_hub = SignalHub(data_stream, position_manager)

# 4. 전략 생성 및 등록
momentum_strategy = MomentumStrategy()
signal_hub.add_strategy(SmaCrossStrategy())

# 5. 백테스트 실행
# (MockDataStream은 get_data에서 항상 최신 1개 row만 반환하므로, 1회만 실행)
backtest = BacktestExecution(signal_hub, position_manager)
backtest.run()

# 6. 결과 출력
position_manager.summary()