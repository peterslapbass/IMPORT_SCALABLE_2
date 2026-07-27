"""
Convierte archivos TXT originales a formato Parquet.
Lee archivos .txt (separados por ;, encoding latin1), asigna nombres de columna
desde la estructura DIN, y guarda como .parquet en data/PARQUET/{año}/.

Uso:
  python scripts/convertir_txt_a_parquet.py "data/TXT/Importaciones - mayo 2026.txt"
  python scripts/convertir_txt_a_parquet.py "data/TXT/*.txt"
  python scripts/convertir_txt_a_parquet.py "data/TXT/*.txt" --año 2026
  python scripts/convertir_txt_a_parquet.py "data/TXT/*.txt" --check
"""
import os, sys, glob, re, argparse, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import pandas as pd
from utils.helpers import cargar_descripcion_estructura

PARQUET_PATH = os.path.join(BASE, 'data', 'PARQUET')


def extraer_año_desde_nombre(filename):
    match = re.search(r'(\d{4})', os.path.basename(filename))
    return match.group(1) if match else None


def convertir_archivo(txt_path, año=None, check_only=False):
    basename = os.path.basename(txt_path)
    name_no_ext = os.path.splitext(basename)[0]

    if not año:
        año = extraer_año_desde_nombre(txt_path)
    if not año:
        print(f"  [SKIP] {basename} — no se pudo determinar el año")
        return False

    parquet_name = f"{name_no_ext}.parquet"
    year_path = os.path.join(PARQUET_PATH, año)
    parquet_path = os.path.join(year_path, parquet_name)

    if check_only:
        existe = " (ya existe)" if os.path.exists(parquet_path) else ""
        print(f"  {basename} → data/PARQUET/{año}/{parquet_name}{existe}")
        return True

    os.makedirs(year_path, exist_ok=True)

    if os.path.exists(parquet_path):
        print(f"  [SKIP] {parquet_name} ya existe en PARQUET/{año}/")
        return True

    try:
        columnas = cargar_descripcion_estructura()
        start = time.time()

        df = pd.read_csv(
            txt_path,
            sep=";",
            encoding="latin1",
            header=None,
            dtype=str,
            low_memory=False
        )

        ncols = min(len(df.columns), len(columnas))
        df = df.iloc[:, :ncols]
        df.columns = columnas[:ncols]

        df.to_parquet(parquet_path, index=False)

        elapsed = time.time() - start
        filas = len(df)
        cols = len(df.columns)
        print(f"  [OK] {parquet_name} ({filas:,} filas, {cols} cols, {elapsed:.1f}s)")
        return True

    except Exception as e:
        print(f"  [ERROR] {basename}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Convierte TXT originales a Parquet para ingesta")
    parser.add_argument("archivos", nargs="+", help="Ruta(s) a archivos .txt o glob (ej: 'data/TXT/*.txt')")
    parser.add_argument("--año", help="Forzar año (si no se puede detectar desde el nombre)")
    parser.add_argument("--check", action="store_true", help="Solo mostrar qué archivos se convertirían")
    args = parser.parse_args()

    archivos = []
    for pattern in args.archivos:
        encontrados = sorted(glob.glob(pattern))
        if not encontrados:
            print(f"Advertencia: '{pattern}' no encontró archivos")
        archivos.extend(encontrados)

    if not archivos:
        print("No hay archivos para procesar.")
        sys.exit(1)

    print(f"Archivos encontrados: {len(archivos)}")
    if not args.check:
        print("-" * 60)

    ok = 0
    for f in archivos:
        if convertir_archivo(f, año=args.año, check_only=args.check):
            ok += 1

    if args.check:
        print(f"\nResumen: {ok} archivos listos para convertir de {len(archivos)}")
    else:
        print(f"\nResumen: {ok} de {len(archivos)} archivos convertidos correctamente")
        if ok:
            print("Ejecuta 'python scripts/ingestar.py' para incorporarlos a DuckDB")


if __name__ == "__main__":
    main()
