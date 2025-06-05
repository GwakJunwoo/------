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
        if strategy_name not in self.positions:
            self.positions[strategy_name] = {
                "date": None, "position": 0, "entry_price": None, "average_price": None, "history": [], "pnl": 0.0
            }
    
        pos = self.positions[strategy_name]["position"]
        average_price = self.positions[strategy_name].get("average_price", None)
    
        # 진입 신호
        if signal > 0:  # 롱 진입
            if pos < 0:
                # 기존 숏 청산 (평단가 기준)
                if average_price is not None:
                    pnl = (average_price - price) * abs(pos)
                    self.positions[strategy_name]["pnl"] += pnl
                    self.positions[strategy_name]["history"].append(
                        (date, "SHORT_EXIT", price, average_price, pos, pnl)
                    )
                # 롱 진입
                self.positions[strategy_name]["position"] = signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price
                self.positions[strategy_name]["history"].append(
                    (date, "LONG_ENTRY", price, price, signal, 0)
                )
            elif pos > 0:
                # 롱 추가 진입 (평단가 갱신)
                new_pos = pos + signal
                new_avg = (average_price * pos + price * signal) / new_pos
                self.positions[strategy_name]["position"] = new_pos
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = new_avg
                self.positions[strategy_name]["history"].append(
                    (date, "LONG_ENTRY", price, new_avg, new_pos, 0)
                )
            elif pos == 0:
                # 롱 진입
                self.positions[strategy_name]["position"] = signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price
                self.positions[strategy_name]["history"].append(
                    (date, "LONG_ENTRY", price, price, signal, 0)
                )
    
        elif signal < 0:  # 숏 진입
            if pos > 0:
                # 기존 롱 청산 (평단가 기준)
                if average_price is not None:
                    pnl = (price - average_price) * abs(pos)
                    self.positions[strategy_name]["pnl"] += pnl
                    self.positions[strategy_name]["history"].append(
                        (date, "LONG_EXIT", price, average_price, pos, pnl)
                    )
                # 숏 진입
                self.positions[strategy_name]["position"] = signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price
                self.positions[strategy_name]["history"].append(
                    (date, "SHORT_ENTRY", price, price, signal, 0)
                )
            elif pos < 0:
                # 숏 추가 진입 (평단가 갱신)
                new_pos = pos + signal  # 둘 다 음수
                new_avg = (average_price * abs(pos) + price * abs(signal)) / abs(new_pos)
                self.positions[strategy_name]["position"] = new_pos
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = new_avg
                self.positions[strategy_name]["history"].append(
                    (date, "SHORT_ENTRY", price, new_avg, new_pos, 0)
                )
            elif pos == 0:
                # 숏 진입
                self.positions[strategy_name]["position"] = signal
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price
                self.positions[strategy_name]["history"].append(
                    (date, "SHORT_ENTRY", price, price, signal, 0)
                )
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

class PositionManagerCapital(PositionManager):
    """
    자본 기반 포지션 매니저: 자본의 일정 비율로 포지션 진입 및 자본/잔고 관리
    기존 PositionManager와 동일한 인터페이스 + 자본 제약
    """
    def __init__(self, capital: float = 10000, risk_per_trade: float = 0.1, stop_loss: float = 0.02, take_profit: float = 0.03):
        super().__init__(stop_loss, take_profit)
        self.initial_capital = capital
        self.cash = capital
        self.risk_per_trade = risk_per_trade
        self.open_positions: Dict[str, Any] = {}

    # 사용안함 
    def calculate_position_size(self, price: float) -> int:
        risk_amount = self.cash * self.risk_per_trade
        stop_loss = self.stop_loss if self.stop_loss != 0 else 1e-6
        price = price if price != 0 else 1e-6
        position_size = int(risk_amount / (price * stop_loss))
        return max(position_size, 1)

    def update_position(self, date: str, strategy_name: str, signal: int, price: float):
        if strategy_name not in self.positions:
            self.positions[strategy_name] = {
                "date": None, "position": 0, "entry_price": None, "average_price": None, "history": [], "pnl": 0.0, "cash": self.cash
            }
    
        pos = self.positions[strategy_name]["position"]
        average_price = self.positions[strategy_name].get("average_price", None)
    
        size = abs(signal)
        required_cash = price * size
    
