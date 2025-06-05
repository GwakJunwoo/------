import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class Evaluation:
    def __init__(self, position_manager):
        self.position_manager = position_manager

    def get_trade_log(self, strategy_name):
        # [(BUY/SELL, price)] 리스트를 DataFrame으로 변환
        history = self.position_manager.get_history(strategy_name)
        if not history:
            return pd.DataFrame()
        df = pd.DataFrame(history, columns=['date', 'side', 'price', 'average_price', 'pos', 'pnl', 'cash'])
        df['date'] = pd.to_datetime(df['date'])
        return df

    def get_daily_pnl(self, strategy_name):
        # 포지션 체결 가격과 방향을 이용해 일별 손익 계산 (단순 예시)
        history = self.position_manager.get_history(strategy_name)
        if not history:
            return pd.Series(dtype=float)
        dates = []
        prices = []
        average_prices = []
        positions = []
        sides = []
        for date, side, price, average_price, pos, pnl in history:
            dates.append(pd.to_datetime(date))
            prices.append(price)
            average_prices.append(average_price)
            positions.append(pos)
            sides.append(1 if side == "BUY" else -1)
        # 단순히 체결마다 손익 계산
        pnl = []
        for i in range(1, len(prices)):
            pnl.append((prices[i] - prices[i-1]) * sides[i-1])
        daily_pnl = pd.Series(pnl)
        return daily_pnl

    def summary(self, strategy_name, print_result=True):
        trade_log = self.get_trade_log(strategy_name)
        daily_pnl = trade_log['pnl'] if not trade_log.empty else pd.Series(dtype=float)
        if daily_pnl.empty:
            if print_result:
                print("No trades.")
            return {
                "Total Trades": 0,
                "Total PnL": 0.0,
                "Sharpe Ratio": 0.0,
                "Win Rate": 0.0,
                "Annualized Volatility": 0.0
            }
        
        cash = self.position_manager.get_cash()
        pct_change = (cash - self.position_manager.get_initial_cash()) / self.position_manager.get_initial_cash() * np.sqrt(365/12)
        cum_pnl = daily_pnl.cumsum()
        sharpe = pct_change / (daily_pnl.std() + 1e-8) * np.sqrt(365/12)
        win_rate = (daily_pnl > 0).sum() / len(daily_pnl)
        volatility = daily_pnl.std() * np.sqrt(365/12)
    
        result = {
            "Total Trades": len(daily_pnl),
            "Total PnL": float(cum_pnl.iloc[-1]),
            "Sharpe Ratio": float(sharpe),
            "Win Rate": float(win_rate) * 100,
            "Annualized Volatility": float(volatility)
        }
        if print_result:
            print("==== Evaluation for", strategy_name, "====")
            for k, v in result.items():
                print(f"{k}: {v}")
        return result