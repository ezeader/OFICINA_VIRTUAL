"""Classify the R14 read-only raw inventory into trades (rubros) ordered by computability.
Output: <public>/casa-angel/rubros-inventario.json"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from build_survey_r9 import dec as _d


def dec(v):
    if isinstance(v, dict): return {_d(k): dec(x) for k, x in v.items()}
    if isinstance(v, list): return [dec(x) for x in v]
    return _d(v)


def r2(x): return round(x, 2)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); a = ap.parse_args()
    raw = dec(json.loads((ROOT / 'openings-r4' / 'rubros-raw.json').read_text(encoding='utf-8-sig')))
    cat = raw['categories']
    def rows(c, pred=lambda k: True):
        return {k: v for k, v in cat.get(c, {}).get('byType', {}).items() if pred(k)}
    def summ(rs, unit_keys=('count', 'area_m2', 'volume_m3', 'length_m')):
        out = {k: 0 for k in unit_keys}
        for v in rs.values():
            for k in unit_keys: out[k] += v[k]
        return {k: (r2(v) if isinstance(v, float) else v) for k, v in out.items()}
    def types(rs): return [{'type': k, 'count': v['count'], 'area_m2': r2(v['area_m2']), 'volume_m3': r2(v['volume_m3']), 'length_m': r2(v['length_m'])} for k, v in sorted(rs.items())]
    def has(k, *w): return any(x.lower() in k.lower() for x in w)

    alb = rows('OST_Walls', lambda k: has(k, 'Muro Interior', 'Blockwork', 'Bajo Escalera', 'Fachada eje', 'Fachada ppal', 'W111', 'W112', 'Durlock Chimenea', 'Cierre Cielorraso'))
    pisos = rows('OST_Floors', lambda k: has(k, 'L01.00', 'L02.00', 'L03.00', 'L05.00', 'L06.00', 'L01.01', 'L01.02', 'L04.01', 'L07.01', 'Deck', 'Escalones'))
    zoc = rows('OST_Cornices', lambda k: has(k, 'Zocalo'))
    ceil = rows('OST_Ceilings')
    roofs = rows('OST_Roofs'); framing = rows('OST_StructuralFraming'); fascia = rows('OST_Fascia'); gutter = rows('OST_Gutter'); alero = rows('OST_Floors', lambda k: has(k, 'Alero'))
    pil_w = rows('OST_Walls', lambda k: has(k, 'Pileta')); pil_f = rows('OST_Floors', lambda k: has(k, 'Pileta')); pil_g = rows('OST_GenericModel', lambda k: has(k, 'pileta'))
    parr = rows('OST_SpecialityEquipment', lambda k: has(k, 'Parrilla')); parr_d = rows('OST_DuctCurves', lambda k: has(k, 'Parrilla'))
    pex = rows('OST_PipeCurves', lambda k: has(k, 'PEX')); colect = rows('OST_PipeAccessory', lambda k: has(k, 'Hidroflex'))
    elec = rows('OST_ElectricalEquipment'); efix = rows('OST_ElectricalFixtures')
    furn = rows('OST_Furniture'); case = rows('OST_Casework'); plumb = rows('OST_PlumbingFixtures'); spec = rows('OST_SpecialityEquipment', lambda k: not has(k, 'Parrilla'))
    topo = rows('OST_Toposolid'); calle = rows('OST_Floors', lambda k: has(k, 'Calle', 'Base Acceso')); rail = rows('OST_StairsRailing'); porton = rows('OST_Walls', lambda k: has(k, 'Portón', 'Porton'))
    wall_mats = {}
    for k, v in rows('OST_Walls').items():
        for mn, mm in v['materials'].items(): wall_mats.setdefault(mn, 0.); wall_mats[mn] += mm['area_m2']
    rev_mats = {k: r2(v) for k, v in wall_mats.items() if has(k, 'Venecitas', 'Piedra', 'Paint', 'Yeso', 'Hormigon fachada')}
    placed_planting = sum(x['placed'] for x in raw['keywordFamilies'] if x['category'] in ('Planting',) or has(x['family'], 'Tree'))

    R = []
    def add(key, name, modeled, score, rs_list, quantities, missing, notes):
        el = sum(sum(v['count'] for v in rs.values()) for rs in rs_list)
        R.append({'key': key, 'name': name, 'modeled': modeled, 'computability': score, 'elements': el,
                  'types': [t for rs in rs_list for t in types(rs)], 'quantities': quantities, 'missing': missing, 'notes': notes})
    add('cubierta', 'Cubierta', 'parcial', 4, [roofs, framing, fascia, gutter, alero],
        {'tejas_m2': summ(roofs)['area_m2'], 'faldones': summ(roofs)['count'], 'vigas_cubierta_ml': summ({k: v for k, v in framing.items() if 'Viga Cubierta' in k})['length_m'],
         'vigas_principales_ml': summ({k: v for k, v in framing.items() if 'Viga Principal' in k})['length_m'], 'correas_ml': summ({k: v for k, v in framing.items() if 'Correas' in k})['length_m'],
         'madera_m3': summ(framing)['volume_m3'], 'fascia_ml': summ(fascia)['length_m'], 'canaletas_ml': summ(gutter)['length_m'], 'alero_metalico_m2': summ(alero)['area_m2']},
        ['Membrana / aislación térmica e hidrófuga (el tipo "Tejas 20mm" solo tiene madera 15 mm + 5 mm)', 'Bajadas pluviales y zinguería completa (solo 2 canaletas, 14 ml)', 'Cumbreras, limatesas y babetas', 'Pendiente como parámetro de cada faldón (verificar)', 'Vigas de madera sin nivel asignado (195 con "(sin nivel)")'],
        'Rubro con mejor capacidad de cómputo después de estructura y aberturas: faldones, vigas y correas medibles. Láminas siguientes recomendadas.')
    add('pisos', 'Pisos y zócalos', 'parcial', 4, [pisos, zoc],
        {'vinilico_PB_m2': r2(sum(v['area_m2'] for k, v in pisos.items() if has(k, 'L02.00', 'L03.00', 'L05.00', 'L06.00')) + sum(v['area_m2'] for k, v in pisos.items() if 'L01.00' in k)),
         'alfombra_L01_01_m2': summ({k: v for k, v in pisos.items() if 'L01.01' in k})['area_m2'], 'madera_PA_m2': r2(sum(v['area_m2'] for k, v in pisos.items() if has(k, 'L01.02', 'L04.01', 'L07.01'))),
         'deck_m2': summ({k: v for k, v in pisos.items() if 'Deck' in k})['area_m2'], 'escalones_m2': summ({k: v for k, v in pisos.items() if 'Escalones' in k})['area_m2'],
         'zocalos_ml': summ(zoc)['length_m'], 'zocalos_tramos': summ(zoc)['count']},
        ['Zócalos solo en 5 tramos de PB (25,6 ml): faltan el resto de los locales', 'Pisos de baños / cerámicos específicos (los paquetes usan "Piso Vinilico PB")', 'Umbrales y solias'],
        'Paquetes de piso por tipo con capa de terminación: m² por local derivables cruzando con los locales.')
    add('climatizacion', 'Climatización (piso radiante)', 'parcial', 3, [pex, colect],
        {'pex_ml': summ(pex)['length_m'], 'colectores': sum(v['count'] for k, v in colect.items() if 'Colector' in k), 'termostatos': sum(v['count'] for k, v in colect.items() if 'termostato' in k.lower())},
        ['Bomba de calor inverter', 'Sistemas por circuito / retorno como Hydronic Return', 'Espacios MEP y cargas'], 'Ver public/casa-angel/climatizacion/manifest.json.')
    add('albanileria', 'Albañilería (muros y tabiques no estructurales)', 'parcial', 3, [alb],
        {**{k: v for k, v in summ(alb).items()}, 'durlock_m2': summ({k: v for k, v in alb.items() if has(k, 'W111', 'W112')})['area_m2'],
         'muros_interiores_m2': summ({k: v for k, v in alb.items() if has(k, 'Muro Interior', 'Blockwork', 'Bajo Escalera')})['area_m2'],
         'fachadas_m2': summ({k: v for k, v in alb.items() if 'Fachada' in k})['area_m2']},
        ['Composición real de muros de mampostería (los tipos tienen una sola capa "White Paint")', 'Revoques, dinteles y refuerzos', 'Encuentros con estructura'],
        'Durlock W111/W112 con capas reales (placas + montantes). Mampostería: área y largo confiables, materiales no.')
    add('cielorrasos', 'Cielorrasos', 'parcial', 3, [ceil],
        {**summ(ceil), 'yeso_RH_m2': summ({k: v for k, v in ceil.items() if 'RH' in k})['area_m2'], 'yeso_ST_m2': summ({k: v for k, v in ceil.items() if 'ST' in k})['area_m2'], 'plain_PA_m2': summ({k: v for k, v in ceil.items() if 'Plain' in k})['area_m2']},
        ['Cielorrasos de PE y de varios locales de PB/PA (108,7 m² modelados vs ~480 m² de locales)', 'Buñas, tapas de inspección, cajones'], 'Placas Knauf ST/RH en PB, "Plain" genérico en PA.')
    add('pileta', 'Pileta', 'parcial', 3, [pil_w, pil_f, pil_g],
        {'muros_m2': summ(pil_w)['area_m2'], 'piso_m2': summ({k: v for k, v in pil_f.items() if 'Piso' in k})['area_m2'], 'borde_m2': summ({k: v for k, v in pil_f.items() if 'Borde' in k})['area_m2'], 'agua_m3': summ(pil_g)['volume_m3']},
        ['Equipo de filtrado, bomba, cañerías y skimmers', 'Iluminación', 'Estructura de la pileta (muros como "Venecitas" 20 cm)'], 'Geometría del vaso y revestimiento venecitas modelados.')
    add('exteriores', 'Exteriores y paisajismo', 'parcial', 2, [topo, calle, rail, porton],
        {'terreno_m2': summ(topo)['area_m2'], 'calle_m2': summ({k: v for k, v in calle.items() if 'Calle' in k})['area_m2'], 'barandas_ml': summ(rail)['length_m'], 'porton_m2': summ(porton)['area_m2'], 'vegetacion_colocada': placed_planting},
        ['Vegetación (familias de árboles cargadas, 0 colocadas)', 'Solados exteriores, cercos, riego, iluminación exterior'], 'Terreno (toposólido) y "Calle" como piso de 1 m de tierra.')
    add('equipamiento', 'Equipamiento y mobiliario fijo', 'parcial', 2, [case, furn, plumb, spec],
        {'muebles': summ(furn)['count'], 'bajomesadas': summ(case)['count'], 'artefactos_sanitarios': summ(plumb)['count'], 'equipos_especiales': summ(spec)['count']},
        ['Muebles de cocina completos (solo 3 cajoneras)', 'Placares interiores como mobiliario fijo con medidas de fabricación'], 'Muchos muebles sin nivel (familias in-place).')
    add('revestimientos', 'Revestimientos', 'no', 1, [],
        {'materiales_en_muros_m2': rev_mats},
        ['Cerámicos y porcelanatos de baños y cocina', 'Capas de terminación de muros (no hay capas Finish en mampostería)', 'Revestimiento de fachada (solo "Hormigon fachada" 8 cm en 2 tipos)'],
        'Solo venecitas (pileta), piedra (chimenea) y pintura como material genérico.')
    add('parrilla', 'Parrilla', 'parcial', 1, [parr, parr_d], {'parrilla': summ(parr)['count'], 'conductos_ml': summ(parr_d)['length_m']},
        ['Fogonero, campana, revestimiento refractario y conducto completo hasta cubierta'], 'Familia "Parrilla K42DB" + 2 conductos.')
    add('electrica', 'Eléctrica', 'no', 0, [elec, efix], {'tableros': summ(elec)['count']},
        ['Bocas, tomas, llaves, luminarias, cañerías y circuitos (0 modelados)', 'Las 3 "Electrical Fixtures" son lavavajillas mal categorizados'], 'Solo un tablero ABB en PE.')
    add('gas', 'Gas', 'no', 0, [], {}, ['Cañerías, medidor, regulador y artefactos a gas (la cocina dual fuel es equipamiento)'], 'Sin red de gas modelada.')
    add('domotica', 'Domótica', 'no', 0, [], {}, ['Sensores, actuadores, cableado y centrales'], 'Sin elementos.')
    add('solar', 'Paneles solares', 'no', 0, [], {}, ['Paneles, estructura, inversor y cableado'], 'Sin elementos ni familias.')
    R.sort(key=lambda r: -r['computability'])
    out = {'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': raw['readAt'], 'method': 'Inventario de solo lectura por categoría, tipo y material (job R14).',
           'scale': 'computability 0–4: 4 = geometría y tipos suficientes para láminas y cómputo; 0 = no modelado.',
           'done': ['estructura', 'aberturas', 'sanitarias'], 'rubros': R}
    p = a.public_dir / 'casa-angel' / 'rubros-inventario.json'
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    for r in R: print(f"{r['key']:<15} {r['modeled']:<8} {r['computability']} {r['elements']:>4}  {r['notes'][:70]}")


if __name__ == '__main__': main()