#        if self.cash < 0:
#            # 잔고가 없으면 진입 불가
#            self.positions[strategy_name]["history"].append(
#                (date, "NO_FUNDS", price, average_price, 0, 0, self.cash)
#            )
#            return

        # 1. 기존 포지션 청산 (반대 신호일 때만)
        if signal > 0 and pos < 0:
            # 숏 청산
            if average_price is not None:
                pnl = (average_price - price) * abs(pos)
                self.cash += price * abs(pos)  # 원금 반환
                #self.cash = max(self.cash, 0)  # 잔고가 음수가 되지 않도록
                self.positions[strategy_name]["pnl"] += pnl
                self.positions[strategy_name]["history"].append(
                    (date, "SHORT_EXIT", price, average_price, pos, pnl, self.cash)
                )
            pos = 0  # 포지션 청산 후 0으로
    
        elif signal < 0 and pos > 0:
            # 롱 청산
            if average_price is not None:
                pnl = (price - average_price) * abs(pos)
                self.cash += price * abs(pos)  # 원금 반환
                #self.cash = max(self.cash, 0)  # 잔고가 음수가 되지 않도록
                self.positions[strategy_name]["pnl"] += pnl
                self.positions[strategy_name]["history"].append(
                    (date, "LONG_EXIT", price, average_price, pos, pnl, self.cash)
                )
            pos = 0  # 포지션 청산 후 0으로
    
        # 진입 실패 처리
        if self.cash < required_cash:
            entry_type = "LONG_ENTRY_FAIL" if signal > 0 else "SHORT_ENTRY_FAIL"
            self.positions[strategy_name]["history"].append(
                (date, entry_type, price, average_price, pos, 0)
            )
            return

        # 2. 진입/추가 진입 처리
        if signal > 0:
            if pos == 0:
                # 신규 롱 진입
                self.cash -= required_cash
                self.positions[strategy_name]["position"] = size
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price
                self.positions[strategy_name]["history"].append(
                    (date, "LONG_ENTRY", price, price, size, 0, self.cash)
                )
            elif pos > 0:
                # 롱 추가 진입 (평단가 갱신)
                new_pos = pos + size
                new_avg = (average_price * pos + price * size) / new_pos
                add_cash = price * size
                if self.cash < add_cash:
                    self.positions[strategy_name]["history"].append(
                        (date, "LONG_ENTRY_FAIL", price, average_price, pos, 0, self.cash)
                    )
                    return
                self.cash -= add_cash
                self.positions[strategy_name]["position"] = new_pos
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = new_avg
                self.positions[strategy_name]["history"].append(
                    (date, "LONG_ENTRY", price, new_avg, new_pos, 0, self.cash)
                )
    
        elif signal < 0:
            if pos == 0:
                # 신규 숏 진입
                self.cash -= required_cash
                self.positions[strategy_name]["position"] = -size
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = price
                self.positions[strategy_name]["history"].append(
                    (date, "SHORT_ENTRY", price, price, -size, 0, self.cash)
                )
            elif pos < 0:
                # 숏 추가 진입 (평단가 갱신)
                new_pos = pos - size
                new_avg = (average_price * abs(pos) + price * size) / abs(new_pos)
                add_cash = price * size
                if self.cash < add_cash:
                    self.positions[strategy_name]["history"].append(
                        (date, "SHORT_ENTRY_FAIL", price, average_price, pos, 0, self.cash)
                    )
                    return
                self.cash -= add_cash
                self.positions[strategy_name]["position"] = new_pos
                self.positions[strategy_name]["entry_price"] = price
                self.positions[strategy_name]["average_price"] = new_avg
                self.positions[strategy_name]["history"].append(
                    (date, "SHORT_ENTRY", price, new_avg, new_pos, 0, self.cash)
                )

    def get_cash(self):
        return self.cash

    def get_equity(self, current_price: float, strategy_name: str):
        """
        현재 잔고 + 미실현 손익(보유 포지션 평가손익)
        """
        info = self.positions.get(strategy_name, {})
        pos = info.get("position", 0)

        if pos == 0:
            return self.cash
        # 예예
        unrealized = (current_price) * pos if pos > 0 else (current_price) * abs(pos)
        print(self.cash, unrealized)
        return self.cash + unrealized

    def get_history(self, strategy_name: str):
        return self.positions.get(strategy_name, {}).get("history", [])

    def get_realized_pnl(self, strategy_name: str):
        return self.positions.get(strategy_name, {}).get("pnl", 0.0)

    def get_initial_cash(self):
        return self.initial_capital

    def summary(self):
        for name, info in self.positions.items():
            print("=================")
            print(f"Strategy: {name}")
            print(f"[{name}] Position: {info['position']}, Entry: {info['entry_price']}, History: {info['history']}")
            print(f"[{name}] Realized PnL: {info.get('pnl', 0.0)}")
            print(f"[{name}] Cash: {self.cash}")