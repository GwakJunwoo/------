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
                {"name": "날짜", "id": "date"},
                {"name": "진입/청산", "id": "side"},
                {"name": "현재가", "id": "price", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "평단가", "id": "average_price", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "포지션", "id": "pos", "type": "numeric"},
                {"name": "손익", "id": "pnl", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "누적손익", "id": "cum_pnl", "type": "numeric", "format": {"specifier": ".3f"}},
            ],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
            page_size=20,
            style_data_conditional=[
                {
                    "if": {
                        "filter_query": '{side} contains "EXIT" || {side} contains "STOPLOSS" || {side} contains "TAKEPROFIT"'
                    },
                    "backgroundColor": "#f16969"  # 밝은 빨간색
                }
            ],
        ),

    ], style={
        "width": "76%", "display": "inline-block", "verticalAlign": "top",
        "padding": "30px 40px 20px 20px", "background": "#fff", "height": "100vh", "boxSizing": "border-box"
    }),
], style={"font-family": "Segoe UI, sans-serif", "background": "#e9ecef", "height": "100vh"})

def make_cum_pnl_series_realized_only(trade_log):
    """
    trade_log의 Date를 인덱스로 누적손익 시계열 생성 (실현손익만 반영)
    """
    if trade_log.empty:
        return pd.Series(dtype=float)
    cum_pnl = trade_log["pnl"].cumsum()
    return pd.Series(cum_pnl.values, index=pd.to_datetime(trade_log["date"]))

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
        # Date 컬럼이 datetime이 아니면 변환
        if not pd.api.types.is_datetime64_any_dtype(trade_log["date"]):
            trade_log["date"] = pd.to_datetime(trade_log["date"])
    else:
        trade_log["cum_pnl"] = []

    fig = go.Figure()
    bar_fig = go.Figure()

    # 누적손익 시계열 (trade_log 기준)
    if not trade_log.empty:
        cum_pnl_series = make_cum_pnl_series_realized_only(trade_log)
        # 가격 시계열이 있으면 price_series도 표시
        price_series = None
        date_series = None
        # 가격 시계열 추출 (선택)
        if hasattr(data_stream, 'data') and not data_stream.data.empty:
            price_series = data_stream.data['close'].reset_index(drop=True)
            if 'Date' in data_stream.data.columns:
                date_series = pd.to_datetime(data_stream.data['Date']).reset_index(drop=True)
            else:
                date_series = data_stream.data.index
        # 가격+진입/청산+누적손익 그래프
        if price_series is not None and date_series is not None:
            fig.add_trace(go.Scatter(
                x=date_series, y=price_series, mode='lines', name='Price', line=dict(color='gray', width=1), opacity=0.5
            ))
        # 진입/청산 마커
    
            # 진입/청산 마커 (롱/숏/청산 구분)
            long_entry_mask = trade_log["side"].str.contains("LONG_ENTRY")
            short_entry_mask = trade_log["side"].str.contains("SHORT_ENTRY")
            exit_mask = trade_log["side"].str.contains("EXIT|STOPLOSS|TAKEPROFIT")
    
            # 롱 진입: 초록 위 삼각형
            if trade_log.loc[long_entry_mask, "date"].size > 0:
                fig.add_trace(go.Scatter(
                    x=trade_log.loc[long_entry_mask, "date"],
                    y=trade_log.loc[long_entry_mask, "price"],
                    mode='markers',
                    name='Long Entry',
                    marker=dict(symbol='triangle-up', color='green', size=12)
                ))
            # 숏 진입: 빨강 아래 삼각형
            if trade_log.loc[short_entry_mask, "date"].size > 0:
                fig.add_trace(go.Scatter(
                    x=trade_log.loc[short_entry_mask, "date"],
                    y=trade_log.loc[short_entry_mask, "price"],
                    mode='markers',
                    name='Short Entry',
                    marker=dict(symbol='triangle-down', color='red', size=12)
                ))
            # 청산: 파란 원
            if trade_log.loc[exit_mask, "date"].size > 0:
                fig.add_trace(go.Scatter(
                    x=trade_log.loc[exit_mask, "date"],
                    y=trade_log.loc[exit_mask, "price"],
                    mode='markers',
                    name='Exit',
                    marker=dict(symbol='circle', color='blue', size=10)
                ))
    
        # 누적손익
        fig.add_trace(go.Scatter(
            x=cum_pnl_series.index, y=cum_pnl_series, mode='lines', name='Cumulative PnL', yaxis='y2', line=dict(color='blue', width=2)
        ))
        fig.update_layout(
            yaxis2=dict(overlaying='y', side='right', title='Cumulative PnL'),
            title="가격 + 진입/청산 + 누적손익",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_white",
            legend=dict(
                orientation="h",           # 수평 정렬
                yanchor="bottom",
                y=-0.3,                   # 그래프 하단에 위치
                xanchor="center",
                x=0.5
            )
        )
        # 거래별 손익 bar chart (trade_log 기준)
        bar_fig.add_trace(go.Bar(
            x=trade_log["date"],
            y=trade_log["pnl"],
            name='Trade PnL',
            marker_color='orange'
        ))
        bar_fig.update_layout(
            title="거래별 손익 (표와 동일)",
            xaxis_title="Date",
            yaxis_title="PnL",
            template="plotly_white"
        )
    else:
        cum_pnl_series = pd.Series(dtype=float)
        # 빈 그래프
        fig = go.Figure()
        bar_fig = go.Figure()

    # 거래내역 표
    if not trade_log.empty:
        trade_log["date"] = pd.to_datetime(trade_log["date"])
        trade_log["price"] = trade_log["price"].round(3)
        trade_log["average_price"] = trade_log["average_price"].round(3)
        trade_log["pos"] = trade_log["pos"].astype(int)
        trade_log["pnl"] = trade_log["pnl"].round(3)
        trade_log["cum_pnl"] = trade_log["cum_pnl"].round(3)
        columns = ["date", "side", "price", "average_price", "pos", "pnl", "cum_pnl"]
        columns_exist = [col for col in columns if col in trade_log.columns]
        table_data = trade_log[columns_exist].to_dict("records")
    else:
        table_data = []

    metrics = evaluator.summary(strategy_name, print_result=False)
    return fig, bar_fig, metrics, table_data

if __name__ == "__main__":
    app.run(debug=True)