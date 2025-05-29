from dash import dcc, html, dash_table, Input, Output, State, callback
import plotly.graph_objs as go
import pandas as pd

from DataStream import MockDataStream, HistoricalDataStream
from Strategy import MomentumStrategy, SmaCrossStrategy
from Position import PositionManager
from SignalHub import SignalHub
from Execution import BacktestExecution
from Evaluation import Evaluation

STRATEGY_OPTIONS = [
    {"label": "MomentumStrategy", "value": "MomentumStrategy"},
    {"label": "SmaCrossStrategy", "value": "SmaCrossStrategy"}
]

ASSET_OPTIONS = [
    {"label": asset, "value": asset} for asset in [
        "ETHUSDT_PERP", "BTCUSDT_PERP", "XRPUSDT_PERP", "ETHUSDT",
        "KTB10F", "KTB3F", "SOLUSDT_PERP", "PAXGUSDT_PERP",
        "TRUMPUSDT_PERP", "XMRUSDT_PERP", "ZN", "BTCUSD",
        "ETHUSD", "ZT"
    ]
]

INTERVAL_OPTIONS = [
    {"label": str(i), "value": i} for i in [1, 5, 15, 30, 60, 240, 1440]
]

VENDOR_OPTIONS = [
    {"label": "Mock", "value": "Mock"},
    {"label": "Historical", "value": "Historical"}
]

STRATEGY_MAP = {
    "MomentumStrategy": MomentumStrategy,
    "SmaCrossStrategy": SmaCrossStrategy
}

layout = html.Div([
    html.Div([
        html.H2("FI Algorithm Trading", style={"margin-bottom": "40px"}),
        html.Label("데이터 벤더", style={"font-weight": "bold"}),
        dcc.Dropdown(
            id='vendor-dropdown',
            options=VENDOR_OPTIONS,
            value="Mock",
            style={"margin-bottom": "20px"}
        ),
        html.Label("전략 선택", style={"font-weight": "bold"}),
        dcc.Dropdown(
            id='strategy-dropdown',
            options=STRATEGY_OPTIONS,
            value="MomentumStrategy",
            style={"margin-bottom": "20px"}
        ),
        html.Label("자산 선택", style={"font-weight": "bold"}),
        dcc.Dropdown(
            id='asset-dropdown',
            options=ASSET_OPTIONS,
            value="KTB3F",
            style={"margin-bottom": "20px"}
        ),
        html.Label("Interval (분)", style={"font-weight": "bold"}),
        dcc.Dropdown(
            id='interval-dropdown',
            options=INTERVAL_OPTIONS,
            value=60,
            style={"margin-bottom": "20px"}
        ),
        html.Button("Backtest 실행", id="run-backtest", n_clicks=0, style={"width": "100%", "margin-bottom": "20px"}),
        html.Hr(),
        html.Div("향후: 조건 서식 등 추가 확장 영역", style={"font-size": "12px", "color": "#888"}),
    ], style={
        "margin-bottom": "30px",
        "background": "#f8f9fa",
        "padding": "30px 20px 20px 20px",
        "border-radius": "8px"
    }),

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
        data=[],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center"},
        style_header={"fontWeight": "bold"},
        page_size=20,
        style_data_conditional=[
            {
                "if": {
                    "filter_query": '{side} contains "EXIT" || {side} contains "STOPLOSS" || {side} contains "TAKEPROFIT"'
                },
                "backgroundColor": "#f16969"
            }
        ],
    ),
], className="content")

