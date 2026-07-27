# validator.py

import pandas as pd

def validar_df(df, columnas_esperadas=None):
    print("🔍 VALIDACIÓN DEL ARCHIVO")
    
    # Columnas
    print("✔️ Columnas presentes:", list(df.columns))
    if columnas_esperadas:
        faltantes = [col for col in columnas_esperadas if col not in df.columns]
        if faltantes:
            print("⚠️ Columnas faltantes:", faltantes)
        else:
            print("✅ Todas las columnas esperadas están presentes.")

    # Tamaño y nulos
    print("📏 Shape:", df.shape)
    print("🧼 Nulos por columna:\n", df.isnull().sum())

    # Tipos de datos
    print("🧪 Tipos de datos:\n", df.dtypes)

    # Duplicados y filas vacías
    print("🔁 Filas duplicadas:", df.duplicated().sum())
    vacías = df[df.isnull().all(axis=1)]
    print("⚪ Filas completamente vacías:", len(vacías))

    # Formato de fecha 'DD' si existe
    if 'DD' in df.columns:
        try:
            fechas = pd.to_datetime(df['DD'], errors='raise')
            print("🗓️ Fechas válidas en columna 'DD'")
        except Exception as e:
            print("❌ Error al parsear fechas en 'DD':", str(e))

    print("✅ Validación completada.")
