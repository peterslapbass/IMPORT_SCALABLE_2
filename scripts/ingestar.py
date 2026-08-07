"""
Ingesta incremental: agrega archivos parquet nuevos a las DBs por año.
Uso:
  python scripts/ingestar.py              # todo los años
  python scripts/ingestar.py --año 2026    # solo 2026
  python scripts/ingestar.py --check      # solo mostrar qué falta
"""
import duckdb, os, glob, time, argparse, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET_PATH = os.path.join(BASE, 'data', 'PARQUET')
sys.path.insert(0, BASE)
os.chdir(BASE)

from utils.helpers import cargar_descripcion_estructura, COLUMNAS_DECIMALES, _db_path, _db_exists

columnas = cargar_descripcion_estructura()
ncols_din = len(columnas)


def procesar_año(año, check_only=False):
    year_path = os.path.join(PARQUET_PATH, str(año))
    if not os.path.exists(year_path):
        print(f'  No hay carpeta PARQUET/{año}')
        return 0, 0

    files = sorted(glob.glob(os.path.join(year_path, '*.parquet')))
    if not files:
        print(f'  No hay archivos .parquet en PARQUET/{año}')
        return 0, 0

    db = _db_path(año)
    crear_db = not _db_exists(año)

    if crear_db:
        if check_only:
            print(f'  [{año}] Base no existe (se creará con {len(files)} archivos)')
            return len(files), 0
        print(f'  [{año}] Creando base nueva...')
        conn = duckdb.connect(db)
        conn.execute("PRAGMA memory_limit='8GB'")
        conn.execute("PRAGMA threads=4")
        col_defs = [f'"{c}" DOUBLE' if c in COLUMNAS_DECIMALES else f'"{c}" VARCHAR' for c in columnas]
        conn.execute(f'CREATE TABLE importaciones ({", ".join(col_defs)})')
        conn.execute("""
            CREATE TABLE _fuentes (
                archivo VARCHAR PRIMARY KEY, mtime DOUBLE,
                filas INTEGER, procesado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        conn = duckdb.connect(db)
        conn.execute("PRAGMA memory_limit='8GB'")
        conn.execute("PRAGMA threads=4")
        procesados = set(conn.execute("SELECT archivo FROM _fuentes").fetchdf()['archivo'])

    nuevos = 0
    omitidos = 0

    for fpath in files:
        fname = os.path.basename(fpath)
        mtime = os.path.getmtime(fpath)

        if not crear_db:
            row = conn.execute(
                "SELECT mtime FROM _fuentes WHERE archivo=?", [fname]
            ).fetchone()
            if row and row[0] >= mtime:
                omitidos += 1
                continue

        if check_only:
            if not crear_db and (not row or row[0] < mtime):
                print(f'    {fname} (desactualizado)')
            continue

        f_abs = os.path.abspath(fpath).replace('\\', '/')
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
                selects.append(f"CAST(REPLACE(CAST({ref} AS VARCHAR), ',', '.') AS DOUBLE) AS \"{din_col}\"")
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

        if not crear_db and 'DD' in columnas:
            dd_idx = columnas.index('DD')
            if dd_idx < len(col_names):
                dd_raw = col_names[dd_idx].replace('"', '""')
                dd_expr = f'LPAD(CAST("{dd_raw}" AS VARCHAR), 8, \'0\')'
                conn.execute(f"""
                    DELETE FROM importaciones WHERE DD IN (
                        SELECT CASE WHEN LENGTH({dd_expr}) = 8
                             AND TRY_CAST({dd_expr} AS INTEGER) IS NOT NULL
                             AND {dd_expr} != '00000000'
                             THEN {dd_expr} END
                        FROM read_parquet('{path_sql}')
                    )
                """)

        sql = f'INSERT INTO importaciones ({", ".join(insert_cols)}) SELECT {", ".join(selects)} FROM read_parquet(\'{path_sql}\')'
        conn.execute(sql)

        total_rows = conn.execute("SELECT COUNT(*) FROM importaciones").fetchone()[0]
        conn.execute(
            "INSERT OR REPLACE INTO _fuentes (archivo, mtime, filas, procesado) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            [fname, mtime, total_rows]
        )
        nuevos += 1
        print(f'    {fname}')

    if nuevos > 0 and not check_only:
        conn.execute("ALTER TABLE importaciones ADD COLUMN IF NOT EXISTS ANO INTEGER")
        conn.execute("""
            UPDATE importaciones SET ANO = TRY_CAST(SUBSTR(DD, 5, 4) AS INTEGER)
            WHERE DD IS NOT NULL AND LENGTH(DD) = 8 AND ANO IS NULL
        """)
        for idx_name, col in [
            ('idx_aranc', 'ARANC_NAC'), ('idx_orig', 'PA_ORIG'), ('idx_adq', 'PA_ADQ'),
            ('idx_importador', 'NUM_UNICO_IMPORTADOR'), ('idx_dd', 'DD'),
            ('idx_comuna', 'CODCOMUN'), ('idx_via_tran', 'VIA_TRAN'),
            ('idx_adu', 'ADU'), ('idx_ano', 'ANO'),
        ]:
            try:
                conn.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON importaciones ("{col}")')
            except Exception:
                pass
        conn.execute("ANALYZE")

    conn.close()
    return nuevos, omitidos


def main():
    parser = argparse.ArgumentParser(description='Ingesta incremental de parquet a DuckDB')
    parser.add_argument('--año', type=str, help='Año específico a procesar')
    parser.add_argument('--check', action='store_true', help='Solo mostrar qué archivos faltan')
    args = parser.parse_args()

    años = [args.año] if args.año else [str(a) for a in range(2017, 2027)]

    total_nuevos = 0
    total_omitidos = 0

    for a in años:
        n, o = procesar_año(a, check_only=args.check)
        total_nuevos += n
        total_omitidos += o

    if args.check:
        print(f'\nResumen: {total_nuevos} archivos nuevos/desactualizados, {total_omitidos} al día')
    else:
        print(f'\nResumen: {total_nuevos} archivos procesados, {total_omitidos} omitidos (ya estaban al día)')


if __name__ == '__main__':
    main()
