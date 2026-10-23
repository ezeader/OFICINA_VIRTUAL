"""Build Estructura and Climatizacion manifests from the R4 read-only inventories.

Inputs (openings-r4/): inventory-structure.json, inventory-hvac.json, inventory-hvac-detail.json
Outputs: <public>/structure/manifest.json and <public>/climatizacion/manifest.json
No Revit access; nothing in the model is changed.
"""
import argparse, collections, json, re
from pathlib import Path

ROOT = Path(__file__).parent; INV = ROOT / 'openings-r4'
LEVEL_CODE = {'00. Planta Baja': 'PB', '01. Planta Alta': 'PA', '02. Planta Entrepiso': 'PE', '03. Planta de Techos': 'PT', '005. Acceso ppal': 'AC'}


def dec(v):
    if isinstance(v, str): return re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), v)
    if isinstance(v, list): return [dec(x) for x in v]
    if isinstance(v, dict): return {k: dec(x) for k, x in v.items()}
    return v


def read(n): return dec(json.loads((INV / n).read_text(encoding='utf-8-sig')))
def r3(x): return round(x, 3) if isinstance(x, (int, float)) else x
def save(p, v): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding='utf8')


def group(rows, key, fields=('area_m2', 'volume_m3', 'length_m')):
    out = collections.OrderedDict()
    for r in rows:
        k = key(r); s = out.setdefault(k, {'count': 0, **{f: 0. for f in fields}})
        s['count'] += 1
        for f in fields: s[f] += r.get(f) or 0
    return [{'key': k, **{f: r3(v) for f, v in s.items()}} for k, s in out.items()]


