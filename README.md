# ImportRealMod

Dashboard interactivo para el análisis de importaciones chilenas (2017–2026).
Construido con **Dash**, **Plotly** y **DuckDB**.

## Requisitos

- Python 3.9+
- Navegador web

## Instalación

```bash
git clone https://github.com/tu-usuario/importrealmod.git
cd importrealmod
pip install -r requirements.txt
```

## Datasets

El proyecto necesita los siguientes archivos en `data/`:

| Archivo | Tamaño | Descripción |
|---|---|---|
| `DICCIONARIO.xlsx` | ~60 KB | Diccionario maestro códigos → glosas (incluido en el repo) |
| `descripcion-y-estructura-de-datos.xlsx` | ~20 KB | Estructura de columnas DIN (incluido) |
| `comunas.csv` | ~10 KB | Coordenadas de comunas (incluido) |
| `puertos_coordenadas.csv` | ~10 KB | Coordenadas de puertos (incluido) |
| `import.csv` | ~10 KB | Lista de importadores SII (incluido) |
| `import.txt` | ~185 MB | RUT → Razón Social del SII (**no incluido** — descargar desde [SII Chile](https://www.sii.cl)) |
| Parquets mensuales | ~17 GB total | Datos de importación por mes (se generan desde TXT) |

> **Nota:** `data/import.txt` supera el límite de archivos de GitHub (185 MB).
> Debes copiarlo manualmente al clonar el repositorio. Sin este archivo no
> funcionará el mapeo de RUT a nombre de empresa en los gráficos.

## Flujo de trabajo completo

### 1. Preparar los TXT originales

Coloca los archivos TXT originales (formato Aduanas, separados por `;`,
encoding `latin1`) en `data/TXT/`:

```
data/TXT/
├── ENE 2017- Importaciones.txt
├── FEB 2017- Importaciones.txt
├── MAR 2017- Importaciones.txt
...
```

### 2. Convertir TXT → Parquet

```bash
python scripts/convertir_txt_a_parquet.py "data/TXT/*.txt"
```

Esto genera archivos `.parquet` en `data/PARQUET/{año}/`. Los parquets
mantienen la estructura de columnas DIN para que DuckDB los interprete
correctamente.

### 3. Construir las bases de datos DuckDB

```bash
python scripts/construir_base_duckdb.py
```

Crea `data/importaciones_{año}.db` para cada año (2017–2026), con:

- Tabla `importaciones` con todas las columnas DIN
- Columnas decimales convertidas correctamente (`,` → `.`)
- Columna `ANO` derivada desde `DD`
- Índices por: ARANC_NAC, PA_ORIG, PA_ADQ, NUM_UNICO_IMPORTADOR, DD,
  CODCOMUN, VIA_TRAN, ADU, ANO

### 4. Ingesta incremental (archivos nuevos)

Cuando lleguen nuevos archivos mensuales:

```bash
python scripts/convertir_txt_a_parquet.py "data/TXT/Importaciones - mayo 2026.txt"
python scripts/ingestar.py --año 2026
```

También puedes ver qué falta sin modificar nada:

```bash
python scripts/ingestar.py --check
```

### 5. Ejecutar la aplicación

```bash
python app.py --browser
```

Esto inicia el servidor en `http://127.0.0.1:8050`.

Para versión de escritorio (pywebview):

```bash
python app.py
```

## Estructura del proyecto

```
├── app.py                          # Punto de entrada (Dash + pywebview)
├── callbacks.py                    # Todos los callbacks y generación de gráficos
├── layout.py                       # UI (sidebar, tabs, filtros)
├── safe_uploader.py                # Subida segura de archivos (Flask)
├── validator.py                    # Validación de DataFrames
│
├── assets/                         # CSS, logo
├── data/                           # Bases de datos, diccionarios, parquets
│   ├── PARQUET/{año}/              # Archivos parquet mensuales
│   ├── DICCIONARIO.xlsx            # Diccionario maestro
│   └── importaciones_{año}.db      # Bases DuckDB (generadas)
│
├── scripts/
│   ├── convertir_txt_a_parquet.py  # TXT original → Parquet
│   ├── construir_base_duckdb.py    # Parquet → DuckDB (build completo)
│   ├── ingestar.py                 # Ingesta incremental
│   ├── exportar_sii_parquet.py     # SII SQLite → Parquet
│   ├── generar_mapeo_hs_actividades.py  # TF-IDF HS ↔ actividades
│   └── scrape_diccionarios_comext.py    # Scraping Comext
│
├── tests/
│   └── test_callbacks.py
│
└── utils/
    └── helpers.py                  # Conexiones, consultas, diccionarios
```

## Scripts útiles

| Comando | Qué hace |
|---|---|
| `python scripts/convertir_txt_a_parquet.py "data/TXT/*.txt"` | Convierte TXT a Parquet |
| `python scripts/convertir_txt_a_parquet.py "data/TXT/*.txt" --check` | Vista previa de conversión |
| `python scripts/construir_base_duckdb.py` | Construye DuckDBs desde cero |
| `python scripts/ingestar.py --año 2026` | Ingiere archivos nuevos del año |
| `python scripts/ingestar.py --check` | Muestra qué archivos faltan |
| `python app.py` | Inicia la app (escritorio) |
| `python app.py --browser` | Inicia la app (navegador) |

## Tecnologías

- **Dash** / **Plotly** — UI interactiva y visualizaciones
- **DuckDB** — Base de datos analítica embebida
- **Pandas** — Transformación de datos
- **pywebview** — Versión de escritorio (Edge Chromium)
