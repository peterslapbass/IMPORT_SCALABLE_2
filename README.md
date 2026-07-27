<p align="center">
  <img src="assets/logo.png" alt="ImportRealMod" width="120"/>
</p>

<h1 align="center">ImportRealMod</h1>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue?logo=python" alt="Python 3.9+"/>
  <img src="https://img.shields.io/badge/dash-2.0+-blue?logo=plotly" alt="Dash 2.0+"/>
  <img src="https://img.shields.io/badge/duckdb-0.8+-yellow?logo=duckdb" alt="DuckDB 0.8+"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License MIT"/>
</p>

<p align="center">
  Plataforma de inteligencia de negocio para importaciones chilenas que transforma ~17 GB de datos aduaneros en visualizaciones interactivas (8 tabs, 30+ gráficos) con búsqueda en milisegundos gracias a DuckDB.
</p>

---

## Características

- **8 tabs analíticos** — Resumen, Países, Productos, Transporte y Rutas, Geografía, Tablas, Financiero, Clasificación
- **Filtros combinados** — años, código arancelario, RUT importador, rango de fechas, producto, país de origen/adquisición, comuna, sección HS
- **Drill-down** — haz clic en cualquier gráfico para filtrar dinámicamente por esa dimensión
- **Tema oscuro/claro** — persistente en localStorage
- **Exportación** — CSV, Excel, HTML (todos los gráficos), impresión PDF
- **Modo escritorio** — ventana nativa con pywebview (Edge Chromium)
- **Ingesta incremental** — agrega nuevos archivos mensuales sin reconstruir todo
- **Caché de tabs** — precarga del siguiente tab en segundo plano para navegación instantánea
- **Procesamiento paralelo** — generación simultánea de gráficos con ThreadPoolExecutor

## Tecnologías

