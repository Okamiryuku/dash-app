from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from dash_bootstrap_templates import load_figure_template

import plotly.express as px
import pandas as pd

resorts = (
    pd.read_csv("/resorts.csv", encoding = "ISO-8859-1")
    .assign(
        country_elevation_rank = lambda x: x.groupby("Country", as_index=False)["Highest point"].rank(ascending=False),
        country_price_rank = lambda x: x.groupby("Country", as_index=False)["Price"].rank(ascending=False),
        country_slope_rank = lambda x: x.groupby("Country", as_index=False)["Total slopes"].rank(ascending=False),
        country_cannon_rank = lambda x: x.groupby("Country", as_index=False)["Snow cannons"].rank(ascending=False),
    ))


dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

app = Dash(__name__, external_stylesheets=[dbc.themes.SLATE, dbc_css])

load_figure_template("SLATE")

app.layout = html.Div([
    dcc.Tabs(
        id="tabs",
        className="dbc",
        value="tab1",
        children=[
            dcc.Tab(
                label="Map of Skiing Hotspots",
                value="tab1",
                children=[
                    html.H1(id="title", style={"text-align": "center"}),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dcc.Markdown("**Price Limit**"),
                                dcc.Slider(id="price-slider", min=0, max=150, step=25, value=150, className="dbc"),
                                html.Br(),
                                dcc.Markdown("**Feature Preferences**"),
                                dcc.RadioItems(
                                    id="night-ski-toggle",
                                    options=[
                                        {"label": "Has Night Skiing", "value": "Yes"},
                                        {"label": "No Night Skiing", "value": "No"}],
                                    value="No",
                                    style={"margin-bottom": "10px"},
                                    className="dbc"
                                ),
                                dcc.RadioItems(
                                    id="summer-ski-toggle",
                                    options=[
                                        {"label": "Has Summer Skiing", "value": "Yes"},
                                        {"label": "No Summer Skiing", "value": "No"}],
                                    value="No",
                                    style={"margin-bottom": "10px"},
                                    className="dbc"
                                ),
                                dcc.RadioItems(
                                    id="snowpark-toggle",
                                    options=[
                                        {"label": "Has Snowpark", "value": "Yes"},
                                        {"label": "No Snowpark", "value": "No"}],
                                    value="No",
                                    style={"margin-bottom": "10px"},
                                    className="dbc"
                                )
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card(
                                dcc.Graph(id="resort-map")
                            )
                        ])
                    ])
                ]

            ),
            dcc.Tab(
                label="Country report & Resort Report card",
                value="tab2",
                children = [
                    html.H1(id="title2", style={"text-align": "center"}),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dcc.Markdown("Select A Continent:"),
                                dcc.Dropdown(
                                    id="continent-dropdown",
                                    options=resorts.Continent.unique(),
                                    value="United States",
                                    className="dbc"
                                ),
                                html.Br(),
                                dcc.Markdown("Select A Country:"),
                                dcc.Dropdown(
                                    id="country-dropdown",
                                    className="dbc"
                                ),
                                html.Br(),
                                dcc.Markdown("Select A Metric to Plot:"),
                                dcc.Dropdown(
                                    id="column-picker",
                                    options=resorts.select_dtypes("number").columns[3:],
                                    value="Price",
                                    className="dbc"
                                )
                            ])
                        ], width=3),
                        dbc.Col([
                            dcc.Graph(id="metric-bar",
                                      hoverData={'points': [{'customdata': ['Hemsedal']}]})
                        ], width=6),
                        dbc.Col([
                            dcc.Markdown("### Resort Report Card"),
                            dbc.Card(id="resort-name", style={"text-align": "center", "fontSize":20}),
                            dbc.Row([
                                dbc.Col([dbc.Card(id="elevation-kpi"), dbc.Card(id="price-kpi")]),
                                dbc.Col([dbc.Card(id="slope-kpi"), dbc.Card(id="cannon-kpi")]),
                            ])
                        ], width=3)
                    ])
                ])
        ])
])


@app.callback(
    Output("title", "children"),
    Output("resort-map", "figure"),
    Input("price-slider", "value"),
    Input("night-ski-toggle", "value"),
    Input("summer-ski-toggle", "value"),
    Input("snowpark-toggle", "value")
)
def snow_map(price, night_ski, summer_ski, snowpark):
    title = f"Resorts with a ticket price less than ${price}."
    df_map = resorts.loc[(resorts["Price"] < price) &
                         (resorts["Nightskiing"] == night_ski) &
                         (resorts["Summer skiing"] == summer_ski) &
                         (resorts["Snowparks"] == snowpark)]
    map = px.density_mapbox(
        df_map,
        lat="Latitude",
        lon="Longitude",
        z="Total slopes",
        hover_name="Resort",
        center={"lat": 45, "lon": -100},
        zoom=2.5,
        mapbox_style="open-street-map",
        color_continuous_scale="redor",
        height=1000
    )
    return title, map


@app.callback(
    Output("country-dropdown", "options"),
    Input("continent-dropdown", "value")
)
def country_dropdown(continent):
    country=resorts.query("Continent in @continent")
    return country.Country.unique()


@app.callback(
    Output("title2", "children"),
    Output("metric-bar", "figure"),
    Input("country-dropdown", "value"),
    Input("column-picker", "value"),
)
def bar_info(country, column):
    if not country and column:
        raise PreventUpdate

    title2 = f"Top Resorts in {country} by {column}"
    df = resorts.query("Country in @country")
    fig = px.bar(
        df.sort_values(column, ascending=False),
        x="Resort",
        y=column,
        custom_data=["Resort"]).update_xaxes(showticklabels=False)

    return title2, fig


@app.callback(
    Output("resort-name", "children"),
    Output("elevation-kpi", "children"),
    Output("price-kpi", "children"),
    Output("slope-kpi", "children"),
    Output("cannon-kpi", "children"),
    Input("metric-bar", "hoverData"))
def report_card(hoverData):
    resort = hoverData["points"][0]["customdata"][0]

    df = resorts.query("Resort == @resort")

    elev_rank = f"Elevation Rank: {int(df['country_elevation_rank'])}"
    price_rank = f"Price Rank: {int(df['country_price_rank'])}"
    slope_rank = f"Slope Rank: {int(df['country_slope_rank'])}"
    cannon_rank = f"Cannon Rank: {int(df['country_cannon_rank'])}"

    return resort, elev_rank, price_rank, slope_rank, cannon_rank


if __name__ == '__main__':
    app.run(debug=True, port='5010')
