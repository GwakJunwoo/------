from dash import dcc, html, dash_table, Input, Output, State, callback, callback_context
import dash
import plotly.graph_objs as go
import pandas as pd
import re
import copy

from DataStream import MockDataStream, HistoricalDataStream
from Strategy import *
from Position import PositionManager, PositionManagerCapital
from SignalHub import SignalHub
from Execution import BacktestExecution
from Evaluation import Evaluation

STRATEGY_OPTIONS = [
    {"label": "MomentumStrategy", "value": "MomentumStrategy"},
    {"label": "RateOfChangeStrategy", "value": "RateOfChangeStrategy"},
    {"label": "SmaCrossStrategy", "value": "SmaCrossStrategy"},
    {"label": "MeanReversionStrategy", "value": "MeanReversionStrategy"},
    {"label": "RsiStrategy", "value": "RsiStrategy"},
    {"label": "BollingerBandStrategy", "value": "BollingerBandStrategy"},
    {"label": "MomentumMeanReversionSwitchStrategy", "value": "MomentumMeanReversionSwitchStrategy"},
    {"label": "DonchianCloseBreakoutStrategy", "value": "DonchianCloseBreakoutStrategy"},
    {"label": "ZScoreMeanReversionStrategy", "value": "ZScoreMeanReversionStrategy"},
    {"label": "AdaptiveZScoreMeanRev", "value": "AdaptiveZScoreMeanRev"},
    {"label": "ZScoreLayeredMeanRev", "value": "ZScoreLayeredMeanRev"},
    {"label": "VotingEnsembleStrategy", "value": "VotingEnsembleStrategy"},
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
    {"label": str(i), "value": i} for i in [1, 5, 15, 30, 60, 120, 240, 1440]
]

VENDOR_OPTIONS = [
    {"label": "Historical", "value": "Historical"},
    {"label": "Mock", "value": "Mock"},
]

STRATEGY_MAP = {
    "MomentumStrategy": MomentumStrategy,
    "RateOfChangeStrategy": RateOfChangeStrategy,
    "SmaCrossStrategy": SmaCrossStrategy,
    "MeanReversionStrategy": MeanReversionStrategy,
    "RsiStrategy": RsiStrategy,
    "BollingerBandStrategy": BollingerBandStrategy,
    "MomentumMeanReversionSwitchStrategy": MomentumMeanReversionSwitchStrategy,
    "DonchianCloseBreakoutStrategy": DonchianCloseBreakoutStrategy,
    "ZScoreMeanReversionStrategy": ZScoreMeanReversionStrategy,
    "AdaptiveZScoreMeanRev": AdaptiveZScoreMeanRev,
    "ZScoreLayeredMeanRev": ZScoreLayeredMeanRev,
    "VotingEnsembleStrategy": VotingEnsembleStrategy,
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
    dcc.Loading(
        id="loading-backtest",
        type="circle",
        children=[
            dcc.Graph(id="pnl-graph", style={"height": "400px"}),
            dcc.Graph(id="daily-pnl-graph", style={"height": "320px"}),
            html.Div(id="metrics-output", style={"margin-top": "20px", "font-size": "16px"}),
            html.Div([
                html.H4("거래 내역", style={"margin-top": "30px", "display": "inline-block"}),
                dcc.Checklist(
                    id="return-mode",
                    options=[{"label": "수익률(%)로 보기", "value": "return"}],
                    value=[],
                    style={"float": "right", "margin-right": "10px"}
                ),
            ], style={"width": "100%", "display": "flex", "align-items": "center", "justify-content": "space-between"}),
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
                    {"name": "잔고", "id": "cash", "type": "numeric", "format": {"specifier": ".3f"}}
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
        ]
    ),
], className="content")

