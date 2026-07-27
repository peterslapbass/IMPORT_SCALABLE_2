"""
Mapeo entre SECCION de CATEGORIA_HS (22 secciones) y actividades económicas SII.
Usa TF-IDF con n-gramas de caracteres (2-5) + cosine similarity.
Guarda data/sii/mapeo_hs_actividades.csv
"""
import os
import pandas as pd
import numpy as np
import duckdb
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SII_DIR = os.path.join(BASE, 'data', 'sii')
DICCIONARIO_PATH = os.path.join(BASE, 'data', 'DICCIONARIO.xlsx')
OUTPUT_PATH = os.path.join(SII_DIR, 'mapeo_hs_actividades.csv')

SPANISH_KWS = {
    'Animals product':
        'animales ganado carne pescado marisco leche lacteo lacteos quesos mantequilla '
        'huevos miel abejas cera abeja curtiembre cuero piel pieles lana seda',
    'Vegetable product':
        'agricultura agricola cultivo flores arboles plantas hortalizas frutas verduras '
        'frutos secos nueces almendras citricos te cafe especias condimentos cereales trigo '
        'arroz maiz avena cebada centeno harina malta almidon inulina gluten semillas oleaginosas '
        'aceite vegetal laca gomas resinas extractos vegetales paja forraje',
    'Animal and Vegetable Bi-Products':
        'grasas aceites animales vegetales manteca ceras jabon',
    'Foodstuffs':
        'carne preparada pescado preparado crustaceos moluscos azucar caramelos confites '
        'cacao chocolate pan pasteles galletas cereales preparados leche preparada harina preparada '
        'fruta preparada verdura preparada salsa bebidas alcohólicas vino cerveza licores aguardiente '
        'vinagre alimentos preparados tabaco cigarros cigarrillos forraje alimentos animales',
    'Mineral Products':
        'sal mineral minerales azufre tierra piedra yeso cal cemento carbon petroleo gas '
        'combustible mineria minero extraccion',
    'Chemical products':
        'quimico quimica farmaceutico farmaceutica farmacos medicamentos abono fertilizante '
        'pintura barniz tinta pigmento colorante cosmetico perfume jabon detergente lubricante '
        'explosivo fosforo fotografia cinematografia colageno gelatina enzima pegamento adhesivo',
    'Plastic and Rubbers':
        'plastico plasticos caucho polimero resina sintetica neumatico cubierta',
    'Animal Hides':
        'cuero piel curtiembre curtido adobo talabarteria marroquineria maleta bolso cartera '
        'guante peleteria pieles',
    'Wood Products':
        'madera carpinteria aserradero tablero enchapado contrachapado corcho cesteria mimbre '
        'basketware paja esparto',
    'Paper Goods':
        'papel carton pulpa celulosa fibra celulosica imprenta impresion publicacion '
        'periodico libro editorial',
    'Textiles':
        'textil textiles hilo tela tejido fibra algodon lana seda lino yute fieltro '
        'no tejido cuerda cordel alfombra tapiz encaje bordado prenda vestir ropa '
        'indumentaria confeccion calcetines medias',
    'Foodwear and Headwear':
        'calzado zapatos botas sandalias alpargatas sombrero gorra paraguas baston '
        'plumas artificiales flores artificiales',
    'Stone and Glass':
        'piedra marmol granito pizarra ceramica loza porcelana gres vidrio cristal '
        'fibra vidrio amianto mica ladrillo baldosa cemento',
    'Precious Metals':
        'joyas joyeria orfebreria metales preciosos oro plata platino paladio perlas '
        'piedras preciosas diamantes esmeraldas rubies bisuteria monedas',
    'Metals':
        'metal metales hierro acero cobre aluminio niquel plomo zinc estano cermet '
        'fundicion forja metalurgia herramientas cuchilleria griferia cerradura '
        'caja fuerte valvula',
    'Machines':
        'maquinaria maquina mecanico electrico electronico computador ordenador '
        'hardware motor turbina bomba compresor ventilador calefaccion horno '
        'refrigeracion lavadora secadora generador transformador bateria cable '
        'reactor nuclear caldera',
    'Transportation':
        'vehiculo automovil automotriz camion autobus ferrocarril locomotora tren '
        'aeronave avion helicoptero barco bote buque naviero motocicleta bicicleta '
        'remolque semirremolque',
    'Instruments':
        'instrumento optico fotografico cinematografico medico quirurgico '
        'medicion control precision cientifico reloj relojeria musical partitura',
    'Weapons':
        'arma armas municion municiones belico guerrero defensa militar',
    'Miscellaneus':
        'mueble muebles mobiliario colchon colchones almohada almohadas iluminacion '
        'lampara lamparas juguete juegos deporte deportivo articulos manufacturados '
        'brocha escoba cepillo cierre cremallera boton lapiz boligrafo',
    'Art and Antiques':
        'obra arte obras artistico antiguedad antiguedades coleccion pintura '
        'escultura cuadro grabado dibujo',
    'Unspecified': 'plantas industriales clasificacion otros',
}

