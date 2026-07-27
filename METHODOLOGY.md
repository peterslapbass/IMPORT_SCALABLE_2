# Methodology — Análisis de Importaciones Chilenas

## 1. Fuente de datos

### 1.1 Aduanas de Chile — Declaraciones de Importación

- **Formato original**: archivos TXT separados por `;`, encoding `latin1`, sin encabezado
- **Período**: 2017–2026 (archivos mensuales por año)
- **Estructura**: 178 columnas definidas en `data/descripcion-y-estructura-de-datos.xlsx` (hoja `DIN`)
- **Cobertura**: todas las declaraciones de ingreso al país, por item (línea de producto)
- **Campos principales** (~178 columnas agrupadas):

| Grupo | Campos clave |
|---|---|
| **Identificación** | NUMENCRIPTADO, TPO_DOCTO (tipo de operación), ADU (aduana), FORM |
| **Fechas** | DD (fecha documento), FECACEP (aceptación), FEC_ALMAC (almacenaje), FECTRA (trámite), FECRETIRO (retiro) |
| **Importador** | NUM_UNICO_IMPORTADOR (RUT), CODCOMUN (comuna), CODPAISCON (país consignante) |
| **Producto** | ARANC_NAC (código armonizado 8 dígitos), DNOMBRE, DMARCA, DVARIEDAD, DOTRO1/2, ATR_5/6 |
| **Valores** | CIF_ITEM (valor CIF del item), FOB, FLETE, SEGURO, CIF (total), PRE_UNIT (precio unitario FOB) |
| **Impuestos** | ADVAL_ALA (% advalorem), VALAD (monto), VAL1–VAL4 (otros impuestos), MON_178 (IVA), MON_191 (total giro) |
| **Origen/Destino** | PA_ORIG (país de origen), PA_ADQ (país de adquisición), PTO_EMB (puerto embarque), PTO_DESEM (puerto desembarque), VIA_TRAN (vía transporte) |
| **Logística** | TPO_CARGA (tipo de carga), TOT_BULTOS, TPO_BUL1–8, CANT_BUL1–8, ID_BULTOS |
| **Financiero** | MONEDA, FORM_PAGO, CL_COMPRA (Incoterm), CODORDIV (origen divisas), BCO_COM (banco) |
| **Régimen** | REG_IMP (régimen importación), MEDIDA (unidad medida), CODVISBUEN (visto bueno), PAGO_GRAV |
| **Pago diferido** | TASA (tasa interés), NCUOTAS, ADU_DI, NUM_DI, FEC_DI, MON_699 |
| **Acuerdos** | NUMACU (acuerdo comercial), ARANC_ALA (arancel ALADI) |
| **Observaciones** | CODOBS1–4, DESOBS1–4 |

### 1.2 SII — Registro de Importadores

- **Archivo**: `data/import.txt` (TAB-separado, 3.126.421 registros)
- **Columnas**: `RUT` (int), `DV` (dígito verificador), `COD_SUBTIPO` (tipo sociedad), `RAZON_SOCIAL` (razón social), `FECHA_INICIO_VIG` (inicio vigencia), `FECHA_TG_VIG` (término vigencia)
- **Uso**: mapeo RUT → Razón Social para mostrar nombres de empresas en gráficos y tablas

### 1.3 Comext — Diccionarios de Códigos

