from dash import html, dcc
import os
import pandas as pd

os.chdir(os.path.dirname(os.path.abspath(__file__)))

ANOS_DISPONIBLES = [str(a) for a in range(2017, 2027)]

_DIAS = [{'label': str(d), 'value': f'{d:02d}'} for d in range(1, 32)]
_MESES = [
    {'label': 'Ene', 'value': '01'}, {'label': 'Feb', 'value': '02'},
    {'label': 'Mar', 'value': '03'}, {'label': 'Abr', 'value': '04'},
    {'label': 'May', 'value': '05'}, {'label': 'Jun', 'value': '06'},
    {'label': 'Jul', 'value': '07'}, {'label': 'Ago', 'value': '08'},
    {'label': 'Sep', 'value': '09'}, {'label': 'Oct', 'value': '10'},
    {'label': 'Nov', 'value': '11'}, {'label': 'Dic', 'value': '12'},
]
_ANOS_OPTIONS = [{'label': a, 'value': a} for a in ANOS_DISPONIBLES]

_FILTER_DROPDOWN = {'fontSize': '11px', 'color': 'var(--text-primary)'}

# Pre-populate Section and HS Description dropdowns from DICCIONARIO
try:
    _cat_hs = pd.read_excel('data/DICCIONARIO.xlsx', sheet_name='CATEGORIA_HS')
    _cat_hs.columns = _cat_hs.columns.str.strip()
    _cat_hs['Chapter'] = _cat_hs['Chapter'].astype(str).str[:2]
    _SECTION_OPTIONS = [{'label': str(s), 'value': str(s)} for s in sorted(_cat_hs['Section'].dropna().unique())]
    _HS_OPTIONS = [{'label': str(h), 'value': str(h)} for h in sorted(_cat_hs['HS Description'].dropna().unique())]
except Exception:
    _SECTION_OPTIONS = []
    _HS_OPTIONS = []

def _filtro_card(title, children, default_open=True):
    return html.Details([
        html.Summary(title),
        html.Div(children, className='filter-body'),
    ], className='filter-card', open=default_open)

