"""Tests para funciones puras de callbacks.py (sin dependencia de DuckDB/parquet)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from callbacks import (
    _build_filter_sql, _empty_fig, _error_fig, _pending_fig,
    _gen_indicadores, _apply_section_hs_filter, _apply_plotly_theme,
    _card, _data_table, _loading_graph,
    _cif_expr, _cant_expr, _product_expr,
    _filter_key, _run_key, _share_results, _deep_val,
)


EMPTY13 = (None,) * 13


def _f(*args):
    assert len(args) <= 13
    return _build_filter_sql(*args, *( (None,) * (13 - len(args)) ))


# ── _build_filter_sql (firma actual: 13 args) ──

def test_build_filter_sql_empty():
    assert _build_filter_sql(*EMPTY13) == []

def test_build_filter_sql_aranc():
    result = _f('6210')
    assert len(result) == 1
    assert 'ARANC_NAC' in result[0]
    assert '6210' in result[0]

def test_build_filter_sql_importador():
    result = _f(None, '9447')
    assert len(result) == 1
    assert 'NUM_UNICO_IMPORTADOR' in result[0]
    assert '9447' in result[0]

def test_build_filter_sql_dates():
    result = _build_filter_sql(None, None, '01', '01', '2024',
                               '31', '12', '2024',
                               None, None, None, None, None)
    assert len(result) == 1
    assert 'TRY_STRPTIME' in result[0]
    assert '2024-01-01' in result[0]
    assert '2024-12-31' in result[0]

def test_build_filter_sql_dates_incomplete():
    result = _build_filter_sql(None, None, '01', None, '2024',
                               None, None, None,
                               None, None, None, None, None)
    assert result == []

def test_build_filter_sql_producto():
    result = _f(None, None, None, None, None, None, None, None, 'manzana')
    assert len(result) == 1
    assert 'DNOMBRE' in result[0]
    assert 'manzana' in result[0]

def test_build_filter_sql_multi_term():
    result = _f('6210,3004')
    assert len(result) == 1
    assert '6210' in result[0]
    assert '3004' in result[0]

def test_build_filter_sql_pais_origen():
    result = _build_filter_sql(None, None, None, None, None, None, None, None,
                               None, None, 'CN', None, None)
    assert len(result) == 1
    assert 'PA_ORIG' in result[0]

def test_build_filter_sql_pais_adq():
    result = _build_filter_sql(None, None, None, None, None, None, None, None,
                               None, None, None, 'US', None)
    assert len(result) == 1
    assert 'PA_ADQ' in result[0]

def test_build_filter_sql_comuna():
    result = _build_filter_sql(None, None, None, None, None, None, None, None,
                               None, None, None, None, 'Santiago')
    assert len(result) == 1
    assert 'CODCOMUN' in result[0]

def test_build_filter_sql_combined():
    result = _build_filter_sql('6210', '9447', '01', '01', '2024',
                               '31', '12', '2024',
                               'manzana', 'IMPORTADOR', 'CN', 'US', 'Santiago')
    assert len(result) == 8  # aranc + primary_importador + dates + producto + search_importador + pa_orig + pa_adq + comuna


# ── _empty_fig / _error_fig / _pending_fig ──

def test_empty_fig():
    fig = _empty_fig()
    assert fig is not None
    assert len(fig.data) == 0
    assert len(fig.layout.annotations) == 1
    assert 'Sin datos' in fig.layout.annotations[0].text

def test_error_fig():
    fig = _error_fig(Exception("test error"))
    assert fig is not None
    assert 'test error' in fig.layout.annotations[0].text

def test_pending_fig():
    fig = _pending_fig()
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0
    assert 'Calculando' in fig.layout.annotations[0].text


# ── _gen_indicadores ──

def test_gen_indicadores_empty():
    cif, kg, precio = _gen_indicadores(pd.DataFrame())
    assert cif == 0
    assert kg == 0
    assert precio == 0

def test_gen_indicadores_normal():
    df = pd.DataFrame({'CIF_ITEM': [1000, 2000], 'CANT_MERC': [100, 200]})
    cif, kg, precio = _gen_indicadores(df)
    assert cif == 3000
    assert kg == 300
    assert precio == 10.0

def test_gen_indicadores_zero_kg():
    df = pd.DataFrame({'CIF_ITEM': [1000], 'CANT_MERC': [0]})
    cif, kg, precio = _gen_indicadores(df)
    assert cif == 1000
    assert kg == 0
    assert precio == 0


# ── UI Helpers ──

def test_card_structure():
    card = _card("Test Title", "Test content")
    children = card.children if hasattr(card, 'children') else []
    assert len(children) == 2

def test_data_table_empty():
    result = _data_table(pd.DataFrame())
    assert 'Sin datos' in result.children if hasattr(result, 'children') else True

def test_data_table_none():
    result = _data_table(None)
    assert 'Sin datos' in result.children if hasattr(result, 'children') else True

def test_data_table_with_data():
    df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    table = _data_table(df)
    assert hasattr(table, 'columns')
    col_names = [c['name'] for c in table.columns]
    assert 'A' in col_names
    assert 'B' in col_names

def test_apply_plotly_theme_transparent():
    fig = _apply_plotly_theme(go.Figure())
    assert fig.layout.paper_bgcolor == 'rgba(0,0,0,0)'
    assert fig.layout.plot_bgcolor == 'rgba(0,0,0,0)'


# ── Constants (columnas ya DOUBLE en DuckDB) ──

def test_cif_expr():
    assert 'CIF_ITEM' in _cif_expr

def test_cant_expr():
    assert 'CANT_MERC' in _cant_expr

def test_product_expr():
    assert 'DNOMBRE' in _product_expr
    assert 'DMARCA' in _product_expr
    assert 'DVARIEDAD' in _product_expr
    assert 'CONCAT' in _product_expr


# ── Caché / single-flight (puros, sin DuckDB) ──

def _key_args(**over):
    base = dict(selected_years=['2026'], primary_aranc=None, primary_importador=None,
                start_day=None, start_month=None, start_year=None,
                end_day=None, end_month=None, end_year=None,
                search_producto=None, search_importador=None,
                search_pa_orig=None, search_pa_adq=None, search_comuna=None,
                column_dropdown='NUM_UNICO_IMPORTADOR',
                section_value=None, hsdesc_value=None, drill_data=None)
    base.update(over)
    return base

def test_filter_key_deterministic():
    assert _filter_key(**_key_args()) == _filter_key(**_key_args())

def test_filter_key_changes_with_filters():
    assert _filter_key(**_key_args()) != _filter_key(**_key_args(search_pa_orig='CN'))

def test_filter_key_format():
    key = _filter_key(**_key_args())
    assert len(key) == 32
    assert all(c in '0123456789abcdef' for c in key)

def test_run_key_stable_to_gen_order():
    a = _run_key(['2026'], 'w', ['f'], 'col', ['b', 'a'])
    b = _run_key(['2026'], 'w', ['f'], 'col', ['a', 'b'])
    assert a == b

def test_run_key_changes_with_filters():
    a = _run_key(['2026'], 'w1', [], 'col', ['a'])
    b = _run_key(['2026'], 'w2', [], 'col', ['a'])
    assert a != b

def test_share_results_copies_frames_and_figs():
    df = pd.DataFrame({'A': [1, 2]})
    fig = go.Figure()
    results = {'t': (fig, df), 'n': 5}
    shared = _share_results(results)
    assert shared is not results
    assert shared['t'][1] is not df
    assert shared['t'][1].equals(df)
    assert shared['t'][0] is not fig
    assert isinstance(shared['t'][0], go.Figure)
    assert shared['n'] == 5

def test_deep_val_passthrough():
    assert _deep_val(0) == 0
    assert _deep_val(None) is None
    assert _deep_val('x') == 'x'


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
