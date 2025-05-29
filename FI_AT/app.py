import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

from pages import home, page2, page3, page4, page5, page6

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

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

if __name__ == "__main__":
    app.run(debug=True)