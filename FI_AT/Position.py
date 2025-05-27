import pandas as pd
from typing import Dict, Any

class PositionManager:
    def __init__(self):
        # {strategy_name: {"position": int, "entry_price": float, ...}}
        self.positions: Dict[str, Dict[str, Any]] = {}

    def update_position(self, strategy_name: str, signal: int, price: float):
        """
        signal: 1=Buy, -1=Sell, 0=Flat/No action
        price: 체결 가격
        """
        if strategy_name not in self.positions:
            self.positions[strategy_name] = {"position": 0, "entry_price": None, "history": [], "pnl": 0.0}

        pos = self.positions[strategy_name]["position"]

        if signal == 1:  # Buy
            if pos <= 0:
                # 만약 기존에 숏 포지션이 있었다면, 청산 손익 계산
                if pos == -1 and self.positions[strategy_name]["entry_price"] is not None:
                    pnl = self.positions[strategy_name]["entry_price"] - price
                    self.positions[strategy_name]["pnl"] += pnl
                self.positions[strategy_name]["position"] = 1
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["history"].append(("BUY", price))
        elif signal == -1:  # Sell
            if pos >= 0:
                # 만약 기존에 롱 포지션이 있었다면, 청산 손익 계산
                if pos == 1 and self.positions[strategy_name]["entry_price"] is not None:
                    pnl = price - self.positions[strategy_name]["entry_price"]
                    self.positions[strategy_name]["pnl"] += pnl
                self.positions[strategy_name]["position"] = -1
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["history"].append(("SELL", price))
        # signal == 0 or None: do nothing

    def get_position(self, strategy_name: str):
        return self.positions.get(strategy_name, {"position": 0, "entry_price": None})

    def get_all_positions(self):
        return self.positions

    def get_history(self, strategy_name: str):
        return self.positions.get(strategy_name, {}).get("history", [])

    def summary(self):
        # 전체 포지션 요약 출력
        for name, info in self.positions.items():
            print("=================")
            print(f"Strategy: {name}")
            print(f"[{name}] Position: {info['position']}, Entry: {info['entry_price']}, History: {info['history']}")
            print(f"[{name}] Realized PnL: {info.get('pnl', 0.0)}")