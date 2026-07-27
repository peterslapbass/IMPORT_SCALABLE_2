import requests
import pandas as pd
from bs4 import BeautifulSoup
import os, shutil
from collections import OrderedDict

os.chdir(os.path.dirname(os.path.abspath(__file__)))

URL = 'http://comext.aduana.cl:7001/codigos/buscar.do'

DICCIONARIOS = OrderedDict([
    (2,  'BANCOS_COMERCIALES'),
    (3,  'CLAUSULA_COMPRA_VENTA'),
    (5,  'ARTICULOS_DENUNCIAS'),
    (7,  'FORMAS_PAGOS'),
    (8,  'FORMAS_PAGO_GRAVAMEN'),
    (9,  'MONEDAS'),
    (12, 'REGIONES'),
    (14, 'TIPOS_CUENTAS'),
    (17, 'UNIDAD_MEDIDA'),
    (19, 'ORIGEN_DIVISAS'),
    (20, 'VISTOS_BUENOS'),
    (21, 'REGIMEN_IMPORTACION'),
    (22, 'CLAVES_ECONOMICAS_IMPORTA'),
    (23, 'ZONAS_ECONOMICAS'),
    (24, 'CLAVES_ECONOMICAS_EXPORTAC'),
])

def fetch_diccionario(opcion):
    resp = requests.get(URL, params={'opcion': f'{opcion:02d}'}, timeout=30)
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')
    rows = soup.select('table tr.tablaItem, table tr.tablaItemSuave')
    data = []
    for tr in rows:
        tds = tr.find_all('td')
        if len(tds) >= 2:
            codigo = tds[0].get_text(strip=True)
            glosa  = tds[1].get_text(strip=True)
            data.append((codigo, glosa))
    return data

def main():
    dst = os.path.join('..', 'data', 'DICCIONARIO.xlsx')

    # Backup
    backup = dst + '.bak'
    if os.path.exists(dst) and not os.path.exists(backup):
        shutil.copy2(dst, backup)
        print(f"Backup -> {backup}")

    # Read all existing sheets
    existing = OrderedDict()
    if os.path.exists(dst):
        xls = pd.ExcelFile(dst)
        for sheet in xls.sheet_names:
            existing[sheet] = xls.parse(sheet)
        print(f"Existing sheets: {', '.join(existing.keys())}")

    # Add new sheets
    added = 0
    skipped = 0
    for opcion, sheet_name in DICCIONARIOS.items():
        if sheet_name in existing:
            print(f"  SKIP {sheet_name} (already exists)")
            skipped += 1
            continue
        print(f"  Fetching opcion={opcion:02d} -> {sheet_name} ...", end=' ')
        data = fetch_diccionario(opcion)
        if not data:
            print("EMPTY")
            continue
        df = pd.DataFrame(data, columns=['Código', 'Glosa'])
        existing[sheet_name] = df
        print(f"{len(df)} rows")
        added += 1

    if added == 0:
        print("\nNothing new to add.")
        return

    # Write everything back
    with pd.ExcelWriter(dst, engine='openpyxl') as writer:
        for sheet_name, df in existing.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"\nDone! Added {added} new sheet(s), skipped {skipped}.")

if __name__ == '__main__':
    main()
