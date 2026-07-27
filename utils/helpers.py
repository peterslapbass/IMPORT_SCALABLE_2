import pandas as pd
import unicodedata
import os
import glob
import duckdb
import threading


DESCRIPCION_PATH = os.path.join('data', 'descripcion-y-estructura-de-datos.xlsx')
DESCRIPCION_SHEET = 'DIN'

_DB_BASE = os.path.join('data', 'importaciones_{}.db')

COLUMNAS_DECIMALES = {'CIF_ITEM', 'CANT_MERC', 'FOB', 'FLETE', 'SEGURO', 'CIF',
                      'PRE_UNIT', 'ADVAL_ALA', 'ADVAL', 'VALAD', 'VAL1', 'VAL2', 'VAL3', 'VAL4'}

COLUMNAS_INDICES = ['DD', 'ARANC_NAC', 'Section', 'HS Description', 'PA_ORIG', 'PA_ADQ',
                    'NUM_UNICO_IMPORTADOR', 'CIF_ITEM', 'CANT_MERC', 'PRODUCTO', 'VIA_TRAN',
                    'TPO_CARGA', 'TOT_BULTOS', 'CODCOMUN', 'ADU', 'PTO_DESEM', 'PTO_EMB',
                    'DESOBS1', 'TPO_DOCTO', 'DNOMBRE', 'DMARCA', 'DVARIEDAD', 'DOTRO1', 'DOTRO2',
                    'ATR_5', 'ATR_6', 'MEDIDA', 'TPO_BUL1', 'CANT_BUL1', 'TPO_BUL2', 'CANT_BUL2',
                    'NUM_UNICO_IMPORTADOR_ORIGINAL']

_COLUMNAS_CACHE = None
_DICT_CACHE = None
_DICT_MTIME = 0
_PARQUET_CACHE = {}


def listar_archivos_parquet(años):
    key = tuple(sorted(str(a) for a in años))
    if key in _PARQUET_CACHE:
        return _PARQUET_CACHE[key]
    archivos = []
    for año in años:
        año = str(año)
        pattern = os.path.join('data', 'PARQUET', año, '*.parquet')
        for f in sorted(glob.glob(pattern)):
            archivos.append((año, f))
    _PARQUET_CACHE[key] = archivos
    return archivos


def cargar_descripcion_estructura():
    global _COLUMNAS_CACHE
    if _COLUMNAS_CACHE is not None:
        return _COLUMNAS_CACHE
    df_descrip = pd.read_excel(DESCRIPCION_PATH, sheet_name=DESCRIPCION_SHEET, header=1)
    if 'CAMPO - DIN -  ENCABEZADO' not in df_descrip.columns:
        raise ValueError("No se encontró la columna 'CAMPO - DIN -  ENCABEZADO' en el diccionario.")
    columnas = (
        df_descrip['CAMPO - DIN -  ENCABEZADO']
        .dropna().astype(str).str.strip().str.replace(' ', '').tolist()
    )
    _COLUMNAS_CACHE = columnas
    return columnas


def _db_path(año):
    return _DB_BASE.format(año)


def _db_exists(año):
    return os.path.exists(_db_path(año))


def _attach_years(conn, años):
    for año in años:
        alias = f'y{año}'
        db = os.path.abspath(_db_path(año)).replace('\\', '/')
        if os.path.exists(_db_path(año)):
            try:
                conn.execute(f"ATTACH '{db}' AS {alias} (READ_ONLY)")
            except Exception:
                pass

    parts = [f"SELECT * FROM y{año}.importaciones" for año in años if _db_exists(año)]
    if parts:
        conn.execute(f"CREATE OR REPLACE TEMP VIEW todas AS {' UNION ALL BY NAME '.join(parts)}")


def _create_conn(años=None):
    conn = duckdb.connect()
    conn.execute("PRAGMA memory_limit='8GB'")
    conn.execute("PRAGMA threads=4")
    if años:
        _attach_years(conn, años)
    return conn


