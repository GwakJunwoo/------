import dash
from dash import dcc, html, Input, Output, State
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
        html.H2("Algo Trading Dashboard", style={"margin-bottom": "40px"}),
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
        html.Div(id="metrics-output", style={"margin-top": "30px", "font-size": "16px"}),
    ], style={
        "width": "76%", "display": "inline-block", "verticalAlign": "top",
        "padding": "30px 40px 20px 20px", "background": "#fff", "height": "100vh", "boxSizing": "border-box"
    }),
], style={"font-family": "Segoe UI, sans-serif", "background": "#e9ecef", "height": "100vh"})

@app.callback(
    [Output("pnl-graph", "figure"),
     Output("metrics-output", "children")],
    [Input("run-backtest", "n_clicks")],
    [State("strategy-dropdown", "value"),
     State("data-dropdown", "value")]
)
def run_backtest(n_clicks, strategy_name, data_value):
    if n_clicks == 0:
        return go.Figure(), ""
    interval, asset = eval(data_value)
    data_stream = MockDataStream(interval, asset)
    position_manager = PositionManager()
    signal_hub = SignalHub(data_stream, position_manager)
    strategy = STRATEGY_MAP[strategy_name]()
    signal_hub.add_strategy(strategy)
    backtest = BacktestExecution(signal_hub, position_manager)
    backtest.run()
    evaluator = Evaluation(position_manager)
    daily_pnl = evaluator.get_daily_pnl(strategy_name)
    cum_pnl = daily_pnl.cumsum() if not daily_pnl.empty else pd.Series()
    fig = go.Figure()
    if not cum_pnl.empty:
        fig.add_trace(go.Scatter(y=cum_pnl, mode='lines', name='Cumulative PnL'))
        fig.update_layout(
            title="누적 손익(Cumulative PnL)",
            xaxis_title="Trade #",
            yaxis_title="PnL",
            template="plotly_white"
        )
    metrics = evaluator.summary(strategy_name, print_result=False)
    return fig, metrics

if __name__ == "__main__":
    app.run(debug=True)