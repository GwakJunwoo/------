import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

from pages import home, page2, page3, page4, page5, page6

# 기존 DashBoard.py에서 사용하던 import도 추가
from DataStream import MockDataStream
from Strategy import *
from Position import PositionManager
from SignalHub import SignalHub
from Execution import BacktestExecution
from Evaluation import Evaluation
import plotly.graph_objs as go
import pandas as pd

STRATEGY_MAP = {
    "MomentumStrategy": MomentumStrategy,
    "SmaCrossStrategy": SmaCrossStrategy
}


app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

# app.py 예시
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([
        html.Div([
            html.H2("KIS FI System", style={"margin-bottom": "40px", "font-weight": "bold"}),
            dbc.Nav(
                [
                    dbc.NavLink("Algorithm", href="/", active="exact", className="sidebar-link"),
                    dbc.NavLink("Position", href="/page2", active="exact", className="sidebar-link"),
                    dbc.NavLink("Details", href="/page3", active="exact", className="sidebar-link"),
                    dbc.NavLink("Debt", href="/page4", active="exact", className="sidebar-link"),
                    dbc.NavLink("Analysis", href="/page5", active="exact", className="sidebar-link"),
                    dbc.NavLink("Database", href="/page6", active="exact", className="sidebar-link"),
                ],
                vertical=True,
                pills=True,
                className="sidebar-nav"
            ),
        ], className="sidebar"),
        html.Div(id='page-content', className="content")
    ], className="layout-root")
])

@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == "/page2":
        return page2.layout
    elif pathname == "/page3":
        return page3.layout
    elif pathname == "/page4":
        return page4.layout
    elif pathname == "/page5":
        return page5.layout
    elif pathname == "/page6":
        return page6.layout
    else:
        return home.layout

def make_cum_pnl_series_realized_only(trade_log):
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

    #MockDataStream을 사용하려면 주석 해제
    #data_stream = MockDataStream(interval, asset)

    # HistoricalDataStream을 사용하려면 주석 해제

    # ==============================================
    interval = 60
    asset = "KTB3F"
    from_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    data_stream = HistoricalDataStream(interval, asset, from_date)

    # ==============================================

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
        if not pd.api.types.is_datetime64_any_dtype(trade_log["date"]):
            trade_log["date"] = pd.to_datetime(trade_log["date"])
    else:
        trade_log["cum_pnl"] = []

    fig = go.Figure()
    bar_fig = go.Figure()

    if not trade_log.empty:
        cum_pnl_series = make_cum_pnl_series_realized_only(trade_log)
        price_series = None
        date_series = None
        if hasattr(data_stream, 'data') and not data_stream.data.empty:
            price_series = data_stream.data['close'].reset_index(drop=True)
            if 'Date' in data_stream.data.columns:
                date_series = pd.to_datetime(data_stream.data['Date']).reset_index(drop=True)
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
            x=cum_pnl_series.index, y=cum_pnl_series, mode='lines', name='Cumulative PnL', yaxis='y2', line=dict(color='blue', width=2)
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
        fig = go.Figure()
        bar_fig = go.Figure()

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