@callback(
    Output("pnl-graph", "figure"),
    Output("daily-pnl-graph", "figure"),
    Output("metrics-output", "children"),
    Output("trade-table", "data"),
    Input("run-backtest", "n_clicks"),
    State("vendor-dropdown", "value"),
    State("asset-dropdown", "value"),
    State("interval-dropdown", "value"),
    State("strategy-dropdown", "value"),
    prevent_initial_call=True
)
def run_backtest(n_clicks, vendor, asset, interval, strategy_name):
    import datetime
    if n_clicks == 0:
        return go.Figure(), go.Figure(), "", []

    # 데이터 스트림 선택
    if vendor == "Mock":
        data_stream = MockDataStream(interval, asset)
    else:
        from_date = (datetime.datetime.now() - datetime.timedelta(days=365/4)).strftime("%Y-%m-%d")
        data_stream = HistoricalDataStream(interval, asset, from_date)

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
        # x축용 날짜는 항상 datetime으로 변환
        if not pd.api.types.is_datetime64_any_dtype(trade_log["date"]):
            trade_log["date"] = pd.to_datetime(trade_log["date"])
    else:
        trade_log["cum_pnl"] = []

    # 가격+진입/청산+누적손익 그래프
    fig = go.Figure()
    # 거래별 손익 바그래프
    bar_fig = go.Figure()

    if not trade_log.empty:
        # 가격 시계열
        price_series = None
        date_series = None
        if hasattr(data_stream, 'data') and not data_stream.data.empty:
            price_series = data_stream.data['close'].reset_index(drop=True)
            if 'Date' in data_stream.data.columns:
                date_series = pd.to_datetime(data_stream.data['Date']).reset_index(drop=True)
            elif 'trade_date' in data_stream.data.columns:
                date_series = pd.to_datetime(data_stream.data['trade_date']).reset_index(drop=True)
            else:
                date_series = data_stream.data.index

        # 가격선
        if price_series is not None and date_series is not None:
            fig.add_trace(go.Scatter(
                x=date_series, y=price_series, mode='lines', name='Price', line=dict(color='gray', width=1), opacity=0.5
            ))

        # 진입/청산 마커
        long_entry_mask = trade_log["side"].str.contains("LONG_ENTRY")
        short_entry_mask = trade_log["side"].str.contains("SHORT_ENTRY")
        exit_mask = trade_log["side"].str.contains("EXIT|STOPLOSS|TAKEPROFIT")

        if trade_log.loc[long_entry_mask, "date"].size > 0:
            fig.add_trace(go.Scatter(
                x=trade_log.loc[long_entry_mask, "date"],
                y=trade_log.loc[long_entry_mask, "price"],
                mode='markers',
                name='Long Entry',
                marker=dict(symbol='triangle-up', color='green', size=12)
            ))
        if trade_log.loc[short_entry_mask, "date"].size > 0:
            fig.add_trace(go.Scatter(
                x=trade_log.loc[short_entry_mask, "date"],
                y=trade_log.loc[short_entry_mask, "price"],
                mode='markers',
                name='Short Entry',
                marker=dict(symbol='triangle-down', color='red', size=12)
            ))
        if trade_log.loc[exit_mask, "date"].size > 0:
            fig.add_trace(go.Scatter(
                x=trade_log.loc[exit_mask, "date"],
                y=trade_log.loc[exit_mask, "price"],
                mode='markers',
                name='Exit',
                marker=dict(symbol='circle', color='blue', size=10)
            ))

        # 누적손익선
        fig.add_trace(go.Scatter(
            x=trade_log["date"], y=trade_log["cum_pnl"], mode='lines', name='Cumulative PnL', yaxis='y2', line=dict(color='blue', width=2)
        ))

        # 레이아웃
        fig.update_layout(
            yaxis2=dict(overlaying='y', side='right', title='Cumulative PnL'),
            title="가격 + 진입/청산 + 누적손익",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5
            )
        )

        # 거래별 손익 바그래프
        bar_fig = go.Figure()
        bar_fig.add_trace(go.Bar(
            x=trade_log["date"],
            y=trade_log["pnl"],
            name='Trade PnL',
            marker_color='skyblue'
        ))
        # y축 자동조정: 데이터 범위에 맞게, 0이 포함되도록 + 마진
        y_pnl = trade_log["pnl"]
        if len(y_pnl) > 0:
            y_min = y_pnl.min()
            y_max = y_pnl.max()
            # 마진 비율 (10%)
            margin = (y_max - y_min) * 0.1 if y_max != y_min else 1
            y_min_margin = y_min - margin
            y_max_margin = y_max + margin
            # 0이 범위 안에 있으면 0도 포함
            if y_min < 0 < y_max:
                y_min_margin = min(0, y_min_margin)
                y_max_margin = max(0, y_max_margin)
            # 값이 모두 0이거나 한 값만 있을 때
            if y_min == y_max:
                y_min_margin -= 1
                y_max_margin += 1
        else:
            y_min_margin, y_max_margin = -1, 1

        bar_fig.update_layout(
            title="거래별 손익 (표와 동일)",
            xaxis_title="Date",
            yaxis_title="PnL",
            template="plotly_white",
            bargap=0.2,
            xaxis=dict(
                rangeslider=dict(visible=True),
                type="date"
            ),
            yaxis=dict(
                autorange=False,
                range=[y_min_margin, y_max_margin],
                zeroline=True
            )
        )

    # DataTable data
    columns = ["date", "side", "price", "average_price", "pos", "pnl", "cum_pnl"]
    columns_exist = [col for col in columns if col in trade_log.columns]
    table_data = trade_log[columns_exist].to_dict("records") if not trade_log.empty else []

    # Metrics
    metrics = evaluator.summary(strategy_name, print_result=False) if hasattr(evaluator, "summary") else ""

    return fig, bar_fig, metrics, table_data