def create_layout(app):
    return html.Div([
        # ── Header (logo + title left, export buttons right) ──
        html.Div(id='header', children=[
            html.Div([
                html.Img(src='/assets/logo.png', style={'height': '70px', 'display': 'inline-block',
                         'verticalAlign': 'middle', 'marginRight': '18px'}),
                html.Div([
                    html.H2("Dashboard de Importaciones", style={'margin': '0', 'color': 'var(--text-primary)',
                             'fontSize': '22px', 'display': 'inline-block'}),
                    html.Span("Análisis de datos de importación Chile",
                              style={'color': 'var(--text-muted)', 'fontSize': '13px', 'display': 'block',
                                     'marginTop': '2px'})
                ], style={'display': 'inline-block', 'verticalAlign': 'middle'}),
            ]),
            html.Div(id='header-toolbar', children=[
                html.Button('☀', id='btn-theme-toggle', n_clicks=0,
                            title='Cambiar tema'),
                html.Button('Exportar CSV', id='btn-export-csv', n_clicks=0,
                            className='btn-export', style={'backgroundColor': 'var(--success)'}),
                html.Button('Exportar Excel', id='btn-export-excel', n_clicks=0,
                            className='btn-export', style={'backgroundColor': 'var(--danger)'}),
                html.Button('Gráficos HTML', id='btn-export-html', n_clicks=0,
                            className='btn-export', style={'backgroundColor': 'var(--info)'}),
                html.Button('Imprimir PDF', id='btn-print', n_clicks=0,
                            className='btn-export', style={'backgroundColor': 'var(--purple)'}),
            ], style={'display': 'flex', 'gap': '8px', 'alignItems': 'center'}),
        ]),

        dcc.Download(id='download-csv'),
        dcc.Download(id='download-html'),
        dcc.Download(id='download-excel'),
        dcc.Store(id='stored-data'),
        dcc.Store(id='selected-years'),
        dcc.Store(id='drill-store'),
        dcc.Store(id='viz-cache'),
        dcc.Store(id='viz-cache-key'),
        dcc.Store(id='sidebar-state', data='expanded'),
        dcc.Store(id='theme-store', data='dark'),

        # ── Drill-down indicator (hidden by default) ──
        html.Div(id='drill-indicator', style={'display': 'none'}),

        # ── Main layout: sidebar + content ──
        html.Div([
            # Sidebar filters
            html.Div(id='sidebar', children=[
                html.Div(id='sidebar-toggle', children='☰',
                         title='Toggle sidebar'),
                html.H3("Filtros", style={'color': 'var(--accent)', 'marginTop': '0',
                         'fontSize': '16px', 'marginBottom': '15px', 'paddingLeft': '14px'}),

                _filtro_card("Años", dcc.Checklist(
                    id='year-checklist',
                    options=[{'label': a, 'value': a} for a in ANOS_DISPONIBLES],
                    value=['2024', '2025', '2026'],
                    inline=False,
                    labelStyle={'color': 'var(--text-secondary)', 'marginRight': '12px',
                                'display': 'block', 'padding': '3px 0'}
                )),

                _filtro_card("Código Arancelario",
                    dcc.Input(id='primary-aranc', type='text',
                              placeholder='Ej: 6210, 3004...',
                              style={'width': '100%', 'padding': '8px', 'borderRadius': '6px',
                                     'border': '1px solid var(--border)', 'backgroundColor': 'var(--bg-primary)',
                                     'color': 'var(--text-secondary)', 'fontSize': '13px'})
                ),

                _filtro_card("Importador (RUT)",
                    dcc.Dropdown(id='primary-importador', options=[],
                                 placeholder='Buscar RUT o nombre...',
                                 style={'fontSize': '12px', 'color': 'var(--text-primary)'})
                ),

                html.Button('Cargar Datos', id='cargar-button', n_clicks=0,
                            className='btn-primary'),
                html.Div(id='carga-status', style={'color': 'var(--text-muted)',
                         'marginTop': '8px', 'fontSize': '12px', 'paddingLeft': '14px'}),

                html.Button('Actualizar Datos', id='btn-ingestar', n_clicks=0,
                            className='btn-primary',
                            style={'backgroundColor': 'var(--info)', 'marginTop': '6px',
                                   'fontSize': '12px', 'padding': '7px'}),
                html.Div(id='ingesta-status', style={'color': 'var(--text-muted)',
                         'marginTop': '6px', 'fontSize': '11px', 'paddingLeft': '14px'}),

                html.Hr(style={'borderColor': 'var(--border)', 'margin': '18px 0'}),
                html.H4("Filtros secundarios", style={'color': 'var(--accent)',
                         'fontSize': '13px', 'marginBottom': '12px', 'paddingLeft': '14px'}),

                _filtro_card("Rango fechas", html.Div([
                    html.Label("Desde:", style={'color': 'var(--text-muted)', 'fontSize': '10px',
                               'marginBottom': '3px', 'display': 'block'}),
                    html.Div([
                        dcc.Dropdown(id='start-day', options=_DIAS, placeholder='Dia',
                                     style={**_FILTER_DROPDOWN, 'flex': '1', 'minWidth': 0}),
                        dcc.Dropdown(id='start-month', options=_MESES, placeholder='Mes',
                                     style={**_FILTER_DROPDOWN, 'flex': '1', 'minWidth': 0}),
                        dcc.Dropdown(id='start-year', options=_ANOS_OPTIONS, placeholder='Año',
                                     style={**_FILTER_DROPDOWN, 'flex': '1', 'minWidth': 0}),
                    ], style={'display': 'flex', 'gap': '3px'}),
                    html.Div(style={'height': '6px'}),
                    html.Label("Hasta:", style={'color': 'var(--text-muted)', 'fontSize': '10px',
                               'marginBottom': '3px', 'display': 'block'}),
                    html.Div([
                        dcc.Dropdown(id='end-day', options=_DIAS, placeholder='Dia',
                                     style={**_FILTER_DROPDOWN, 'flex': '1', 'minWidth': 0}),
                        dcc.Dropdown(id='end-month', options=_MESES, placeholder='Mes',
                                     style={**_FILTER_DROPDOWN, 'flex': '1', 'minWidth': 0}),
                        dcc.Dropdown(id='end-year', options=_ANOS_OPTIONS, placeholder='Año',
                                     style={**_FILTER_DROPDOWN, 'flex': '1', 'minWidth': 0}),
                    ], style={'display': 'flex', 'gap': '3px'}),
                ]), default_open=False),
                _filtro_card("Producto",
                    dcc.Input(id='search-producto', type='text',
                              placeholder='Términos separados por coma', debounce=True,
                              style={'width': '100%', 'padding': '8px', 'borderRadius': '6px',
                                     'border': '1px solid var(--border)', 'backgroundColor': 'var(--bg-primary)',
                                     'color': 'var(--text-secondary)', 'fontSize': '12px'})
                ),
                _filtro_card("Importador",
                    dcc.Input(id='search-importador', type='text',
                              placeholder='Términos separados por coma', debounce=True,
                              style={'width': '100%', 'padding': '8px', 'borderRadius': '6px',
                                     'border': '1px solid var(--border)', 'backgroundColor': 'var(--bg-primary)',
                                     'color': 'var(--text-secondary)', 'fontSize': '12px'})
                ),
                _filtro_card("País origen",
                    dcc.Input(id='search-pa-orig', type='text',
                              placeholder='Términos separados por coma', debounce=True,
                              style={'width': '100%', 'padding': '8px', 'borderRadius': '6px',
                                     'border': '1px solid var(--border)', 'backgroundColor': 'var(--bg-primary)',
                                     'color': 'var(--text-secondary)', 'fontSize': '12px'})
                ),
                _filtro_card("País adquisición",
                    dcc.Input(id='search-pa-adq', type='text',
                              placeholder='Términos separados por coma', debounce=True,
                              style={'width': '100%', 'padding': '8px', 'borderRadius': '6px',
                                     'border': '1px solid var(--border)', 'backgroundColor': 'var(--bg-primary)',
                                     'color': 'var(--text-secondary)', 'fontSize': '12px'})
                ),
                _filtro_card("Comuna",
                    dcc.Input(id='search-comuna', type='text',
                              placeholder='Términos separados por coma', debounce=True,
                              style={'width': '100%', 'padding': '8px', 'borderRadius': '6px',
                                     'border': '1px solid var(--border)', 'backgroundColor': 'var(--bg-primary)',
                                     'color': 'var(--text-secondary)', 'fontSize': '12px'})
                ),
                _filtro_card("Columna para barra %",
                    dcc.Dropdown(
                        id='column-dropdown',
                        options=[{'label': col, 'value': col} for col in
                                 ['NUM_UNICO_IMPORTADOR','PA_ORIG','PA_ADQ','TPO_CARGA','VIA_TRAN','TPO_BUL1','TPO_BUL2']],
                        value='NUM_UNICO_IMPORTADOR',
                        style={'fontSize': '12px', 'color': 'var(--text-primary)'}
                    )
                ),
                _filtro_card("Section (HS)",
                    dcc.Dropdown(id='section-dropdown', options=_SECTION_OPTIONS, multi=True,
                                 placeholder="Selecciona secciones",
                                 style={'fontSize': '12px', 'color': 'var(--text-primary)'})
                ),
                _filtro_card("HS Description",
                    dcc.Dropdown(id='hsdesc-dropdown', options=_HS_OPTIONS, multi=True,
                                 placeholder="Selecciona descripciones",
                                 style={'fontSize': '12px', 'color': 'var(--text-primary)'})
                ),
            ], style={'width': '300px', 'display': 'inline-block',
                      'verticalAlign': 'top', 'marginRight': '25px'}),

            # Content area
            html.Div(id='main-content', children=[
                dcc.Tabs(id='main-tabs', value='Resumen', children=[
                    dcc.Tab(label='Resumen', value='Resumen'),
                    dcc.Tab(label='Paises', value='Paises'),
                    dcc.Tab(label='Productos', value='Productos'),
                    dcc.Tab(label='Transporte y Rutas', value='Transporte y Rutas'),
                    dcc.Tab(label='Geografía', value='Geografía'),
                    dcc.Tab(label='Tablas', value='Tablas'),
                    dcc.Tab(label='Financiero', value='Financiero'),
                    dcc.Tab(label='Clasificación', value='Clasificación'),
                ], style={
                    'backgroundColor': 'var(--bg-secondary)', 'color': 'var(--text-secondary)',
                    'border': '1px solid var(--border)', 'borderBottom': 'none',
                    'fontWeight': 'bold', 'fontSize': '13px'
                }, colors={
                    'border': 'var(--border)',
                    'primary': 'var(--accent)',
                    'background': 'var(--bg-primary)'
                }),
                html.Div(id='output-visualizations'),
                html.Div(id='loading-overlay', className='hidden', children=[
                    html.Div(className='loading-spinner'),
                    html.Div('Cargando\u2026', className='loading-text'),
                ])
            ], style={'width': 'calc(100% - 345px)', 'display': 'inline-block',
                      'verticalAlign': 'top'}),
        ], style={'padding': '0 20px'}),
    ], style={'backgroundColor': 'var(--bg-primary)', 'minHeight': '100vh',
              'fontFamily': '\'Inter\', sans-serif'})
