"""
Exporta las tablas relevantes de la base SQLite del SII a formato parquet (DuckDB nativo).
Se ejecuta una sola vez. Reduce 1.1 GB → ~150 MB y acelera consultas 4x.
"""
import os
import duckdb

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(BASE, 'data', 'datos_empresariales.db')
SII_DIR = os.path.join(BASE, 'data', 'sii')

os.makedirs(SII_DIR, exist_ok=True)

con = duckdb.connect()
con.execute('INSTALL sqlite; LOAD sqlite')
con.execute(f"ATTACH '{SQLITE_PATH}' AS sii (TYPE SQLITE)")

tables = {
    'pj.parquet':        'SELECT RUT, DV, RAZON_SOCIAL FROM sii.pub_nombres_pj',
    'actecos.parquet':   'SELECT RUT, DV, DESC_ACTIVIDAD_ECONOMICA FROM sii.pub_nom_actecos',
    'domicilio.parquet': 'SELECT RUT, DV, COMUNA, CALLE, NUMERO, CIUDAD FROM sii.pub_nom_domicilio WHERE VIGENCIA=\'S\'',
}

for fname, sql in tables.items():
    path = os.path.join(SII_DIR, fname)
    print(f'Exportando {fname}...')
    con.execute(f"COPY ({sql}) TO '{path}' (FORMAT PARQUET)")
    size = os.path.getsize(path)
    cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{path}')").fetchone()[0]
    print(f'  {cnt:,} filas, {size/1024/1024:.1f} MB')

con.close()
print(f'\nExportación completa. Archivos en: {SII_DIR}')
