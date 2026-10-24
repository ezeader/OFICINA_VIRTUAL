"""R25: data-only manifests for rubros still to define (no sheets): revestimientos, parrilla, electrica, gas, domotica, solar.
public/casa-angel/rubros/<clave>/manifest.json (web contract lib/rubros.ts; all fields optional, sheets = [])."""
import argparse, json, math, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT))
from publish_openings_r4 import read

MODEL = 'Casa-Angel-piloto-documentacion.rvt'


def c2(v): return ('%.2f' % v).replace('.', ',')


def clean(s):
    return s.encode('latin-1', 'backslashreplace').decode('unicode_escape') if isinstance(s, str) and '\\x' in s else s


def base(title, summary, read_at, **kw):
    m = {'title': title, 'summary': summary, 'model': MODEL, 'readAt': read_at, 'revision': 'R25', 'kinds': {}, 'sheets': [], 'codes': [], 'totals': [], 'quantities': []}
    m.update(kw); return m


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); a = ap.parse_args()
    d = read(OUT / 'pend-data.json'); at = d['readAt']
    rooms = [dict(r, name=clean(r['name']), level=clean(r['level'])) for r in d['rooms']]
    items = {int(i['id']): i for i in d['items']}
    inv = {x['key']: x for x in json.loads((a.public_dir / 'rubros-inventario.json').read_text(encoding='utf-8'))['rubros']}
    eq = json.loads((a.public_dir / 'rubros' / 'equipamiento' / 'manifest.json').read_text(encoding='utf-8'))
    cub = json.loads((a.public_dir / 'rubros' / 'cubierta' / 'manifest.json').read_text(encoding='utf-8'))
    lv = lambda r: r['level'][:2] == '00' and 'PB' or (r['level'][:2] == '01' and 'PA' or 'PE')
    rl = lambda r: f"{r['number']} · {r['name']} · {lv(r)}"
    out = {}

    # ---------------- Revestimientos
    wet = [r for r in rooms if any(k in r['name'] for k in ('Baño', 'Toilette'))]
    kitchen = [r for r in rooms if r['name'].split(' ')[0] in ('Cocina', 'Lavadero')]
    ml = {'Cocina': sum(c['width_m'] for c in eq['codes'] if c['kind'] == 'ME' and 'Cocina' in (c.get('room') or '') and 'Quincho' not in (c.get('room') or '')),
          'Lavadero': sum(c['width_m'] for c in eq['codes'] if c['kind'] == 'LV')}
    H_WET, H_BAND, H_PAINT = 2.40, 0.60, 2.60
    q = [{'label': rl(r), 'group': 'Baños y toilettes (estimado h 2,40)', 'count': 1, 'value': round(r['perimeter_m'] * H_WET, 2), 'unit': 'm²', 'detail': f"perímetro {c2(r['perimeter_m'])} × 2,40 · sin descontar vanos"} for r in wet]
    q += [{'label': rl(r), 'group': 'Cocina y lavadero (franja sobre mesada h 0,60)', 'count': 1, 'value': round(ml[r['name'].split(' ')[0]] * H_BAND, 2), 'unit': 'm²', 'detail': f"{c2(ml[r['name'].split(' ')[0]])} ml de mesada/lavadero × 0,60"} for r in kitchen]
    dry = [r for r in rooms if r not in wet and 'Ascensor' not in r['name']]
    q += [{'label': rl(r), 'group': 'Pintura de muros (estimado h 2,60)', 'count': 1, 'value': round(r['perimeter_m'] * min(H_PAINT, r['height_m']), 2), 'unit': 'm²', 'detail': f"perímetro {c2(r['perimeter_m'])} × {c2(min(H_PAINT, r['height_m']))} · sin descontar vanos"} for r in dry]
    mats = inv['revestimientos']['quantities']['materiales_en_muros_m2']
    q += [{'label': clean(k), 'group': 'Materiales ya cargados en muros (Revit)', 'count': 1, 'value': round(v, 2), 'unit': 'm²', 'detail': 'área de capa en el modelo'} for k, v in mats.items()]
    tw = sum(x['value'] for x in q if x['group'].startswith('Baños')); tk = sum(x['value'] for x in q if x['group'].startswith('Cocina')); tp = sum(x['value'] for x in q if x['group'].startswith('Pintura'))
    out['revestimientos'] = base('Revestimientos', f"No hay revestimientos modelados. Estimación preliminar: {c2(tw)} m² en {len(wet)} baños/toilettes, {c2(tk)} m² en cocina y lavadero, {c2(tp)} m² de pintura de muros.", at,
        kinds={'RV': 'Revestimiento cerámico / porcelanato', 'PI': 'Pintura'},
        totals=[{'label': 'Baños y toilettes (h 2,40)', 'value': round(tw, 2), 'unit': 'm²', 'detail': f"{len(wet)} locales · sin descontar vanos"},
                {'label': 'Cocina y lavadero (franja 0,60)', 'value': round(tk, 2), 'unit': 'm²', 'detail': 'sobre mesadas y lavaderos (Equipamiento)'},
                {'label': 'Venecitas pileta (modelado)', 'value': round(mats.get('Venecitas', 0), 2), 'unit': 'm²', 'detail': 'ver Pileta'},
                {'label': 'Pintura de muros (estimado)', 'value': round(tp, 2), 'unit': 'm²', 'detail': f"{len(dry)} locales · h 2,60"}],
        quantities=q, quantityNote='Estimación preliminar con perímetro de local × altura supuesta, sin descontar vanos. Se reemplaza por cómputo real cuando se modelen las capas de terminación.',
        notModeled=['Cerámicos y porcelanatos de baños, toilettes, cocina y lavadero', 'Capas de terminación (Finish) en muros de mampostería', 'Revestimiento de fachada (hoy solo "Hormigón fachada" 8 cm)', 'Guardas, cantoneras, buñas y zócalos sanitarios'],
        decisions=['Rubro sin láminas hasta definir materiales y alturas.', 'Hipótesis recomendadas: baños revestidos hasta 2,40 m; cocina y lavadero solo franja de 0,60 m sobre mesada; resto pintado.'],
        questions=['¿Altura de revestimiento en baños: hasta 2,40 m (recomendado), hasta cielorraso o solo zona húmeda?', '¿Material y formato para baños (porcelanato 60×120, cerámico, microcemento)?',
                   '¿Cocina y lavadero: franja de 0,60 m sobre mesada (recomendado) o pared completa?', '¿La fachada lleva revestimiento además del hormigón visto?', '¿Modelamos las capas de terminación en los muros (cambia el modelo, requiere tu OK)?'])

    # ---------------- Parrilla
    p = items.get(743956); ducts = [items[i] for i in (738025, 745388) if i in items]
    codes = [{'code': 'PR-01', 'kind': 'PR', 'label': 'PR-01 · parrilla K42DB', 'status': 'Familia "Parrilla" (Quincho, PB)', 'elementId': '743956', 'type': 'Parrilla K42DB'}]
    codes += [{'code': f'CH-{k:02d}', 'kind': 'CH', 'label': f"CH-{k:02d} · conducto Ø {c2(x['diameter_m'] * 100).replace(',00', '')} cm · {c2(x['length_m'])} ml", 'status': 'Conducto redondo "Parrilla"', 'elementId': str(x['id']), 'length_m': round(x['length_m'], 3)} for k, x in enumerate(ducts, 1)]
    out['parrilla'] = base('Parrilla', f"Modelada solo como equipo: parrilla K42DB en el Quincho y {len(ducts)} conductos Ø 25 cm ({c2(sum(x['length_m'] for x in ducts))} ml). Falta diseñar fogonero, campana y remate.", at,
        kinds={'PR': 'Parrilla', 'CH': 'Conducto de humos'}, codes=codes,
        totals=[{'label': 'Conductos de humo', 'value': round(sum(x['length_m'] for x in ducts), 2), 'unit': 'ml', 'detail': 'Ø 25 cm · 2 tramos'}, {'label': 'Parrilla', 'value': 1, 'unit': 'u', 'detail': 'K42DB · 2,06 × 0,77'}],
        quantities=[{'label': c['label'], 'group': 'Parrilla', 'count': 1, 'value': c.get('length_m', 1), 'unit': 'ml' if 'length_m' in c else 'u', 'detail': c['status']} for c in codes],
        notModeled=['Fogonero / brasero y parrilla regulable', 'Campana y revestimiento refractario', 'Conducto completo hasta cubierta y sombrerete', 'Mesada de apoyo y leñero'],
        decisions=['Rubro sin láminas: hay que diseñar la parrilla antes de documentarla.'],
        questions=['¿Parrilla de obra a medida (recomendado) o equipo prefabricado como el K42DB?', '¿Ancho de boca y alto de campana? Propuesta: boca 1,50 m, campana hasta cielorraso.', '¿Revestimiento exterior: ladrillo refractario visto, acero o revoque?', '¿El conducto sale por cubierta (atraviesa CU) o por muro? ¿Con sombrerete giratorio?'])

    # ---------------- Eléctrica
    t = items.get(2403792); dw = [i for i in items.values() if i['cat'] == 'ElectricalFixtures']
    qe = []
    for r in sorted(rooms, key=lambda r: (r['level'], r['number'])):
        if 'Ascensor' in r['name']: continue
        il = max(1, math.ceil(r['area_m2'] / 12)); to = max(1 if any(k in r['name'] for k in ('Baño', 'Toilette', 'Puente', 'Vestidor')) else 2, math.ceil(r['perimeter_m'] / 6))
        qe.append({'label': rl(r), 'group': f"Propuesta de bocas · {r['level']}", 'count': il + to, 'value': il + to, 'unit': 'bocas', 'detail': f"{il} iluminación + {to} tomas (estimado por superficie y perímetro)"})
    out['electrica'] = base('Eléctrica', f"Sin instalación eléctrica modelada: solo el tablero ABB (PE). Propuesta preliminar: {sum(x['value'] for x in qe)} bocas en {len(qe)} locales, a validar con el proyecto eléctrico.", at,
        kinds={'TG': 'Tablero', 'BO': 'Bocas'},
        codes=[{'code': 'TG-01', 'kind': 'TG', 'label': 'TG-01 · tablero ABB Protecta Compact EPB25-304C', 'status': 'Planta Entrepiso', 'elementId': '2403792', 'type': 'EPB25-304C'}],
        totals=[{'label': 'Tableros', 'value': 1, 'unit': 'u', 'detail': 'ABB EPB25-304C (PE)'}, {'label': 'Bocas (propuesta preliminar)', 'value': sum(x['value'] for x in qe), 'unit': 'bocas', 'detail': '1 iluminación cada 12 m² + 1 toma cada 6 m de perímetro'}],
        quantities=qe, quantityNote='Bocas estimadas por superficie y perímetro de cada local (no es el cálculo reglamentario). Se reemplaza por el proyecto eléctrico.',
        notModeled=['Bocas, tomas, llaves y luminarias', 'Cañerías, cajas y circuitos', 'Puesta a tierra, acometida y medidor', f"Las {len(dw)} \"Electrical Fixtures\" del modelo son lavavajillas mal categorizados"],
        decisions=['Rubro sin láminas hasta tener el proyecto eléctrico.'],
        questions=['¿Quién hace el proyecto eléctrico (instalador matriculado) y con qué grado de electrificación?', '¿Iluminación: embutidos LED en cielorrasos, apliques, o ambos? ¿Exterior y pileta?',
                   '¿Tablero general en PE (donde está el ABB) o en PB junto al acceso? ¿Seccionales por planta?', '¿Corregimos la categoría de los 3 lavavajillas en el modelo (cambio de modelo, requiere tu OK)?'])

    # ---------------- Gas
    cook = [c for c in eq['codes'] if c['kind'] == 'EQ' and 'cocina' in c['label']]
    out['gas'] = base('Gas', 'Sin red de gas modelada ni sistemas de cañería de gas en el modelo. Único artefacto que podría usar gas: la cocina dual fuel (EQ-02).', at,
        kinds={'GA': 'Artefactos a gas'},
        codes=[{'code': 'GA-01', 'kind': 'GA', 'label': 'GA-01 · cocina dual fuel (EQ-02)', 'status': 'Equipamiento · Cocina PA', 'elementId': cook[0]['elementId'] if cook else None}],
        totals=[{'label': 'Artefactos posibles a gas', 'value': 1, 'unit': 'u', 'detail': 'cocina dual fuel'}],
        notModeled=['Acometida, medidor y regulador (o zeppelin GLP)', 'Cañerías y llaves de paso', 'Ventilaciones reglamentarias de locales con artefactos', 'Caldera / termotanque (el piso radiante no tiene fuente modelada)'],
        decisions=['Rubro sin láminas hasta definir si hay gas.'],
        questions=['¿Hay gas natural en la calle o se usa GLP con zeppelin? ¿O la casa es todo eléctrica (recomendado si el piso radiante va con bomba de calor)?',
                   '¿Qué artefactos van a gas: cocina, caldera del piso radiante, termotanque, parrilla con encendido?', '¿Dónde iría el medidor / zeppelin (retiro sobre la calle CA-01)?'])

    # ---------------- Domótica
    out['domotica'] = base('Domótica', 'Sin elementos de domótica en el modelo. Base existente: 11 termostatos del piso radiante (Climatización) y 30 locales.', at,
        totals=[{'label': 'Locales a cubrir', 'value': len(rooms), 'unit': 'locales', 'detail': 'PB, PA y PE'}, {'label': 'Zonas de clima existentes', 'value': 11, 'unit': 'termostatos', 'detail': 'ver Climatización'}],
        quantities=[{'label': rl(r), 'group': f"Locales · {r['level']}", 'count': 1, 'value': round(r['area_m2'], 2), 'unit': 'm²', 'detail': 'sin dispositivos'} for r in sorted(rooms, key=lambda r: (r['level'], r['number']))],
        notModeled=['Central / controlador', 'Sensores, actuadores y teclados', 'Cableado de datos y Wi-Fi', 'Seguridad: alarma, cámaras, portero'],
        decisions=['Rubro sin láminas hasta definir el alcance.'],
        questions=['¿Qué se automatiza: iluminación, cortinas, clima por zona, riego, pileta, seguridad?', '¿Sistema cableado (KNX) o inalámbrico (Zigbee / Wi-Fi)? Recomendado: cableado si se define antes de la obra gruesa.',
                   '¿Integramos los 11 termostatos del piso radiante a la domótica?', '¿Dónde va el rack / central (Sala de máquinas PA)?'])

    # ---------------- Solar
    aguas = [(c['code'], x['slope_deg'], x['area_m2']) for c in cub['codes'] if c['kind'] == 'CU' for x in (c.get('aguas') or [])]
    big = [x for x in aguas if x[2] >= 15]
    out['solar'] = base('Paneles solares', f"Sin paneles ni familias en el modelo. Superficie de techo candidata: {len(big)} aguas de más de 15 m² ({c2(sum(x[2] for x in big))} m²); falta conocer su orientación.", at,
        totals=[{'label': 'Aguas candidatas (≥ 15 m²)', 'value': round(sum(x[2] for x in big), 2), 'unit': 'm²', 'detail': f"{len(big)} aguas · orientación a confirmar"}, {'label': 'Techo de tejas total', 'value': round(sum(x[2] for x in aguas), 2), 'unit': 'm²', 'detail': 'ver Cubierta'}],
        quantities=[{'label': f"{code} · agua {c2(s)}°", 'group': 'Aguas de cubierta', 'count': 1, 'value': round(ar, 2), 'unit': 'm²', 'detail': 'candidata' if ar >= 15 else 'chica'} for code, s, ar in aguas],
        notModeled=['Paneles, estructura de montaje e inversor', 'Cableado y tablero de continua', 'Colectores solares térmicos (agua caliente / pileta)'],
        decisions=['Rubro sin láminas hasta definir sistema y potencia.'],
        questions=['¿Fotovoltaico (electricidad), térmico (agua caliente / pileta) o ambos?', '¿Potencia o consumo objetivo? Propuesta: 5 kWp on-grid (≈ 25 m² de paneles).',
                   '¿Qué aguas miran al norte? El modelo no tiene orientación verdadera cargada.', '¿Paneles sobre tejas con estructura o integrados?'])

    for k, m in out.items():
        p = a.public_dir / 'rubros' / k; p.mkdir(parents=True, exist_ok=True)
        (p / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: (len(m['codes']), len(m['quantities']), len(m['questions'])) for k, m in out.items()}))


if __name__ == '__main__': main()