# 1. Cargar CATEGORIA_HS y armar textos por seccion
df_hs = pd.read_excel(DICCIONARIO_PATH, sheet_name='CATEGORIA_HS')
df_hs.columns = df_hs.columns.str.strip()

sections_sorted = sorted(df_hs['Section'].unique())
section_corpus = []
for s in sections_sorted:
    descs = ' '.join(df_hs[df_hs['Section'] == s]['HS Description'].tolist())
    kws = SPANISH_KWS.get(s, '')
    section_corpus.append(f'{descs} {kws}')

# 2. TF-IDF character n-grams
vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 5), max_features=5000,
                             sublinear_tf=True)
section_vecs = vectorizer.fit_transform(section_corpus)

# 3. Cargar actividades
con = duckdb.connect()
actecos_path = os.path.join(SII_DIR, 'actecos.parquet')
df_acts = con.execute(
    "SELECT DISTINCT DESC_ACTIVIDAD_ECONOMICA FROM read_parquet(?) ORDER BY 1",
    [actecos_path]
).fetchdf()

# 4. Matchear
mapeo = []
for _, row in df_acts.iterrows():
    act = row['DESC_ACTIVIDAD_ECONOMICA']
    act_vec = vectorizer.transform([act])
    sims = cosine_similarity(act_vec, section_vecs)[0]
    best_idx = sims.argmax()
    best_score = sims[best_idx]

    # Umbral: si score < 0.2 va a Unspecified
    if best_score >= 0.2:
        mapeo.append({
            'ACTIVIDAD': act,
            'SECTION': sections_sorted[best_idx],
            'SCORE': round(best_score, 3)
        })
    else:
        # Revisar si destaca sobre el segundo mejor
        sorted_sims = np.sort(sims)[::-1]
        if len(sorted_sims) > 1 and best_score / (sorted_sims[1] + 0.001) > 1.5:
            mapeo.append({
                'ACTIVIDAD': act,
                'SECTION': sections_sorted[best_idx],
                'SCORE': round(best_score, 3)
            })
        else:
            mapeo.append({
                'ACTIVIDAD': act,
                'SECTION': 'Unspecified',
                'SCORE': round(best_score, 3)
            })

# 5. Guardar
df_out = pd.DataFrame(mapeo)
df_out = df_out.drop_duplicates(subset=['ACTIVIDAD', 'SECTION'])
df_out = df_out.sort_values(['SECTION', 'SCORE'], ascending=[True, False])
df_out.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')

# 6. Estadisticas
print(f'Mapeo generado: {len(df_out)} entradas')
print(f'Distribución por sección:')
spec_cnt = 0
for sect in sorted(df_out['SECTION'].unique()):
    cnt = len(df_out[df_out['SECTION'] == sect])
    print(f'  {sect}: {cnt} actividades')
    if sect == 'Unspecified':
        spec_cnt = cnt
print(f'\nMapeadas: {len(df_out) - spec_cnt} / {len(df_acts)} ({100*(len(df_out)-spec_cnt)/len(df_acts):.0f}%)')

# 7. Mostrar ejemplos por seccion
print('\n--- Ejemplos por seccion ---')
for sect in sorted(df_out['SECTION'].unique()):
    if sect == 'Unspecified':
        continue
    muestra = df_out[df_out['SECTION'] == sect].head(3)
    for _, r in muestra.iterrows():
        print(f'  [{sect:35s}] {r["ACTIVIDAD"][:65]:65s} ({r["SCORE"]})')

con.close()
