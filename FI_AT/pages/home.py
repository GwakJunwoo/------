from dash import dcc, html, dash_table

layout = html.Div([
    html.Div([
        html.H2("FI Algorithm Trading", style={"margin-bottom": "40px"}),
        html.Label("전략 선택", style={"font-weight": "bold"}),
        dcc.Dropdown(
            id='strategy-dropdown',
            options=[
                {"label": "MomentumStrategy", "value": "MomentumStrategy"},
                {"label": "SmaCrossStrategy", "value": "SmaCrossStrategy"}
            ],
            value="MomentumStrategy",
            style={"margin-bottom": "20px"}
        ),
        html.Label("데이터 선택", style={"font-weight": "bold"}),
        dcc.Dropdown(
            id='data-dropdown',
            options=[
                {"label": "KTB 1d", "value": "('1d', 'KTB')"}
            ],
            value="('1d', 'KTB')",
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