def structure(s):
    MH = 'Muro Hormigón 20cm'
    walls = [w for w in s['walls'] if w['type'] == MH]
    by_level = collections.defaultdict(list)
    for w in sorted(walls, key=lambda w: (w['level'], w['bbox']['min'][1] if w['bbox'] else 0, w['bbox']['min'][0] if w['bbox'] else 0)):
        by_level[w['level']].append(w)
    elements = []
    for lev, rows in by_level.items():
        for i, w in enumerate(rows, 1):
            elements.append({'id': str(w['id']), 'code': f"MH-{LEVEL_CODE.get(lev, 'XX')}-{i:02d}", 'category': 'Walls', 'type': w['type'], 'level': lev,
                             'length_m': r3(w.get('length_m')), 'height_m': r3(w.get('height_m')), 'thickness_m': r3(w.get('width_m')),
                             'area_m2': r3(w.get('area_m2')), 'volume_m3': r3(w.get('volume_m3')), 'topConstraint': w.get('topConstraint'),
                             'baseOffset_m': r3(w.get('baseOffset_m')), 'structuralFlag': w.get('structural'), 'mark': w.get('mark'),
                             'materials': [m['name'] for m in w.get('materials', [])]})
    related_types = ['Viga de encadenado invertida', 'VIGA encuentro 2 techos, revestimiento fachada', 'Muro Fachada eje', 'Muro Fachada ppal', 'Bajo Escalera', 'Muro Pileta', 'Muro Interior 20cm']
    other_walls = group([w for w in s['walls'] if w['type'] in related_types], lambda w: w['type'] + ' | ' + w['level'])
    def has_concrete(t): return any(re.search('hormig|concrete', l['material'], re.I) for l in s['floorTypes'].get(t, {}).get('layers', []))
    slab_like = [f for f in s['floors'] if re.search('platea|insitu|losa|base acceso|L\\d\\d\\.\\d\\d', f['type'], re.I)]
    floors = []
    for f in slab_like:
        layers = s['floorTypes'].get(f['type'], {}).get('layers', [])
        conc = sum(l['thickness_m'] for l in layers if re.search('hormig|concrete', l['material'], re.I))
        role = 'Fundación (platea)' if 'Platea' in f['type'] else 'Losa / estructura' if (conc or 'Insitu' in f['type'] or 'Base' in f['type']) else 'Paquete de piso (sin capa de hormigón)'
        floors.append({'id': str(f['id']), 'type': f['type'], 'level': f['level'], 'role': role, 'area_m2': r3(f['area_m2']), 'volume_m3': r3(f['volume_m3']),
                       'thickness_m': r3(f.get('thickness_m')), 'concreteLayer_m': r3(conc), 'concreteVolume_m3': r3((f['area_m2'] or 0) * conc) if conc else None,
                       'structuralFlag': f.get('structural'), 'layers': [{**l, 'thickness_m': r3(l['thickness_m'])} for l in layers]})
    mh_ids = {int(e['id']) for e in elements}
    struct_ids = mh_ids | {int(f['id']) for f in floors}
    warns = [w for w in s['warnings'] if set(w['elementIds']) & struct_ids]
    wcount = collections.Counter(w['text'] for w in warns)
    overlaps = [w for w in warns if 'overlap' in w['text'] or 'joined but do not' in w['text']]
    attach = [w for w in warns if 'attached to, but miss' in w['text']]
    code_of = {int(e['id']): e['code'] for e in elements}
    cases = [{
        'id': 'estructura-ascensor-364138', 'title': 'Ascensor · cerramiento vidriado sobre muro de hormigón',
        'elementIds': ['364138', '1020586', '1020050'], 'codes': [code_of.get(364138, '364138'), 'MC-1020586', 'MC-1020050'],
        'observation': 'Caso ya documentado en Aberturas R3: el muro cortina MC-1020586 se solapa con el muro de hormigón 364138 y hay un segundo conjunto (MC-1020050) a 2 cm. No se tocó (pedido del usuario).',
        'proposedCorrection': 'Definir con estructura si el vano del ascensor es un hueco en el tabique de hormigón (recorte del muro) o un cerramiento exterior al hormigón; recién entonces ajustar el modelo.',
        'status': 'pending', 'blockedBy': 'Usuario: no modificar el caso ascensor por ahora.'}]
    for i, w in enumerate(overlaps, 1):
        ids = [str(x) for x in w['elementIds']]
        cases.append({'id': f'estructura-solape-{i:02d}', 'title': 'Solape / unión inconsistente en elementos estructurales',
                      'elementIds': ids, 'codes': [code_of.get(int(x), x) for x in ids], 'observation': w['text'],
                      'proposedCorrection': 'Revisar en planta y corte: unir o recortar (Cut/Join Geometry) solo después de validar cuál elemento manda; no se corrigió automáticamente.', 'status': 'pending'})
    by_level = group(elements, lambda e: e['level'])
    total_slab = sum(f['concreteVolume_m3'] or 0 for f in floors if f['role'] != 'Paquete de piso (sin capa de hormigón)') + sum(f['volume_m3'] or 0 for f in floors if f['role'] != 'Paquete de piso (sin capa de hormigón)' and not f['concreteLayer_m'])
    return {
        'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': s['readAt'], 'revision': 'R4-inventario', 'status': 'Inventario de solo lectura + propuesta (sin láminas generadas)',
        'levels': [{**l, 'elevation_m': r3(l['elevation_m'])} for l in s['levels']], 'grids': sorted(s['grids'], key=lambda g: (g.isdigit(), int(g) if g.isdigit() else 0, g)),
        'nativeSchedule': {'id': '1168184', 'name': 'Muros Estructura de Hormigón', 'rows': 43, 'matchesInventory': len(elements) == 43},
        'concreteWalls': {'type': MH, 'count': len(elements), 'byLevel': by_level,
                          'totals': {'length_m': r3(sum(e['length_m'] or 0 for e in elements)), 'area_m2': r3(sum(e['area_m2'] or 0 for e in elements)), 'volume_m3': r3(sum(e['volume_m3'] or 0 for e in elements))},
                          'elements': elements},
        'otherStructuralWalls': other_walls,
        'slabsAndFoundations': floors,
        'slabSummary': group(floors, lambda f: f['level'] + ' | ' + f['role']),
        'framing': {'note': 'Solo vigas y correas de madera de cubierta (familia Kerto LVL). No hay vigas de hormigón modeladas como Structural Framing.', 'byType': [{**r, **{k: r3(v) for k, v in r.items() if isinstance(v, float)}} for r in s['summary']['framingByType']]},
        'columns': {'structural': 0, 'architectural': [{'id': str(c['id']), 'family': c['family'], 'type': c['type'], 'volume_m3': r3(c.get('volume_m3'))} for c in s['architecturalColumns']]},
        'roofs': group(s['roofs'], lambda r: r['type'] + ' | ' + r['level']),
        'notModeled': [
            'Fundaciones (categoría Structural Foundations vacía): solo la platea PB modelada como piso "Platea PB 15CM".',
            'Armaduras (Rebar = 0): cuantías y despiece de hierro no están en el modelo.',
            'Columnas estructurales (0) y vigas de hormigón (0 como Structural Framing): los encadenados están modelados como muros ("Viga de encadenado invertida", "VIGA encuentro...").',
            'Losas de PA/PE: los tipos L01.00 / L01.02 / L04.01 / L07.01 son paquetes de piso sin capa de hormigón; solo L01.01 / 30cm incluye 15 cm de hormigón. Falta modelar o confirmar la losa estructural de esos sectores.',
            'Niveles no marcados como estructurales (Structural = No en los 5 niveles); no hay niveles de fundación ni de losa (cota de hormigón vs. piso terminado).',
            'Parámetro "Structural" de los 43 muros de hormigón desactivado: Revit no los trata como estructura (no aparecen en vistas/planillas estructurales).',
        ],
        'warnings': {'total': len(warns), 'byText': [{'text': k, 'count': v} for k, v in wcount.most_common()], 'attachedButMiss': len(attach)},
        'reviewCases': cases,
        'proposal': {
            'numbering': 'MH-<nivel>-<nn> para muros de hormigón (MH-PB-01…), LO-<nivel>-<nn> losas, PL-01 platea, VE-<nivel>-<nn> vigas/encadenados, CO-<nn> columnas. Código guardado en Mark (parámetro de identidad), igual que V-/P-/MC- en Aberturas.',
            'sheets': [
                {'number': 'EST-00', 'title': 'Índice, criterios y planilla general de hormigón (muros, losas, platea) con volúmenes'},
                {'number': 'EST-PB-01', 'title': 'Planta de estructura PB · muros MH-PB con códigos, ejes A–H / 1–10 y cotas a ejes'},
                {'number': 'EST-PA-01', 'title': 'Planta de estructura PA · muros MH-PA y losas LO-PA'},
                {'number': 'EST-PE-01', 'title': 'Planta de estructura PE · muros MH-PE y losas LO-PE'},
                {'number': 'EST-FU-01', 'title': 'Platea PB 15 cm · contorno, espesor, niveles (cuando se defina fundación)'},
                {'number': 'EST-SEC-nn', 'title': 'Sectores (Cuartos inv., Hall/Acceso, Quincho, Núcleo ascensor/escalera): alzados de muros con aberturas y pases, cotas de vanos (vinculadas con Aberturas R4)'},
                {'number': 'EST-REV-nn', 'title': 'Casos de revisión: solapes y uniones (como el del ascensor) con contexto planta + axonometría'},
            ],
            'quantities': 'Planilla nativa por código: longitud, alto, espesor, área y volumen de hormigón; losas por capa de hormigón (área × espesor de capa); platea por volumen. Totales por nivel y por sector.',
            'webData': 'structure/manifest.json: concreteWalls.elements (con code propuesto), slabsAndFoundations, reviewCases y proposal.sheets; las láminas se agregarán con image/pdf como en openings/manifest.json.',
        },
        'openQuestions': [
            '¿Las losas de PA y PE son de hormigón armado? Hoy figuran solo como paquetes de piso (salvo L01.01 / 30cm).',
            '¿Hay fundaciones además de la platea (vigas de fundación, pilotes, zapatas)?',
            '¿Activamos el parámetro Structural en los 43 muros de hormigón y marcamos niveles estructurales? Es un cambio de parámetros del modelo (no documentación): requiere su OK.',
            '¿Confirmamos la numeración MH-/LO-/PL-/VE- y que se escriba en Mark?',
        ],
    }