def query_parquet(selects, where_clause=None, group_by=None, order_by=None, limit=None, conn=None, años=None):
    own_conn = conn is None
    if own_conn:
        if not años:
            return pd.DataFrame()
        conn = _create_conn(años)
    try:
        sql = f"SELECT {selects} FROM todas"
        if where_clause:
            sql += f" WHERE {where_clause}"
        if group_by:
            sql += f" GROUP BY {group_by}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"
        return conn.execute(sql).fetchdf()
    finally:
        if own_conn:
            conn.close()


def query_aggregated(metric_col, group_cols, filters=None, extra_selects=None, conn=None, años=None):
    extra_aliases = set(extra_selects.keys()) if extra_selects else set()
    selects = []
    for g in group_cols:
        if g in extra_aliases:
            selects.append(f'{extra_selects[g]} AS "{g}"')
        else:
            selects.append(f'CAST("{g}" AS VARCHAR) AS "{g}"')

    selects.append(f'SUM("{metric_col}") AS "{metric_col}"')

    if extra_selects:
        for alias, expr in extra_selects.items():
            if alias not in group_cols:
                selects.append(f'{expr} AS "{alias}"')

    select_str = ', '.join(selects)
    where_parts = []
    if filters:
        where_parts.extend(filters)
    where_parts.append(f'"{metric_col}" IS NOT NULL')

    where_str = ' AND '.join(where_parts) if where_parts else None
    group_parts = []
    for g in group_cols:
        if g in extra_aliases:
            group_parts.append(extra_selects[g])
        else:
            group_parts.append(f'"{g}"')
    group_str = ', '.join(group_parts) if group_parts else None

    return query_parquet(select_str, where_clause=where_str, group_by=group_str, conn=conn, años=años)


def query_raw(columns=None, filters=None, limit=None, conn=None, años=None):
    if columns is None:
        columns = cargar_descripcion_estructura()
    selects = [f'"{col}"' for col in columns]
    select_str = ', '.join(selects)
    where_str = ' AND '.join(filters) if filters else None
    return query_parquet(select_str, where_clause=where_str, limit=limit, conn=conn, años=años)


def query_count(años, filters=None):
    conn = _create_conn(años)
    try:
        sql = "SELECT COUNT(*) AS total FROM todas"
        if filters:
            sql += f" WHERE {' AND '.join(filters)}"
        return conn.execute(sql).fetchone()[0]
    finally:
        conn.close()


def obtener_metadata_parquet(años):
    conn = get_global_conn(años)
    min_date = conn.execute(
        "SELECT MIN(STRPTIME(DD, '%d%m%Y')) FROM todas "
        "WHERE DD IS NOT NULL AND LENGTH(DD)=8 AND TRY_STRPTIME(DD, '%d%m%Y') IS NOT NULL"
    ).fetchone()[0]
    max_date = conn.execute(
        "SELECT MAX(STRPTIME(DD, '%d%m%Y')) FROM todas "
        "WHERE DD IS NOT NULL AND LENGTH(DD)=8 AND TRY_STRPTIME(DD, '%d%m%Y') IS NOT NULL"
    ).fetchone()[0]

    chapters = conn.execute(
        "SELECT DISTINCT SUBSTR(ARANC_NAC, 1, 2) AS ch FROM todas WHERE ARANC_NAC IS NOT NULL"
    ).fetchdf()['ch'].dropna().tolist()

    df_dict = cargar_diccionarios_categoria_hs()
    merged = pd.DataFrame({'Chapter': chapters}).merge(
        df_dict[['Chapter', 'HS Description', 'Section']].drop_duplicates(),
        on='Chapter', how='left'
    )
    sections = sorted(merged['Section'].dropna().unique().tolist())
    hs_descs = sorted(merged['HS Description'].dropna().unique().tolist())

    return {
        'min_date': str(min_date)[:10] if min_date else None,
        'max_date': str(max_date)[:10] if max_date else None,
        'sections': sections,
        'hs_descriptions': hs_descs
    }


