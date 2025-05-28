import pandas as pd
from typing import Dict, Any, Optional

class PositionManager:
    """
    각 전략별 포지션, 진입가, 손익, 진입/청산 이력, 손절/익절 관리
    """
    def __init__(self, stop_loss: float = 0.02, take_profit: float = 0.03):
        # {strategy_name: {...}}
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def update_position(self, date: str, strategy_name: str, signal: int, price: float):
        """
        진입 신호(1:롱, -1:숏), 가격을 받아 포지션 상태 갱신
        """
        if strategy_name not in self.positions:
            self.positions[strategy_name] = {
                "date": None, "position": 0, "entry_price": None, "average_price": None,"history": [], "pnl": 0.0
            }

        pos = self.positions[strategy_name]["position"]
        entry = self.positions[strategy_name]["entry_price"]
        average_price = self.positions[strategy_name].get("average_price", None)

        # 진입 신호
        if signal > 0:  # 롱 진입
            if pos < 0:
                # 기존 숏 청산 로직: 지금은 그냥 숏 포지션 상태에서 매수 시그널이 나오면 청산산
                if pos < 0 and entry is not None:
                    pnl = entry - price
                    self.positions[strategy_name]["pnl"] += pnl
                    self.positions[strategy_name]["positions"] = 0

                    # 청산 가격도 반영
                    self.positions[strategy_name]["entry_price"] = price
                    self.positions[strategy_name]["history"].append((date, "SHORT_EXIT", price, average_price, pos, pnl))

                # 롱 포지션 진입
                self.positions[strategy_name]["position"] = signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price if average_price is None else ((average_price * pos) + price) / (pos + signal)
                self.positions[strategy_name]["history"].append((date, "LONG_ENTRY", price, average_price, pos, 0))
            elif pos > 0:  # 이미 롱 포지션인 경우
                # 롱 포지션 추가 진입
                self.positions[strategy_name]["position"] += signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = ((entry * pos) + (price * signal)) / (pos + signal)
                self.positions[strategy_name]["history"].append((date, "LONG_ENTRY", price, average_price, pos, 0))

            elif pos == 0:  # 포지션이 없는 경우
                # 롱 포지션 진입
                self.positions[strategy_name]["position"] = signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price
                self.positions[strategy_name]["history"].append((date, "LONG_ENTRY", price, average_price, pos, 0))

        elif signal < 0:  # 숏 진입
            if pos > 0:
                # 기존 롱 청산 로직: 롱 포지션 상태에서 숏 시그널이 나오면 청산
                if pos > 0 and entry is not None:
                    pnl = price - entry
                    self.positions[strategy_name]["pnl"] += pnl
                    self.positions[strategy_name]["positions"] = 0

                    # 청산 가격도 반영
                    self.positions[strategy_name]["entry_price"] = price
                    self.positions[strategy_name]["history"].append((date, "LONG_EXIT", price, average_price, pos, pnl))

                # 숏 포지션 진입
                self.positions[strategy_name]["position"] = signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price if average_price is None else ((average_price * pos) + price) / (pos + signal)
                self.positions[strategy_name]["history"].append((date, "SHORT_ENTRY", price, average_price, pos, 0))
            elif pos < 0:  # 이미 숏 포지션인 경우
                # 숏 포지션 추가 진입
                self.positions[strategy_name]["position"] += signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = ((entry * pos) + (price * signal)) / (pos + signal)
                self.positions[strategy_name]["history"].append((date, "SHORT_ENTRY", price, average_price, pos, 0))

            elif pos == 0:  # 포지션이 없는 경우
                # 숏 포지션 진입
                self.positions[strategy_name]["position"] = signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price
                self.positions[strategy_name]["history"].append((date, "SHORT_ENTRY", price, average_price, pos, 0))
        # signal == 0 or None: do nothing

    #TODO: 아직 미구현, 적용 안함
    def check_exit(self, strategy_name: str, price: float) -> Optional[str]:
        """
        포지션이 있을 때 손절/익절 조건을 체크하고, 조건 충족 시 자동 청산
        return: 'stop_loss', 'take_profit', None
        """
        info = self.positions.get(strategy_name)
        if not info or info["position"] == 0 or info["entry_price"] is None:
            return None

        pos = info["position"]
        entry = info["entry_price"]
        pnl = (price - entry) if pos == 1 else (entry - price)
        pnl_pct = pnl / entry if entry != 0 else 0

        # 손절
        if pnl_pct <= -self.stop_loss:
            info["pnl"] += pnl
            if pos == 1:
                info["history"].append(("LONG_STOPLOSS", price, pnl))
            else:
                info["history"].append(("SHORT_STOPLOSS", price, pnl))
            info["position"] = 0
            info["entry_price"] = None
            return "stop_loss"
        # 익절
        if pnl_pct >= self.take_profit:
            info["pnl"] += pnl
            if pos == 1:
                info["history"].append(("LONG_TAKEPROFIT", price, pnl))
            else:
                info["history"].append(("SHORT_TAKEPROFIT", price, pnl))
            info["position"] = 0
            info["entry_price"] = None
            return "take_profit"
        return None

    def get_position(self, strategy_name: str):
        return self.positions.get(strategy_name, {"position": 0, "entry_price": None})

    def get_all_positions(self):
        return self.positions

    def get_history(self, strategy_name: str):
        return self.positions.get(strategy_name, {}).get("history", [])

    def get_realized_pnl(self, strategy_name: str):
        return self.positions.get(strategy_name, {}).get("pnl", 0.0)

    def summary(self):
        for name, info in self.positions.items():
            print("=================")
            print(f"Strategy: {name}")
            print(f"[{name}] Position: {info['position']}, Entry: {info['entry_price']}, History: {info['history']}")
            print(f"[{name}] Realized PnL: {info.get('pnl', 0.0)}")