| Tecnología | Uso |
|---|---|
| [Dash](https://dash.plotly.com/) / [Plotly](https://plotly.com/python/) | UI interactiva y visualizaciones |
| [DuckDB](https://duckdb.org/) | Base de datos analítica embebida (OLAP) |
| [Pandas](https://pandas.pydata.org/) / [NumPy](https://numpy.org/) | Transformación y cómputo de datos |
| [pywebview](https://pywebview.flowrl.com/) | Versión de escritorio (Edge Chromium) |
| [Flask](https://flask.palletsprojects.com/) | Subida segura de archivos |
| [openpyxl](https://openpyxl.readthedocs.io/) | Exportación a Excel |

<!--
## Capturas de pantalla

<p align="center">
  <img src="assets/screenshots/resumen.png" alt="Tab Resumen" width="45%"/>
  <img src="assets/screenshots/paises.png" alt="Tab Países" width="45%"/>
  <br/>
  <img src="assets/screenshots/productos.png" alt="Tab Productos" width="45%"/>
  <img src="assets/screenshots/transporte.png" alt="Tab Transporte" width="45%"/>
</p>
-->

---

## Requisitos

- Python 3.9+
- Navegador web (modo browser) o Edge Chromium (modo escritorio)

## Instalación

```bash
git clone https://github.com/peterslapbass/IMPORT_SCALABLE_2.git
cd IMPORT_SCALABLE_2
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

---

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

---

## Descripción de los Tabs

| Tab | Gráficos incluidos |
|---|---|
| **Resumen** | Evolución mensual CIF, Evolución mensual cantidad, Precio CIF/Kg mensual, Comparación interanual (YoY), Distribución de precios unitarios, Porcentaje por variable (barra %), Concentración de importadores (Top 10) |
| **Países** | CIF mensual por país de origen, CIF mensual por país de adquisición, Heatmap país origen vs tiempo, Heatmap país adquisición vs tiempo, Distribución de precios por país de origen |
| **Productos** | Distribución por sección (Section), Top 20 productos por frecuencia, Top 20 productos por valor CIF, Jerarquía de productos (Treemap: Section → HS → Código) |
| **Transporte y Rutas** | CIF por medio de transporte, Top 15 aduanas, Distribución por tipo de operación, Top 15 tipos de bulto, Mapa de puertos, Diagrama Sankey puerto embarque → desembarque, Matriz puertos (Top 10) |
| **Geografía** | Mapa de comunas con CIF y cantidad, Mapa de puertos con volumen CIF |
| **Tablas** | Importadores coincidentes (RUT → Razón Social), Top 20 productos por frecuencia (completo), Top 20 productos por valor CIF (completo), Top 20 transacciones individuales, Precio promedio por país de origen/adquisición |
| **Financiero** | CIF por moneda, CIF por forma de pago, Distribución por cláusula de compra (Incoterms), CIF por origen de divisas, Desglose de costos (FOB + Flete + Seguro vs CIF) |
| **Clasificación** | CIF por régimen de importación, Top 15 unidades de medida, Top 15 bancos comerciales, Arancel efectivo promedio por sección, Días de despacho (aceptación → almacenaje) |

---

## Estructura de datos DIN

Los archivos de importación contienen las siguientes columnas (definidas en `data/descripcion-y-estructura-de-datos.xlsx`):

| Grupo | Columnas |
|---|---|
| **Fechas** | `DD` (día), `FECACEP`, `FEC_ALMAC` |
| **Producto** | `ARANC_NAC`, `DNOMBRE`, `DMARCA`, `DVARIEDAD`, `DOTRO1`, `DOTRO2`, `ATR_5`, `ATR_6`, `PRODUCTO` |
| **Valores** | `CIF_ITEM`, `FOB`, `FLETE`, `SEGURO`, `CIF`, `PRE_UNIT`, `ADVAL_ALA`, `ADVAL`, `VALAD`, `VAL1`–`VAL4` |
| **Cantidades** | `CANT_MERC`, `TOT_BULTOS`, `CANT_BUL1`, `CANT_BUL2` |
| **Países** | `PA_ORIG` (origen), `PA_ADQ` (adquisición) |
| **Transporte** | `VIA_TRAN`, `TPO_CARGA`, `PTO_EMB`, `PTO_DESEM` |
| **Geografía** | `CODCOMUN` (comuna), `ADU` (aduana) |
| **Importador** | `NUM_UNICO_IMPORTADOR`, `NUM_UNICO_IMPORTADOR_ORIGINAL` |
| **Clasificación** | `TPO_DOCTO`, `REG_IMP`, `MEDIDA`, `TPO_BUL1`, `TPO_BUL2`, `MONEDA`, `FORM_PAGO`, `CL_COMPRA`, `CODORDIV`, `BCO_COM`, `CODVISBUEN`, `PAGO_GRAV`, `DESOBS1`, `ID_BULTOS` |
| **Derivadas** | `Section`, `HS Description`, `Chapter`, `ANO`, `MES` |

---

## Fuentes de datos

- **Aduanas de Chile** — Archivos mensuales de importación con detalle de cada declaración (código arancelario, valor CIF, país de origen, transporte, etc.)
- **Servicio de Impuestos Internos (SII)** — Registro de importadores con RUT y Razón Social (usado para mapear RUT → nombre de empresa en gráficos)
- **Comext** ([comext.aduana.cl](http://comext.aduana.cl:7001)) — Diccionarios de códigos: formas de pago, monedas, bancos, regímenes de importación, etc. (se obtienen con `scripts/scrape_diccionarios_comext.py`)

---

## Referencia de Scripts

| Comando | Qué hace |
|---|---|
| `python scripts/convertir_txt_a_parquet.py "data/TXT/*.txt"` | Convierte TXT originales a Parquet |
| `python scripts/convertir_txt_a_parquet.py "data/TXT/*.txt" --check` | Vista previa (solo muestra qué se convertirá) |
| `python scripts/construir_base_duckdb.py` | Construye las DuckDBs desde cero (todos los años) |
| `python scripts/ingestar.py` | Ingesta incremental de archivos nuevos (todos los años) |
| `python scripts/ingestar.py --año 2026` | Ingesta incremental solo para un año |
| `python scripts/ingestar.py --check` | Muestra qué archivos faltan por ingestar |
| `python scripts/exportar_sii_parquet.py` | Exporta datos SII (SQLite) a Parquet |
| `python scripts/generar_mapeo_hs_actividades.py` | Genera mapeo TF-IDF entre códigos HS y actividades económicas SII |
| `python scripts/scrape_diccionarios_comext.py` | Scrapea diccionarios de Comext y actualiza DICCIONARIO.xlsx |

---

## Ajuste de rendimiento

El proyecto usa DuckDB con las siguientes optimizaciones:

```sql
PRAGMA threads = 4;         -- Hasta 4 hilos por query
PRAGMA memory_limit = '8GB'; -- Límite de memoria
```

**Recomendaciones:**
- **SSD** — Las queries sobre parquets se benefician enormemente de discos SSD
- **Memoria RAM** — 8 GB o más recomendado
- **Paralelismo** — La generación de gráficos corre en hasta 4 hilos simultáneos (`ThreadPoolExecutor`)
- **Caché** — Los tabs ya generados se cachean en memoria; cambiar filtros invalida la caché

---

## Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| `Error 408` al hacer `git push` | Archivos grandes en el historial | Usar `git checkout --orphan latest` y hacer un commit fresco (ver sección Instalación) |
| La app no muestra datos | DuckDB no construida o sin parquets | Ejecutar `python scripts/construir_base_duckdb.py` |
| "No hay base DuckDB para los años seleccionados" | Falta ejecutar construcción | Ver punto anterior |
| `data/import.txt` no encontrado | Archivo no descargado desde SII | Descargar desde [SII Chile](https://www.sii.cl) y copiar a `data/import.txt` |
| Los gráficos muestran RUT en vez de nombre de empresa | `import.txt` faltante o incompleto | Ver fila anterior |
| Puerto 8050 ya en uso | Otra instancia ejecutándose | Cerrar la otra instancia o cambiar el puerto en `app.py` |
| Error de memoria DuckDB | `PRAGMA memory_limit` muy alto para el equipo | Reducir a `4GB` o `2GB` en `utils/helpers.py` línea 84 |

---

## Estructura del proyecto

```
├── app.py                          # Punto de entrada (Dash + pywebview)
├── callbacks.py                    # Todos los callbacks y generación de gráficos
├── layout.py                       # UI (sidebar, tabs, filtros)
├── safe_uploader.py                # Subida segura de archivos (Flask)
├── validator.py                    # Validación de DataFrames
│
├── assets/                         # CSS, logo
│   ├── dashboard.css               # Estilos (tema oscuro/claro)
│   ├── print.css                   # Estilos de impresión PDF
│   └── logo.png                    # Logo de la aplicación
│
├── data/                           # Bases de datos, diccionarios, parquets
│   ├── PARQUET/{año}/              # Archivos parquet mensuales
│   ├── DICCIONARIO.xlsx            # Diccionario maestro códigos → glosas
│   ├── descripcion-y-estructura-de-datos.xlsx  # Estructura de columnas DIN
│   ├── comunas.csv                 # Coordenadas de comunas
│   ├── puertos_coordenadas.csv     # Coordenadas de puertos
│   ├── import.txt                  # RUT → Razón Social SII (no incluido en repo)
│   └── importaciones_{año}.db      # Bases DuckDB (generadas por construir_base_duckdb.py)
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
│   └── test_callbacks.py          # Tests unitarios (pytest)
│
└── utils/
    └── helpers.py                  # Conexiones DuckDB, consultas, diccionarios
```

---

## Licencia

MIT