def enriquecer_desde_diccionarios(df, columnas_a_enriquecer):
    dicts = cargar_diccionarios()
    mapeos = {
        'PA_ORIG': dicts['PAIS'],
        'PA_ADQ': dicts['PAIS'],
        'VIA_TRAN': dicts['TRANSPORTE'],
        'TPO_CARGA': dicts['CARGA'],
        'CODCOMUN': dicts['COMUNA'],
        'ADU': dicts['ADUANA'],
        'PTO_DESEM': dicts['PUERTOS'],
        'PTO_EMB': dicts['PUERTOS'],
        'TPO_DOCTO': dicts['OPERACION'],
        'TPO_BUL1': dicts['BULTO'],
        'TPO_BUL2': dicts['BULTO'],
        'MONEDA': dicts['MONEDAS'],
        'FORM_PAGO': dicts['FORMAS_PAGOS'],
        'REG_IMP': dicts['REGIMEN_IMPORTACION'],
        'MEDIDA': dicts['UNIDAD_MEDIDA'],
        'BCO_COM': dicts['BANCOS_COMERCIALES'],
        'CL_COMPRA': dicts['CLAUSULA_COMPRA_VENTA'],
        'CODORDIV': dicts['ORIGEN_DIVISAS'],
        'CODVISBUEN': dicts['VISTOS_BUENOS'],
        'PAGO_GRAV': dicts['FORMAS_PAGO_GRAVAMEN'],
    }
    for col in columnas_a_enriquecer:
        if col in df.columns and col in mapeos:
            mapping = mapeos[col]
            vals = df[col].astype(str).str.strip()
            if col == 'CODCOMUN':
                mapped = vals.map(mapping).fillna(vals.str.zfill(5).map(mapping))
            else:
                mapped = vals.map(mapping)
            df.loc[:, col] = mapped.fillna(vals)
    return df


def leer_txt_sin_encabezado(filepath, delimiter=';', decimal=','):
    columnas = cargar_descripcion_estructura()
    ext = filepath.lower().split('.')[-1]
    if ext == 'parquet':
        df = pd.read_parquet(filepath)
        columnas_asignar = columnas[:len(df.columns)]
        df.columns = columnas_asignar
        return df
    else:
        df = pd.read_csv(
            filepath, header=None, names=columnas,
            delimiter=delimiter, encoding='latin1',
            decimal=decimal, on_bad_lines='skip', low_memory=False
        )
        return df


DICCIONARIO_PATH = os.path.join('data', 'DICCIONARIO.xlsx')

def cargar_diccionarios():
    global _DICT_CACHE, _DICT_MTIME
    mtime = os.path.getmtime(DICCIONARIO_PATH)
    if _DICT_CACHE is not None and mtime == _DICT_MTIME:
        return _DICT_CACHE
    def _load_dict(sheet_name):
        df = pd.read_excel(DICCIONARIO_PATH, sheet_name=sheet_name)
        return {str(k).strip(): v for k, v in df.set_index('Código')['Glosa'].to_dict().items()}
    _DICT_CACHE = {
        'PAIS': _load_dict('PAIS'),
        'BULTO': _load_dict('BULTO'),
        'CARGA': _load_dict('CARGA'),
        'TRANSPORTE': _load_dict('TRANSPORTE'),
        'COMUNA': _load_dict('COMUNA'),
        'ADUANA': _load_dict('ADUANA'),
        'PUERTOS': _load_dict('PUERTOS'),
        'OPERACION': _load_dict('OPERACION'),
        'MONEDAS': _load_dict('MONEDAS'),
        'FORMAS_PAGOS': _load_dict('FORMAS_PAGOS'),
        'REGIMEN_IMPORTACION': _load_dict('REGIMEN_IMPORTACION'),
        'UNIDAD_MEDIDA': _load_dict('UNIDAD_MEDIDA'),
        'BANCOS_COMERCIALES': _load_dict('BANCOS_COMERCIALES'),
        'CLAUSULA_COMPRA_VENTA': _load_dict('CLAUSULA_COMPRA_VENTA'),
        'ORIGEN_DIVISAS': _load_dict('ORIGEN_DIVISAS'),
        'VISTOS_BUENOS': _load_dict('VISTOS_BUENOS'),
        'REGIONES': _load_dict('REGIONES'),
        'TIPOS_CUENTAS': _load_dict('TIPOS_CUENTAS'),
        'FORMAS_PAGO_GRAVAMEN': _load_dict('FORMAS_PAGO_GRAVAMEN'),
        'ARTICULOS_DENUNCIAS': _load_dict('ARTICULOS_DENUNCIAS'),
        'CLAVES_ECONOMICAS_IMPORTA': _load_dict('CLAVES_ECONOMICAS_IMPORTA'),
        'ZONAS_ECONOMICAS': _load_dict('ZONAS_ECONOMICAS'),
        'CLAVES_ECONOMICAS_EXPORTAC': _load_dict('CLAVES_ECONOMICAS_EXPORTAC'),
    }
    _DICT_MTIME = mtime
    return _DICT_CACHE