@callback(
    Output("pnl-graph", "figure"),
    Output("daily-pnl-graph", "figure"),
    Output("metrics-output", "children"),
    Output("trade-table", "data"),
    Input("run-backtest", "n_clicks"),
    Input("return-mode", "value"),
    State("vendor-dropdown", "value"),
    State("asset-dropdown", "value"),
    State("interval-dropdown", "value"),
    State("strategy-dropdown", "value"),
    State("trade-table", "data"),
    prevent_initial_call=True
)
def unified_callback(n_clicks, return_mode, vendor, asset, interval, strategy_name, current_table_data):
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    # 1. 백테스트 버튼 클릭 시
    if triggered_id == "run-backtest":
        import datetime
        if n_clicks == 0:
            return go.Figure(), go.Figure(), "", []

        # 데이터 스트림 선택
        if vendor == "Mock":
            data_stream = MockDataStream(interval, asset)
        else:
            from_date = (datetime.datetime.now() - datetime.timedelta(days=365/12)).strftime("%Y-%m-%d")
            data_stream = HistoricalDataStream(interval, asset, from_date)

        position_manager = PositionManagerCapital()
        signal_hub = SignalHub(data_stream, position_manager)
        strategy = STRATEGY_MAP[strategy_name]()
        signal_hub.add_strategy(strategy)
        backtest = BacktestExecution(signal_hub, position_manager)
        backtest.run()
        evaluator = Evaluation(position_manager)

        trade_log = evaluator.get_trade_log(strategy_name)
        if not trade_log.empty:
            trade_log["cum_pnl"] = trade_log["pnl"].cumsum()
            if not pd.api.types.is_datetime64_any_dtype(trade_log["date"]):
                trade_log["date"] = pd.to_datetime(trade_log["date"])
        else:
            trade_log["cum_pnl"] = []

        fig = go.Figure()
        bar_fig = go.Figure()

        if not trade_log.empty:
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

            if price_series is not None and date_series is not None:
                fig.add_trace(go.Scatter(
                    x=date_series, y=price_series, mode='lines', name='Price', line=dict(color='gray', width=1), opacity=0.5
                ))

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

            fig.add_trace(go.Scatter(
                x=trade_log["date"], y=trade_log["cum_pnl"], mode='lines', name='Cumulative PnL', yaxis='y2', line=dict(color='blue', width=2)
            ))

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

            bar_fig.add_trace(go.Bar(
                x=trade_log["date"],
                y=trade_log["pnl"],
                name='Trade PnL',
                marker_color='skyblue'
            ))
            y_pnl = trade_log["pnl"]
            if len(y_pnl) > 0:
                y_min = y_pnl.min()
                y_max = y_pnl.max()
                margin = (y_max - y_min) * 0.1 if y_max != y_min else 1
                y_min_margin = y_min - margin
                y_max_margin = y_max + margin
                if y_min < 0 < y_max:
                    y_min_margin = min(0, y_min_margin)
                    y_max_margin = max(0, y_max_margin)
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

        columns = ["date", "side", "price", "average_price", "pos", "pnl", "cum_pnl", "cash"]
        columns_exist = [col for col in columns if col in trade_log.columns]
        table_df = trade_log[columns_exist].copy() if not trade_log.empty else pd.DataFrame(columns=columns_exist)
        table_data = table_df.to_dict("records") if not table_df.empty else []

        metrics = evaluator.summary(strategy_name, print_result=False) if hasattr(evaluator, "summary") else ""
        metrics_table = ""
        # === 전체 수익률 계산 ===
        # === 마지막 단계에서 남아있는 포지션은 시가평가 ===
        try:
            initial_capital = getattr(position_manager, "initial_capital", None)
            # 마지막 거래 가격 구하기
            last_price = None
            if not trade_log.empty:
                last_price = trade_log["price"].iloc[-1]
            # 평가자산(현금+미실현손익)
            if last_price is not None:
                final_equity = position_manager.get_equity(last_price, strategy_name)
            else:
                final_equity = position_manager.get_cash()

            print(f"초기자본: {initial_capital}, 최종평가: {final_equity}")
            if initial_capital and final_equity is not None:
                total_return = (final_equity / initial_capital - 1) * 100
                total_return_str = f"전체 수익률: {total_return:.2f}% (초기자본: {initial_capital:,.0f} → 최종평가: {final_equity:,.0f})"
            else:
                total_return_str = ""
        except Exception as e:
            total_return_str = ""

        if isinstance(metrics, dict):
            rounded_metrics = {k: round(v, 3) if isinstance(v, float) else v for k, v in metrics.items()}
            metrics_table = dash_table.DataTable(
                columns=[{"name": k, "id": k} for k in rounded_metrics.keys()],
                data=[rounded_metrics],
                style_cell={"textAlign": "center"},
                style_header={"fontWeight": "bold"},
                style_table={"marginBottom": "10px"},
            )
        else:
            metrics_table = html.Pre(str(metrics))

        # === 전체 수익률을 metrics_table 위에 출력 ===
        metrics_output = html.Div([
            html.Div(total_return_str, style={"fontWeight": "bold", "fontSize": "18px", "marginBottom": "10px", "color": "#1a7f37"}),
            metrics_table
        ])

        return fig, bar_fig, metrics_output, table_data
    
    # TODO: return-mode 체크박스 기능 구현
    """
    # 2. return-mode 체크박스 변경 시
    elif triggered_id == "return-mode":
        if not current_table_data:
            return dash.no_update, dash.no_update, dash.no_update, current_table_data
        new_data = copy.deepcopy(current_table_data)
        if "return" in return_mode:
            cum_return = 0
            for row in new_data:
                try:
                    avg = float(row.get("average_price", 0))
                    price = float(row.get("price", 0))
                    if avg != 0:
                        # 수익률 계산 이거는 ("EXIT|STOPLOSS|TAKEPROFIT") 이 경우에만 적용
                        if row["side"] in ["EXIT", "STOPLOSS", "TAKEPROFIT"]:
                            ret = (price / avg - 1) * 100
                            row["pnl"] = round(ret, 3)
                            cum_return += ret
                            row["cum_pnl"] = round(cum_return, 3)
                except Exception:
                    pass
        # 체크 해제 시 원본 복구 불가(백테스트 다시 실행해야 함)
        return dash.no_update, dash.no_update, dash.no_update, new_data

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    """