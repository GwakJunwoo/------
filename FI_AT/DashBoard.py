import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.graph_objs as go
import pandas as pd

from DataStream import MockDataStream
from Strategy import *
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
                {"name": "날짜", "id": "Date"},
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

def make_cum_pnl_series_realized_only(price_series, trade_log, date_series):
    """
    진입/청산 시점에만 누적손익을 업데이트(실현손익만 반영, trade_log 기준)
    """
    cum_pnl = []
    realized_pnl = 0
    trade_ptr = 0
    trade_log = trade_log.reset_index(drop=True)
    # tick_idx 생성
    if "tick_idx" not in trade_log.columns and not trade_log.empty:
        tick_indices = []
        used = set()
        for price in trade_log["price"]:
            idx = (abs(price_series - price)).idxmin()
            if idx not in used:
                tick_indices.append(idx)
                used.add(idx)
            else:
                tick_indices.append(None)
        trade_log["tick_idx"] = tick_indices

    # 누적손익 시계열: 거래 발생 시점에만 값이 점프, 나머지는 이전 값 유지
    tick_idx_to_cum_pnl = {}
    running_pnl = 0
    for i, row in trade_log.iterrows():
        idx = row["tick_idx"]
        if pd.notnull(idx) and 0 <= int(idx) < len(price_series):
            running_pnl += row["pnl"]
            tick_idx_to_cum_pnl[int(idx)] = running_pnl

    cum_pnl = []
    last_pnl = 0
    for i in range(len(price_series)):
        if i in tick_idx_to_cum_pnl:
            last_pnl = tick_idx_to_cum_pnl[i]
        cum_pnl.append(last_pnl)
    return pd.Series(cum_pnl, index=date_series)

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

    trade_log = evaluator.get_trade_log(strategy_name)
    if not trade_log.empty:
        trade_log["cum_pnl"] = trade_log["pnl"].cumsum()
    else:
        trade_log["cum_pnl"] = []

    # 날짜 시계열 추출
    if hasattr(data_stream, 'data') and not data_stream.data.empty:
        price_series = data_stream.data['close'].reset_index(drop=True)
        if 'Date' in data_stream.data.columns:
            date_series = pd.to_datetime(data_stream.data['Date']).reset_index(drop=True)
        else:
            date_series = data_stream.data.index
    else:
        price_series = None
        date_series = None

    fig = go.Figure()
    bar_fig = go.Figure()

    # 누적손익 시계열 생성 (실현손익만 반영)
    if price_series is not None and not trade_log.empty:
        cum_pnl_series = make_cum_pnl_series_realized_only(price_series, trade_log, date_series)
    else:
        cum_pnl_series = pd.Series([0] * len(price_series), index=date_series) if price_series is not None else pd.Series([])

    # 진입/청산 마커: 날짜 기준으로 맞추기
    entry_dates, entry_price, exit_dates, exit_price = [], [], [], []
    if not trade_log.empty and "tick_idx" in trade_log.columns:
        entry_mask = trade_log["side"].str.contains("ENTRY")
        exit_mask = trade_log["side"].str.contains("EXIT|STOPLOSS|TAKEPROFIT")
        entry_idx = trade_log.loc[entry_mask, "tick_idx"].dropna().astype(int).tolist()
        exit_idx = trade_log.loc[exit_mask, "tick_idx"].dropna().astype(int).tolist()
        if date_series is not None:
            entry_dates = [date_series.iloc[i] for i in entry_idx if 0 <= i < len(date_series)]
            entry_price = [price_series.iloc[i] for i in entry_idx if 0 <= i < len(price_series)]
            exit_dates = [date_series.iloc[i] for i in exit_idx if 0 <= i < len(date_series)]
            exit_price = [price_series.iloc[i] for i in exit_idx if 0 <= i < len(price_series)]

    # 가격+진입/청산+누적손익 그래프 (x축: 날짜)
    if price_series is not None:
        fig.add_trace(go.Scatter(
            x=date_series, y=price_series, mode='lines', name='Price', line=dict(color='gray', width=1), opacity=0.5
        ))
    if entry_dates and entry_price:
        fig.add_trace(go.Scatter(
            x=entry_dates, y=entry_price, mode='markers', name='Entry',
            marker=dict(symbol='triangle-up', color='green', size=12)
        ))
    if exit_dates and exit_price:
        fig.add_trace(go.Scatter(
            x=exit_dates, y=exit_price, mode='markers', name='Exit',
            marker=dict(symbol='triangle-down', color='red', size=12)
        ))
    if not cum_pnl_series.empty:
        fig.add_trace(go.Scatter(
            x=cum_pnl_series.index, y=cum_pnl_series, mode='lines', name='Cumulative PnL', yaxis='y2', line=dict(color='blue', width=2)
        ))
        fig.update_layout(
            yaxis2=dict(overlaying='y', side='right', title='Cumulative PnL'),
            title="가격 + 진입/청산 + 누적손익",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_white"
        )

    # 일별 손익 bar chart (x축: 날짜)
    if not cum_pnl_series.empty:
        daily_pnl = cum_pnl_series.diff().fillna(0)
        bar_fig.add_trace(go.Bar(x=cum_pnl_series.index, y=daily_pnl, name='PnL'))
        bar_fig.update_layout(
            title="PnL (시계열 기준)",
            xaxis_title="Date",
            yaxis_title="PnL",
            template="plotly_white"
        )

    # 거래내역 표
    if not trade_log.empty:
        if "tick_idx" in trade_log.columns and date_series is not None:
            trade_log["Date"] = [
                date_series.iloc[i] if pd.notnull(i) and 0 <= int(i) < len(date_series) else None
                for i in trade_log["tick_idx"]
            ]
        trade_log["price"] = trade_log["price"].round(2)
        trade_log["pnl"] = trade_log["pnl"].round(3)
        trade_log["cum_pnl"] = trade_log["cum_pnl"].round(3)
        columns = ["Date", "side", "price", "pnl", "cum_pnl"]
        columns_exist = [col for col in columns if col in trade_log.columns]
        table_data = trade_log[columns_exist].to_dict("records")
    else:
        table_data = []

    metrics = evaluator.summary(strategy_name, print_result=False)
    return fig, bar_fig, metrics, table_data

if __name__ == "__main__":
    app.run(debug=True)