_CATEGORIA_HS_CACHE = None
_CATEGORIA_HS_MTIME = 0

def cargar_diccionarios_categoria_hs():
    global _CATEGORIA_HS_CACHE, _CATEGORIA_HS_MTIME
    mtime = os.path.getmtime(DICCIONARIO_PATH)
    if _CATEGORIA_HS_CACHE is not None and mtime == _CATEGORIA_HS_MTIME:
        return _CATEGORIA_HS_CACHE
    df = pd.read_excel(DICCIONARIO_PATH, sheet_name='CATEGORIA_HS')
    df.columns = df.columns.str.strip()
    df['Chapter'] = df['Chapter'].astype(str).str[:2]
    _CATEGORIA_HS_CACHE = df
    _CATEGORIA_HS_MTIME = mtime
    return df


hs_industries = {
    '3004': 'Farmacéutica', '2710': 'Petroquímica',
    '3901': 'Plásticos', '3902': 'Plásticos', '3903': 'Plásticos', '3904': 'Plásticos',
    '3907': 'Resinas', '3908': 'Resinas', '3910': 'Resinas', '3911': 'Resinas',
    '3824': 'Aditivos para Plásticos', '3407': 'Aditivos para Plásticos',
    '3808': 'Químicos - Agroquímicos/Desinfectantes',
    '3304': 'Químicos - Industria Cosmética',
    '2830': 'Minería', '2815': 'Minería', '2707': 'Minería',
    '7201': 'Fundición', '7202': 'Fundición', '8111': 'Fundición',
    '2827': 'Tratamiento de Aguas', '2833': 'Tratamiento de Aguas', '2828': 'Tratamiento de Aguas',
    '4801': 'Industria del Papel', '4802': 'Industria del Papel', '4810': 'Industria del Papel',
    '4707': 'Industria del Papel', '3809': 'Industria del Papel - Aditivos'
}

def asignar_industria(codigo_hs):
    codigo_hs = str(codigo_hs)[:4]
    return hs_industries.get(codigo_hs, 'Industria Desconocida')

def eliminar_acentos(texto):
    if isinstance(texto, str):
        texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto

import_df = pd.read_csv(os.path.join('data', 'import.txt'), sep='\t', encoding='utf-8')
import_df['RUT'] = import_df['RUT'].astype(str).str.strip()
import_dict = dict(zip(import_df['RUT'], import_df['RAZON_SOCIAL']))
import_ruts_set = set(import_df['RUT'].values)

def obtener_importadores_coincidentes(df_data):
    if 'NUM_UNICO_IMPORTADOR_ORIGINAL' not in df_data.columns:
        return pd.DataFrame(columns=['RUT_ORIGINAL', 'NOMBRE_REEMPLAZADO'])
    ruts_originales = df_data['NUM_UNICO_IMPORTADOR_ORIGINAL'].astype(str).str.strip().unique()
    coincidencias = [rut for rut in ruts_originales if rut in import_ruts_set]
    if not coincidencias:
        def normalizar_rut(valor):
            valor = str(valor).strip().upper()
            valor = valor.replace('.', '').replace('-', '').replace(' ', '')
            return valor
        import_ruts_norm_set = {normalizar_rut(rut) for rut in import_ruts_set}
        coincidencias = [
            rut for rut in ruts_originales 
            if normalizar_rut(rut) in import_ruts_norm_set
        ]
    mapeo_rut_nombre = dict(zip(
        df_data['NUM_UNICO_IMPORTADOR_ORIGINAL'].astype(str).str.strip(), 
        df_data['NUM_UNICO_IMPORTADOR'].astype(str)
    ))
    resultados = []
    for rut in coincidencias:
        nombre_reemplazado = mapeo_rut_nombre.get(rut, rut)
        resultados.append({'RUT_ORIGINAL': rut, 'NOMBRE_REEMPLAZADO': nombre_reemplazado})
    resultado = pd.DataFrame(resultados) if resultados else pd.DataFrame(columns=['RUT_ORIGINAL', 'NOMBRE_REEMPLAZADO'])
    return resultado.drop_duplicates().sort_values('NOMBRE_REEMPLAZADO').reset_index(drop=True)

