import duckdb
import os
import glob
import time
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET_PATH = os.path.join(BASE, 'data', 'PARQUET')
DIN_PATH = os.path.join(BASE, 'data', 'descripcion-y-estructura-de-datos.xlsx')

COLUMNAS_DECIMALES = {'CIF_ITEM', 'CANT_MERC', 'FOB', 'FLETE', 'SEGURO', 'CIF',
                      'PRE_UNIT', 'ADVAL_ALA', 'ADVAL', 'VALAD', 'VAL1', 'VAL2', 'VAL3', 'VAL4'}

print("Cargando estructura DIN...")
df_descrip = pd.read_excel(DIN_PATH, sheet_name='DIN', header=1)
col_series = df_descrip['CAMPO - DIN -  ENCABEZADO'].dropna().astype(str).str.strip()
columnas = [c.replace(' ', '') for c in col_series]
ncols_din = len(columnas)
print(f"  {ncols_din} columnas DIN")

# Agrupar archivos por año
archivos_por_año = {}
for año_str in [str(a) for a in range(2017, 2027)]:
    year_path = os.path.join(PARQUET_PATH, año_str)
    if os.path.exists(year_path):
        archivos_por_año[año_str] = sorted(glob.glob(os.path.join(year_path, '*.parquet')))

total_archivos = sum(len(v) for v in archivos_por_año.values())
print(f"Archivos encontrados: {total_archivos}\n")

start_total = time.time()

for año, files in sorted(archivos_por_año.items()):
    if not files:
        continue

    db_path = os.path.join(BASE, 'data', f'importaciones_{año}.db')
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"  [{año}] Base anterior eliminada")

    conn = duckdb.connect(db_path)
    conn.execute("PRAGMA memory_limit='8GB'")
    conn.execute("PRAGMA threads=4")

    # Crear tabla con todas las columnas DIN
    col_defs = []
    for col in columnas:
        tipo = 'DOUBLE' if col in COLUMNAS_DECIMALES else 'VARCHAR'
        col_defs.append(f'"{col}" {tipo}')
    conn.execute(f'CREATE TABLE importaciones ({", ".join(col_defs)})')

    # Crear tabla de tracking
    conn.execute("""
        CREATE TABLE _fuentes (
            archivo VARCHAR PRIMARY KEY,
            mtime DOUBLE,
            filas INTEGER,
            procesado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    año_start = time.time()

    for filepath in files:
        f_abs = os.path.abspath(filepath).replace('\\', '/')
        fname = os.path.basename(filepath)
        f_start = time.time()

        # Obtener nombres de columnas del parquet (basura, mapeamos por posición)
        col_names = conn.execute(
            "SELECT column_name FROM (DESCRIBE SELECT * FROM read_parquet(?))",
            [f_abs]
        ).fetchdf()['column_name'].tolist()

        ncols = min(len(col_names), ncols_din)
        selects = []
        insert_cols = []
        for i in range(ncols):
            din_col = columnas[i]
            raw_name = col_names[i].replace('"', '""')
            ref = f'"{raw_name}"'
            insert_cols.append(f'"{din_col}"')

            if din_col in COLUMNAS_DECIMALES:
                selects.append(
                    f'CAST(REPLACE(CAST({ref} AS VARCHAR), \',\', \'.\') AS DOUBLE) AS "{din_col}"'
                )
            elif din_col == 'DD':
                selects.append(
                    f"CASE WHEN LENGTH(LPAD(CAST({ref} AS VARCHAR), 8, '0')) = 8 "
                    f"AND TRY_CAST(LPAD(CAST({ref} AS VARCHAR), 8, '0') AS INTEGER) IS NOT NULL "
                    f"AND LPAD(CAST({ref} AS VARCHAR), 8, '0') != '00000000' "
                    f"THEN LPAD(CAST({ref} AS VARCHAR), 8, '0') END AS \"{din_col}\""
                )
            else:
                selects.append(f'CAST({ref} AS VARCHAR) AS "{din_col}"')

        path_sql = f_abs.replace("'", "''")
        sql = (
            f'INSERT INTO importaciones ({", ".join(insert_cols)}) '
            f'SELECT {", ".join(selects)} FROM read_parquet(\'{path_sql}\')'
        )
        conn.execute(sql)

        # Obtener mtime y contar filas
        mtime = os.path.getmtime(filepath)
        row_count = conn.execute("SELECT COUNT(*) FROM importaciones").fetchone()[0]

        conn.execute(
            "INSERT OR REPLACE INTO _fuentes (archivo, mtime, filas, procesado) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            [fname, mtime, row_count]
        )

        elapsed = time.time() - f_start
        print(f"  [{año}] {fname} ({elapsed:.1f}s)")

    # Agregar columna ANO y actualizar
    conn.execute("ALTER TABLE importaciones ADD COLUMN ANO INTEGER")
    conn.execute(
        "UPDATE importaciones SET ANO = TRY_CAST(SUBSTR(DD, 5, 4) AS INTEGER) "
        "WHERE DD IS NOT NULL AND LENGTH(DD) = 8"
    )

    # Índices
    for idx_name, col in [
        ('idx_aranc', 'ARANC_NAC'), ('idx_orig', 'PA_ORIG'),
        ('idx_adq', 'PA_ADQ'), ('idx_importador', 'NUM_UNICO_IMPORTADOR'),
        ('idx_dd', 'DD'), ('idx_comuna', 'CODCOMUN'),
        ('idx_via_tran', 'VIA_TRAN'), ('idx_adu', 'ADU'), ('idx_ano', 'ANO'),
    ]:
        try:
            conn.execute(f'CREATE INDEX {idx_name} ON importaciones ("{col}")')
        except Exception:
            pass

    conn.execute("ANALYZE")

    total_rows = conn.execute("SELECT COUNT(*) FROM importaciones").fetchone()[0]
    año_elapsed = time.time() - año_start
    db_size = os.path.getsize(db_path) / 1024 / 1024
    print(f"  [{año}] -> {total_rows:,} filas, {db_size:.0f} MB ({año_elapsed:.0f}s)")
    conn.close()

total = time.time() - start_total
print(f"\nOK ETL completado en {total:.0f}s ({total/60:.1f}min)")
