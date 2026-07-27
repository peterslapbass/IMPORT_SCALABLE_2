"""Tests para funciones de callbacks.py (sin dependencia de DuckDB/parquet)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from callbacks import (
    _build_filter_sql, _empty_fig, _error_fig,
    _gen_indicadores, _apply_section_hs_filter,
    _card, _data_table, _loading_graph,
    _cif_expr, _cant_expr, _product_expr,
)


# ── _build_filter_sql ──

def test_build_filter_sql_empty():
    assert _build_filter_sql(None, None, None, None, None, None, None, None, None) == []

def test_build_filter_sql_aranc():
    result = _build_filter_sql('6210', None, None, None, None, None, None, None, None)
    assert len(result) == 1
    assert 'ARANC_NAC' in result[0]
    assert '6210' in result[0]

def test_build_filter_sql_importador():
    result = _build_filter_sql(None, '9447', None, None, None, None, None, None, None)
    assert len(result) == 1
    assert 'NUM_UNICO_IMPORTADOR' in result[0]
    assert '9447' in result[0]

def test_build_filter_sql_dates():
    result = _build_filter_sql(None, None, '2024-01-01', '2024-12-31', None, None, None, None, None)
    assert len(result) == 1
    assert 'STRPTIME' in result[0]
    assert '2024-01-01' in result[0]

def test_build_filter_sql_producto():
    result = _build_filter_sql(None, None, None, None, 'manzana', None, None, None, None)
    assert len(result) == 1
    assert 'DNOMBRE' in result[0]
    assert 'manzana' in result[0]

def test_build_filter_sql_multi_term():
    result = _build_filter_sql('6210,3004', None, None, None, None, None, None, None, None)
    assert len(result) == 1
    assert '6210' in result[0]
    assert '3004' in result[0]

def test_build_filter_sql_pais_origen():
    result = _build_filter_sql(None, None, None, None, None, None, 'CN', None, None)
    assert len(result) == 1
    assert 'PA_ORIG' in result[0]

def test_build_filter_sql_pais_adq():
    result = _build_filter_sql(None, None, None, None, None, None, None, 'US', None)
    assert len(result) == 1
    assert 'PA_ADQ' in result[0]

def test_build_filter_sql_comuna():
    result = _build_filter_sql(None, None, None, None, None, None, None, None, 'Santiago')
    assert len(result) == 1
    assert 'CODCOMUN' in result[0]

def test_build_filter_sql_combined():
    result = _build_filter_sql('6210', '9447', '2024-01-01', '2024-12-31',
                                'manzana', 'IMPORTADOR', 'CN', 'US', 'Santiago')
    assert len(result) == 8  # aranc + primary_importador + dates + producto + search_importador + pa_orig + pa_adq + comuna


# ── _empty_fig / _error_fig ──

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
    # Should return a Div with title and content
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
    # Should return a DataTable with columns from the DataFrame
    assert hasattr(table, 'columns')
    col_names = [c['name'] for c in table.columns]
    assert 'A' in col_names
    assert 'B' in col_names


# ── Constants ──

def test_cif_expr():
    assert 'CIF_ITEM' in _cif_expr
    assert 'REPLACE' in _cif_expr
    assert 'DOUBLE' in _cif_expr

def test_cant_expr():
    assert 'CANT_MERC' in _cant_expr
    assert 'REPLACE' in _cant_expr

def test_product_expr():
    assert 'DNOMBRE' in _product_expr
    assert 'DMARCA' in _product_expr
    assert 'DVARIEDAD' in _product_expr
    assert 'CONCAT' in _product_expr


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
