import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.graph_objs as go
import pandas as pd

from DataStream import MockDataStream
from Strategy import MomentumStrategy, SmaCrossStrategy
from Position import PositionManager
from SignalHub import SignalHub
from Execution import BacktestExecution
from Evaluation import Evaluation

STRATEGY_MAP = {
    "MomentumStrategy": MomentumStrategy,
    "SmaCrossStrategy": SmaCrossStrategy
}
DATA_OPTIONS = [
    {"label": "KTB 1d", "value": ("1d", "KTB")},
]

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.H2("FI Alogrithm Trading", style={"margin-bottom": "40px"}),
        html.Label("전략 선택", style={"font-weight": "bold"}),
        dcc.Dropdown(
            id='strategy-dropdown',
            options=[{"label": k, "value": k} for k in STRATEGY_MAP.keys()],
            value="MomentumStrategy",
            style={"margin-bottom": "20px"}
        ),
        html.Label("데이터 선택", style={"font-weight": "bold"}),
        dcc.Dropdown(
            id='data-dropdown',
            options=[{"label": d["label"], "value": str(d["value"])} for d in DATA_OPTIONS],
            value=str(("1d", "KTB")),
            style={"margin-bottom": "20px"}
        ),
        html.Button("Backtest 실행", id="run-backtest", n_clicks=0, style={"width": "100%", "margin-bottom": "20px"}),
        html.Hr(),
        html.Div("향후: 실시간 모니터링, 전략 파라미터, 로그 등 확장 영역", style={"font-size": "12px", "color": "#888"}),
    ], style={
        "width": "22%", "display": "inline-block", "verticalAlign": "top",
        "padding": "30px 20px 20px 20px", "background": "#f8f9fa", "height": "100vh", "boxSizing": "border-box"
    }),

    html.Div([
        html.H3("백테스트 결과", style={"margin-top": "10px"}),
        dcc.Graph(id="pnl-graph", style={"height": "400px"}),
        dcc.Graph(id="daily-pnl-graph", style={"height": "320px"}),
        html.Div(id="metrics-output", style={"margin-top": "20px", "font-size": "16px"}),
        html.H4("거래 내역", style={"margin-top": "30px"}),
        dash_table.DataTable(
            id='trade-table',
            columns=[
                {"name": "진입/청산", "id": "side"},
                {"name": "가격", "id": "price", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "손익", "id": "pnl", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "누적손익", "id": "cum_pnl", "type": "numeric", "format": {"specifier": ".3f"}},
            ],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
            page_size=20,
        ),
    ], style={
        "width": "76%", "display": "inline-block", "verticalAlign": "top",
        "padding": "30px 40px 20px 20px", "background": "#fff", "height": "100vh", "boxSizing": "border-box"
    }),
], style={"font-family": "Segoe UI, sans-serif", "background": "#e9ecef", "height": "100vh"})