comunas_df = pd.read_csv(os.path.join('data', 'comunas.csv'))
puertos_coords = pd.read_csv(os.path.join('data', 'puertos_coordenadas.csv'))

def enriquecer_dataframe(df, dicts):
    mapeos = {
        'PA_ORIG': dicts['PAIS'], 'PA_ADQ': dicts['PAIS'],
        'VIA_TRAN': dicts['TRANSPORTE'], 'TPO_CARGA': dicts['CARGA'],
        'ID_BULTOS': dicts['BULTO'], 'CODCOMUN': dicts['COMUNA'],
        'ADU': dicts['ADUANA'], 'PTO_DESEM': dicts['PUERTOS'],
        'PTO_EMB': dicts['PUERTOS'], 'TPO_DOCTO': dicts['OPERACION']
    }
    for col, mapping in mapeos.items():
        if col in df.columns:
            df[col] = df[col].map(mapping)
    for i in range(1, 9):
        col = f'TPO_BUL{i}'
        if col in df.columns:
            df[col] = df[col].map(dicts['BULTO'])
    return df

def buscar_codigo_diccionario(nombre_diccionario, texto):
    if not texto:
        return []
    texto = eliminar_acentos(str(texto)).lower().strip()
    diccionarios = cargar_diccionarios()
    if nombre_diccionario not in diccionarios:
        return []
    resultados = []
    for codigo, descripcion in diccionarios[nombre_diccionario].items():
        descripcion = eliminar_acentos(str(descripcion)).lower()
        if texto in descripcion:
            resultados.append(str(codigo))
    return resultados

def buscar_codigos_columna(columna, texto):
    mapa = {
        "PA_ORIG": "PAIS",
        "PA_ADQ": "PAIS",
        "CODCOMUN": "COMUNA",
        "VIA_TRAN": "TRANSPORTE",
        "TPO_CARGA": "CARGA",
        "ADU": "ADUANA",
        "PTO_DESEM": "PUERTOS",
        "PTO_EMB": "PUERTOS",
        "TPO_DOCTO": "OPERACION",
        "TPO_BUL1": "BULTO",
        "TPO_BUL2": "BULTO",
        "MEDIDA": "UNIDAD_MEDIDA",
    }
    if columna not in mapa:
        return []
    return buscar_codigo_diccionario(mapa[columna], texto)


_GLOBAL_CONN = None
_GLOBAL_CONN_AÑOS = None
_GLOBAL_CONN_LOCK = threading.Lock()


def get_global_conn(años=None):
    global _GLOBAL_CONN, _GLOBAL_CONN_AÑOS
    with _GLOBAL_CONN_LOCK:
        años_key = tuple(sorted(str(a) for a in años)) if años else ()
        if _GLOBAL_CONN is not None and _GLOBAL_CONN_AÑOS == años_key:
            try:
                _GLOBAL_CONN.execute("SELECT 1")
                return _GLOBAL_CONN
            except Exception:
                pass
        if _GLOBAL_CONN is not None:
            try:
                _GLOBAL_CONN.close()
            except Exception:
                pass
        _GLOBAL_CONN = _create_conn(años)
        _GLOBAL_CONN_AÑOS = años_key
        return _GLOBAL_CONN


def reset_global_conn():
    global _GLOBAL_CONN, _GLOBAL_CONN_AÑOS
    with _GLOBAL_CONN_LOCK:
        if _GLOBAL_CONN is not None:
            try:
                _GLOBAL_CONN.close()
            except Exception:
                pass
            _GLOBAL_CONN = None
            _GLOBAL_CONN_AÑOS = None