- **Fuente**: [comext.aduana.cl:7001](http://comext.aduana.cl:7001)
- **Scraping**: `scripts/scrape_diccionarios_comext.py`
- **Destino**: `data/DICCIONARIO.xlsx` (24 hojas, ~1.800 códigos mapeados)

### 1.4 Datos geográficos

- `data/comunas.csv`: 338 comunas chilenas con coordenadas (lat/lon)
- `data/puertos_coordenadas.csv`: 344 puertos mundiales con coordenadas (lat/lon)

## 2. Pipeline de procesamiento

```
TXT original (Aduanas)
   │
   ▼
1. Convertir TXT → Parquet
   ─────────────────────────
   • lectura: pd.read_csv(sep=";", encoding="latin1", header=None, dtype=str)
   • asignación de nombres de columna desde estructura DIN
   • escritura: df.to_parquet() → data/PARQUET/{año}/
   • script: scripts/convertir_txt_a_parquet.py
   │
   ▼
2. Cargar Parquet → DuckDB
   ─────────────────────────
   • mapeo posicional de columnas (por orden, no por nombre)
   • columnas decimales (14): conversión coma → punto y CAST a DOUBLE
     (CIF_ITEM, CANT_MERC, FOB, FLETE, SEGURO, CIF, PRE_UNIT,
      ADVAL_ALA, ADVAL, VALAD, VAL1, VAL2, VAL3, VAL4)
   • columna DD: padding a 8 dígitos, validación numérica
   • columna ANO: derivada de SUBSTR(DD, 5, 4)
   • índices: ARANC_NAC, PA_ORIG, PA_ADQ, NUM_UNICO_IMPORTADOR, DD,
     CODCOMUN, VIA_TRAN, ADU, ANO
   • script: scripts/construir_base_duckdb.py
   │
   ▼
3. Consultas en tiempo real (Dash)
   ──────────────────────────────
   • ATTACH READ_ONLY a bases por año
   • UNION ALL BY NAME → vista temporal `todas`
   • queries agregadas con SUM, GROUP BY, filtros ILIKE
   • script: utils/helpers.py (funciones query_parquet, query_aggregated, query_raw)
```

## 3. Enriquecimiento de datos

El dashboard aplica dos tipos de enriquecimiento:

### 3.1 Mapeo códigos → glosas (DICCIONARIO.xlsx)

Cada columna codificada se mapea a su descripción legible mediante `enriquecer_desde_diccionarios()`:

| Columna en datos | Diccionario (hoja) | Ejemplo de mapeo |
|---|---|---|
| PA_ORIG, PA_ADQ | PAIS (243 países) | 034 → "ARGENTINA" |
| VIA_TRAN | TRANSPORTE (9 modos) | 1 → "MARITIMO" |
| TPO_CARGA | CARGA (6 tipos) | F → "REFRIGERADA" |
| CODCOMUN | COMUNA (346 comunas) | 1101 → "ARICA" |
| ADU | ADUANA (17 aduanas) | 10 → "ARICA" |
| PTO_EMB, PTO_DESEM | PUERTOS (347 puertos) | 101 → "VALPARAISO" |
| TPO_DOCTO | OPERACION (60 tipos) | 107 → "IMPORTACION" |
| TPO_BUL1, TPO_BUL2 | BULTO (67 tipos) | 1 → "PALLET" |
| MONEDA | MONEDAS (50 monedas) | 001 → "DOLAR USA" |
| FORM_PAGO | FORMAS_PAGOS (38 formas) | 11 → "CREDITO DIRECT." |
| REG_IMP | REGIMEN_IMPORTACION (27 regímenes) | 12 → "IMPORT. COMUN" |
| MEDIDA | UNIDAD_MEDIDA (24 unidades) | 04 → "KILO NETO" |
| BCO_COM | BANCOS_COMERCIALES (30 bancos) | 15 → "BANCO DE CHILE" |
| CL_COMPRA | CLAUSULA_COMPRA_VENTA (13 incoterms) | 0 → "CIF" |
| CODORDIV | ORIGEN_DIVISAS (5 orígenes) | 1 → "PROPIAS" |
| CODVISBUEN | VISTOS_BUENOS (22 entidades) | 1 → "S.A.G." |
| PAGO_GRAV | FORMAS_PAGO_GRAVAMEN (82 formas) | 123 → "CONTADO" |

### 3.2 Clasificación arancelaria (CATEGORIA_HS)

El código ARANC_NAC (8 dígitos) se descompone jerárquicamente:

```
Section (21 categorías, ej: "Textiles", "Machines")
   └── HS Description (98 capítulos, ej: "CHAPTER 52 - COTTON")
        └── Chapter (2 dígitos, ej: 52)
             └── ARANC_NAC (8 dígitos, ej: 52094200)
```

Las 21 secciones del sistema armonizado:

| Section | Descripción | Capítulos |
|---|---|---|
| I | Animals product | 1–5 |
| II | Vegetable product | 6–14 |
| III | Animal and Vegetable Bi-Products | 15 |
| IV | Foodstuffs | 16–24 |
| V | Mineral Products | 25–27 |
| VI | Chemical products | 28–38 |
| VII | Plastic and Rubbers | 39–40 |
| VIII | Animal Hides | 41–43 |
| IX | Wood Products | 44–46 |
| X | Paper Goods | 47–49 |
| XI | Textiles | 50–63 |
| XII | Footwear and Headwear | 64–67 |
| XIII | Stone and Glass | 68–70 |
| XIV | Precious Metals | 71 |
| XV | Metals | 72–83 |
| XVI | Machines | 84–85 |
| XVII | Transportation | 86–89 |
| XVIII | Instruments | 90–92 |
| XIX | Weapons | 93 |
| XX | Miscellaneous | 94–96 |
| XXI | Art and Antiques | 97 |

### 3.3 Mapeo RUT → Razón Social

- Diccionario: `import_dict` (dict con 3.1M entries: `{RUT: RAZON_SOCIAL}`)
- Se aplica en: gráfico de concentración (Resumen), tabla Top 20 individual (Tablas), barra % por variable, exportaciones CSV/Excel

## 4. Motor de base de datos (DuckDB)

### 4.1 Configuración

```sql
PRAGMA memory_limit = '8GB';  -- Límite de memoria RAM
PRAGMA threads = 4;            -- Hilos paralelos por query
```

### 4.2 Conexiones

- Cada año es un archivo DuckDB separado: `data/importaciones_{año}.db`
- Las queries multi-año usan `ATTACH READ_ONLY` + `UNION ALL BY NAME`
- La conexión global se recicla al cambiar los años seleccionados
- En generación paralela de gráficos, cada hilo crea su propia conexión

### 4.3 Columnas decimales (14)

Almacenadas como VARCHAR en parquet (con coma decimal), convertidas a DOUBLE durante la ingesta:
- `CIF_ITEM`, `CANT_MERC`, `FOB`, `FLETE`, `SEGURO`, `CIF`
- `PRE_UNIT`, `ADVAL_ALA`, `ADVAL`, `VALAD`, `VAL1`, `VAL2`, `VAL3`, `VAL4`

### 4.4 Índices

Creados en cada tabla `importaciones`:
- `idx_aranc`, `idx_orig`, `idx_adq`, `idx_importador`
- `idx_dd`, `idx_comuna`, `idx_via_tran`, `idx_adu`, `idx_ano`

## 5. Dashboard — Visualizaciones

### 5.1 Tabs y generadores (30 generadores, 8 tabs)

| Tab | Generadores | Tipo de visualización |
|---|---|---|
| **Resumen** | monthly, yoy, price_hist, pct_bar, importer_conc | Área, líneas, histograma, barras |
| **Países** | country_analysis, heat_analysis, box_precios | Líneas, heatmap, boxplot |
| **Productos** | section, top20_analysis, treemap | Pie, barras horizontales, treemap |
| **Transporte y Rutas** | transporte, aduana, operacion, bultos, port_analysis | Barras, pie, sankey, mapa, matriz |
| **Geografía** | mapa_comunas, port_analysis (reuso) | Scatter mapbox |
| **Tablas** | top20_analysis, top20_ind, avg_price_analysis, importadores | DataTables |
| **Financiero** | monedas, formas_pago, clausula, origen_divisas, cost_breakdown | Barras, pie |
| **Clasificación** | regimen, unidad, bancos, tariff, dispatch_days | Barras, histograma |

### 5.2 Filtros disponibles (12 controles)

- Años (checklist 2017–2026)
- Código arancelario (texto, términos separados por coma)
- Importador RUT (dropdown con autocompletado desde SII)
- Rango de fechas (día, mes, año desde/hasta)
- Producto, Importador, País origen, País adquisición, Comuna (texto, ILIKE)
- Columna para barra % (dropdown: NUM_UNICO_IMPORTADOR, PA_ORIG, PA_ADQ, TPO_CARGA, VIA_TRAN, TPO_BUL1, TPO_BUL2)
- Section HS, HS Description (dropdowns dinámicos multi-select)

### 5.3 Métricas clave

- **CIF_ITEM**: valor CIF del item en USD (costo, seguro y flete)
- **CANT_MERC**: cantidad de mercancía en kg
- **PRE_UNIT**: precio unitario (CIF_ITEM / CANT_MERC)
- **FOB, FLETE, SEGURO**: desglose de costos
- **Conteo**: frecuencia de importación (número de declaraciones)
- **ADVAL_ALA**: tasa arancelaria efectiva (%)

## 6. Arquitectura del sistema

```
┌──────────────────────────────────────────────────────────┐
│                     Navegador Web                         │
│              http://127.0.0.1:8050                        │
└────────────────────────┬─────────────────────────────────┘
                         │ Dash (HTTP/WebSocket)
┌────────────────────────▼─────────────────────────────────┐
│                   callbacks.py                            │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│   │ Filtros  │  │  Tabs    │  │  Exportación          │   │
│   │ SQL      │  │  Caché   │  │  CSV / Excel / HTML   │   │
│   └────┬─────┘  └────┬─────┘  └──────────────────────┘   │
│        │              │                                    │
│   ┌────▼──────────────▼─────┐                              │
│   │  _run_gens()           │                              │
│   │  ThreadPoolExecutor    │                              │
│   │  (max 4 workers)       │                              │
│   └────┬──────────────┬─────┘                              │
└────────┼──────────────┼────────────────────────────────────┘
         │              │
         │ conn (1)     │ conn (2..n)
┌────────▼──────────────▼────────────────────────────────────┐
│                    utils/helpers.py                         │
│  ┌─────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ DuckDB conn  │  │  Diccionarios    │  │  Geografía    │  │
│  │ (attach años)│  │  (24 hojas xlsx) │  │  (comunas,    │  │
│  │              │  │  + import_dict)  │  │   puertos)    │  │
│  └──────┬───────┘  └──────────────────┘  └───────────────┘  │
└─────────┼────────────────────────────────────────────────────┘
          │
┌─────────▼──────────────────────────────────────────────────┐
│  data/importaciones_{año}.db   (DuckDB files, read-only)   │
│  data/PARQUET/{año}/*.parquet  (source parquet files)      │
│  data/DICCIONARIO.xlsx         (master dictionary)         │
│  data/import.txt               (SII importer registry)     │
└────────────────────────────────────────────────────────────┘
```

## 7. Rendimiento y optimización

### 7.1 Paralelismo
- Generación de gráficos: hasta 4 hilos simultáneos (ThreadPoolExecutor)
- DuckDB: hasta 4 hilos por query (PRAGMA threads=4)
- Precarga del siguiente tab en segundo plano

### 7.2 Caché
- Caché de tabs generados en memoria (`_TAB_CACHE`)
- Invalidación por hash de parámetros de filtro
- Caché de diccionarios (DICCIONARIO.xlsx) con verificación de mtime
- Caché de estructura DIN y listado de parquets

### 7.3 Almacenamiento
- Parquet: formato columnar comprimido (~17 GB total)
- DuckDB: archivos por año, attach read-only para queries multi-año
- Índices en columnas de filtrado frecuente
- Columnas decimales como DOUBLE (no string)