@app.callback(
    [Output("pnl-graph", "figure"),
     Output("daily-pnl-graph", "figure"),
     Output("metrics-output", "children"),
     Output("trade-table", "data")],
    [Input("run-backtest", "n_clicks")],
    [State("strategy-dropdown", "value"),
     State("data-dropdown", "value")]
)
def run_backtest(n_clicks, strategy_name, data_value):
    if n_clicks == 0:
        return go.Figure(), go.Figure(), "", []
    interval, asset = eval(data_value)
    data_stream = MockDataStream(interval, asset)
    position_manager = PositionManager()
    signal_hub = SignalHub(data_stream, position_manager)
    strategy = STRATEGY_MAP[strategy_name]()
    signal_hub.add_strategy(strategy)
    backtest = BacktestExecution(signal_hub, position_manager)
    backtest.run()
    evaluator = Evaluation(position_manager)
    # 전체 가격 데이터
    price_series = data_stream.data['close'].reset_index(drop=True) if hasattr(data_stream, 'data') and not data_stream.data.empty else None
    # 누적 손익
    daily_pnl = evaluator.get_daily_pnl(strategy_name)
    trade_log = evaluator.get_trade_log(strategy_name)
    # 거래 발생 시점 인덱스(가격 시계열 기준)
    trade_indices = []
    if not trade_log.empty and price_series is not None:
        # 거래가 발생한 가격 시계열 인덱스 찾기
        for price in trade_log['price']:
            idx = price_series[price_series == price].index
            # 여러 번 체결된 가격이 있을 수 있으니, 사용된 인덱스는 제외
            idx = [i for i in idx if i not in trade_indices]
            if idx:
                trade_indices.append(idx[0])
            else:
                trade_indices.append(None)
    # 누적 손익을 가격 시계열 길이에 맞게 forward fill
    cum_pnl = pd.Series(0, index=range(len(price_series)))
    if not trade_log.empty and trade_indices:
        pnl = trade_log["pnl"] = trade_log["price"].diff().fillna(0)
        trade_log["pnl"] = trade_log["pnl"].where(trade_log["side"] == "SELL", 0)
        trade_log["cum_pnl"] = trade_log["pnl"].cumsum()
        last_pnl = 0
        trade_ptr = 0
        for i in range(len(price_series)):
            if trade_ptr < len(trade_indices) and i == trade_indices[trade_ptr]:
                last_pnl = trade_log["cum_pnl"].iloc[trade_ptr]
                trade_ptr += 1
            cum_pnl.iloc[i] = last_pnl
        # 삼각형 마커 위치
        entry_idx = [trade_indices[i] for i, row in trade_log.iterrows() if row['side'] == 'BUY' and trade_indices[i] is not None]
        entry_price = [trade_log['price'].iloc[i] for i in range(len(trade_log)) if trade_log['side'].iloc[i] == 'BUY' and trade_indices[i] is not None]
        exit_idx = [trade_indices[i] for i, row in trade_log.iterrows() if row['side'] == 'SELL' and trade_indices[i] is not None]
        exit_price = [trade_log['price'].iloc[i] for i in range(len(trade_log)) if trade_log['side'].iloc[i] == 'SELL' and trade_indices[i] is not None]
    else:
        entry_idx, entry_price, exit_idx, exit_price = [], [], [], []
    # 가격+진입/청산+누적손익 그래프
    fig = go.Figure()
    if price_series is not None:
        fig.add_trace(go.Scatter(
            y=price_series, mode='lines', name='Price', line=dict(color='gray', width=1), opacity=0.5
        ))
    if entry_idx:
        fig.add_trace(go.Scatter(
            x=entry_idx, y=entry_price, mode='markers', name='Buy',
            marker=dict(symbol='triangle-up', color='green', size=12)
        ))
    if exit_idx:
        fig.add_trace(go.Scatter(
            x=exit_idx, y=exit_price, mode='markers', name='Sell',
            marker=dict(symbol='triangle-down', color='red', size=12)
        ))
    if not cum_pnl.empty:
        fig.add_trace(go.Scatter(
            y=cum_pnl, mode='lines', name='Cumulative PnL', yaxis='y2', line=dict(color='blue', width=2)
        ))
        fig.update_layout(
            yaxis2=dict(overlaying='y', side='right', title='Cumulative PnL'),
            title="가격 + 진입/청산 + 누적손익",
            xaxis_title="Timestamp",
            yaxis_title="Price",
            template="plotly_white"
        )
    # 일별 손익 bar chart
    bar_fig = go.Figure()
    if not daily_pnl.empty:
        bar_fig.add_trace(go.Bar(y=daily_pnl, name='Daily PnL'))
        bar_fig.update_layout(
            title="일별 손익(Daily PnL)",
            xaxis_title="Trade #",
            yaxis_title="Daily PnL",
            template="plotly_white"
        )
    # 거래내역 표
    if not trade_log.empty:
        trade_log["pnl"] = trade_log["price"].diff().fillna(0)
        trade_log["pnl"] = trade_log["pnl"].where(trade_log["side"] == "SELL", 0)
        trade_log["cum_pnl"] = trade_log["pnl"].cumsum()
        trade_log["price"] = trade_log["price"].round(3)
        trade_log["pnl"] = trade_log["pnl"].round(3)
        trade_log["cum_pnl"] = trade_log["cum_pnl"].round(3)
        table_data = trade_log.to_dict("records")
    else:
        table_data = []
    metrics = evaluator.summary(strategy_name, print_result=False)
    return fig, bar_fig, metrics, table_data

if __name__ == "__main__":
    app.run(debug=True)