def climatizacion(h, d):
    rooms = {r['id']: r for r in d['rooms']}
    pex = [p for p in d['pipes'] if 'Hidroflex' in p['type'] or 'PEX' in p['type']]
    horiz = [p for p in pex if abs(p['a'][2] - p['b'][2]) < .01]
    vert = [p for p in pex if abs(p['a'][2] - p['b'][2]) >= .01]
    acc = d['accessories']
    colectores = [a for a in acc if 'Colector' in a['family']]
    def room_of(rid): return rooms.get(rid)
    per = collections.OrderedDict()
    def same_level(p):
        r = room_of(p['room'])
        return r if r and r['level'] == p['level'] else None   # ignore rooms found on another level
    for p in sorted(horiz, key=lambda p: (p['level'], (same_level(p) or {}).get('name', 'zzz'))):
        r = same_level(p)
        key = (p['level'], r['name'] if r else '(fuera de local)')
        s = per.setdefault(key, {'level': p['level'], 'room': r['name'] if r else None, 'roomId': str(r['id']) if r else None,
                                 'roomArea_m2': r3(r['area_m2']) if r else None, 'supply_m': 0., 'return_m': 0., 'segments': 0, 'systems': set()})
        s['supply_m' if 'Mando' in p['type'] else 'return_m'] += p['length_m']; s['segments'] += 1; s['systems'].add(p['systemName'])
    circuits = []
    for k, s in per.items():
        total = s['supply_m'] + s['return_m']
        circuits.append({**{x: y for x, y in s.items() if x != 'systems'}, 'systems': sorted(x for x in s['systems'] if x),
                         'supply_m': r3(s['supply_m']), 'return_m': r3(s['return_m']), 'total_m': r3(total),
                         'density_m_per_m2': r3(total / s['roomArea_m2']) if s['roomArea_m2'] else None,
                         'thermostat': any(a['room'] and s['roomId'] and str(a['room']) == s['roomId'] and 'termostato' in a['family'].lower() for a in acc)})
    tot = lambda rows, w: r3(sum(p['length_m'] for p in rows if w in p['type']))
    return {
        'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': d['readAt'], 'revision': 'R4-inventario', 'status': 'Inventario de solo lectura + propuesta (sin láminas nuevas)',
        'system': {'description': 'Piso radiante (losa radiante) con serpentines PEX embebidos en la carpeta, alimentado por bomba de calor inverter aire-agua (frío/calor).',
                   'modeledAs': 'Tuberías Hidroflex PEX Ø20 (tipos "CAL - Mando - Rollo 400" y "CAL - Retorno - Rollo 200"), colectores Hidroflex LUXUS con gabinete, cronotermostatos inalámbricos y "Reticulado" (piezas de soporte/malla).'},
        'pipes': {'pex': {'segments': len(pex), 'supply_m': tot(pex, 'Mando'), 'return_m': tot(pex, 'Retorno'), 'total_m': r3(sum(p['length_m'] for p in pex)),
                          'horizontal_m': r3(sum(p['length_m'] for p in horiz)), 'vertical_m': r3(sum(p['length_m'] for p in vert)),
                          'diameters_mm': sorted({round(p['diameter_mm'], 1) for p in pex if p['diameter_mm']}),
                          'pipingSystems': [{'name': k, 'segments': v} for k, v in collections.Counter(p['systemName'] for p in pex).most_common()],
                          'byLevel': group([{**p} for p in pex], lambda p: p['level'] + ' | ' + ('Mando' if 'Mando' in p['type'] else 'Retorno'), fields=('length_m',))},
                  'hydronicPpr': group([p for p in d['pipes'] if p not in pex], lambda p: p['type'] + ' | ' + (p['system'] or ''), fields=('length_m',))},
        'manifolds': [{'id': str(a['id']), 'family': a['family'], 'type': a['type'], 'level': a['level'], 'room': (room_of(a['room']) or {}).get('name'),
                       'name': 'Colector Norte' if 'Entrepiso' in (a['level'] or '') or (room_of(a['room']) or {}).get('name') == 'SM' else 'Colector Sur'} for a in colectores],
        'cabinets': [{'id': str(a['id']), 'type': a['type'], 'room': (room_of(a['room']) or {}).get('name')} for a in acc if 'Gabinete' in a['family']],
        'thermostats': [{'id': str(a['id']), 'room': (room_of(a['room']) or {}).get('name'), 'level': a['level']} for a in acc if 'termostato' in a['family'].lower()],
        'mechanicalEquipment': [{'id': str(a['id']), 'family': a['family'], 'type': a['type'], 'level': a['level'], 'note': 'Bomba centrífuga genérica (tipo sin catálogo); no es la bomba de calor.'} for a in acc if a['category'] == 'Mechanical Equipment'],
        'circuitsByRoom': circuits,
        'floorBuildUp': [{'type': f['name'], 'layers': [{**l, 'thickness_m': r3(l['thickness_m'])} for l in f['layers']]} for f in h['floorTypesMatching'] if f['match'] and f['name'].startswith('L')],
        'existingDocumentation': {'sheets': d['sheets'], 'views': d['views']},
        'notModeled': [
            'Bomba de calor inverter aire-agua (unidad exterior / hidrokit): no hay equipo en el modelo. Solo existe una bomba centrífuga Grundfos genérica en PB sin tipo de catálogo.',
            'Separación de circuitos: los serpentines están en solo 4 sistemas de tubería (Hydronic Supply 1/3/13/19); no hay un sistema ni un código por circuito/local, ni vínculo con la salida del colector.',
            'Retorno clasificado como "Hydronic Supply": las tuberías "CAL - Retorno" usan el sistema de impulsión; falta el sistema Hydronic Return.',
            'Espacios MEP y zonas HVAC: 0 espacios y solo la zona Default; no hay cargas térmicas ni caudales por local.',
            'Capa de piso radiante: los tipos de piso tienen carpeta 2,5 cm + EPS pero no una capa específica de serpentín / panel radiante; el espesor de carpeta sobre tubo no está verificado.',
            'Tanque de inercia, vaso de expansión, válvula mezcladora, aislación de montantes y control (cabezales electrotérmicos instanciados = 0; la familia está cargada).',
            'Refrescamiento: no hay datos de punto de rocío / control de condensación para el modo frío.',
        ],
        'quantityTakeoff': {
            'structure': 'Por colector → circuito (salida) → local: longitud de mando + retorno, área servida, densidad m/m² (≈6,7 m/m² para paso 15 cm), largo máximo por circuito (≤100–120 m con Ø20), cabezal y termostato asociados.',
            'perRoomCurrent': 'circuitsByRoom (longitud horizontal por local según IsPointInRoom en el nivel de cada tramo). Densidades bajas (<4 m/m²) indican circuitos incompletos o solo distribución.',
            'totals': ['Tubo PEX Ø20 en rollos (mando 400 m / retorno 200 m según tipos)', 'Colectores por cantidad de salidas', 'Gabinetes', 'Cabezales electrotérmicos', 'Termostatos', 'Placa EPS / film / zócalo perimetral (m² y ml por local)', 'Carpeta (m³ por local)'],
        },
        'proposal': {
            'numbering': 'CR-<colector>-<nn> por circuito (CR-N-01… Colector Norte; CR-S-01… Colector Sur), escrito en Mark o Comments de cada tramo y en un sistema de tubería por circuito.',
            'sheets': [
                {'number': 'CLI-00', 'title': 'Esquema de principio: bomba de calor inverter, inercia, colectores Norte/Sur, circuitos y control'},
                {'number': 'CLI-PB-01', 'title': 'Planta PB · serpentines por local con código de circuito, longitud y paso'},
                {'number': 'CLI-PA-01', 'title': 'Planta PA · ídem'},
                {'number': 'CLI-PE-01', 'title': 'Planta PE · ídem'},
                {'number': 'CLI-COL-N / CLI-COL-S', 'title': 'Colectores: vista frontal, salidas numeradas, planilla de circuitos (local, m, caudal) (hoy existen CAL.0202 y CAL.0101)'},
                {'number': 'CLI-DET-01', 'title': 'Detalle de paquete de piso: platea/losa, EPS, film, tubo, carpeta, terminación; zócalo perimetral y juntas'},
                {'number': 'CLI-REV-nn', 'title': 'Casos de revisión (retorno mal clasificado, circuitos sin local, densidades bajas, falta bomba de calor)'},
            ],
            'reuse': 'Partir de las láminas CAL existentes (CAL. 00/01/02, CAL.0001/0002/0007/0101/0103/0201/0202) en vez de duplicarlas.',
        },
        'openQuestions': [
            '¿Marca/modelo y potencia de la bomba de calor inverter? ¿Ubicación de la unidad exterior y del hidrokit/tanque?',
            '¿Paso de serpentín y temperatura de diseño (calefacción / refrescamiento)? ¿Hay control de punto de rocío?',
            '¿Corrijo el sistema de los tramos de retorno a "Hydronic Return" y creo un sistema por circuito? Son cambios de parámetros MEP del modelo (no solo documentación): requiere su OK.',
            '¿Los cuartos de invitados tienen circuitos completos? Las densidades modeladas (~2,3 m/m²) sugieren que solo está el trazado parcial.',
        ],
    }


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); a = ap.parse_args()
    s = structure(read('inventory-structure.json')); save(a.public_dir / 'structure' / 'manifest.json', s)
    c = climatizacion(read('inventory-hvac.json'), read('inventory-hvac-detail.json')); save(a.public_dir / 'climatizacion' / 'manifest.json', c)
    print(json.dumps({'concreteWalls': s['concreteWalls']['count'], 'mhTotals': s['concreteWalls']['totals'], 'slabs': len(s['slabsAndFoundations']),
                      'structureCases': len(s['reviewCases']), 'pex': c['pipes']['pex']['total_m'], 'circuitRows': len(c['circuitsByRoom'])}, ensure_ascii=False))


if __name__ == '__main__': main()
