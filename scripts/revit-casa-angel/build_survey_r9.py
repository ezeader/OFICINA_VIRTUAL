"""Turn openings-r4/survey.json (read-only Revit dump) into a per-element survey for budgeting.

Output: openings-r4/survey-summary.json  {elementId: {...}}  (used by the sheets and the manifest).
Values come from the model; generic Revit materials are flagged so nobody buys from them blindly.
"""
import json, re, collections
from pathlib import Path

OUT = Path(__file__).parent / 'openings-r4'
GENERIC = {'Glass', 'Sash', 'Aluminium', 'Puertas', '<By Category>', 'Wood Sheathing, Chipboard'}


def dec(v):
    if isinstance(v, str): return re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), v)
    if isinstance(v, list): return [dec(x) for x in v]
    if isinstance(v, dict): return {k: dec(x) for k, x in v.items()}
    return v


def txt(params, *names):
    for n in names:
        if n in params and params[n].get('txt') not in (None, '', '<None>'): return params[n]['txt']
        if n in params and isinstance(params[n].get('v'), str) and params[n]['v']: return params[n]['v']
    return None


def r3(x): return round(x, 3) if isinstance(x, (int, float)) else x


def opening_type(r):
    fam, typ = r['family'], r['type']
    if fam == 'M_Fixed': return 'Paño fijo'
    if fam == 'Ventanas' and 'Practicable' in typ: return 'Ventana practicable 2 hojas (abatible, rotura de puente térmico)'
    if fam == 'JALO_PUERTA ABATIBLE': return 'Puerta abatible 1 hoja'
    if fam == 'Puerta interior corredera': return 'Puerta corrediza embutida'
    if r['category'] == 'Walls':
        if 'Corrediza' in typ: return 'Muro cortina · paños corredizos (según tipo; hojas no modeladas)'
        if 'Vano' in typ: return 'Cerramiento vidriado de vano'
        return 'Muro cortina · paños fijos'
    return typ


def summarize(r):
    tp, ip = r['typeParams'], r['instance']
    mats = r['materials']
    glass = [m for m in mats if m['class'] in ('Glass', 'Cristal') or re.search('vidrio|glass|cristal', m['name'], re.I)]
    frame = [m for m in mats if m not in glass]
    s = {'code': r['code'], 'openingType': opening_type(r), 'notes': []}
    if r['category'] == 'Walls':
        panels = []
        for p in r.get('panels', []):
            w, h, src = p['width_m'], p['height_m'], 'parámetro'
            if not w or not h:
                if p.get('bbox'): w, h, src = p['bbox']['width_m'], p['bbox']['height_m'], 'geometría'
                else: w = h = None; src = 'sin geometría'
            panels.append({'id': str(p['id']), 'type': p['type'], 'material': ', '.join(p['materials']) or None,
                           'width_m': r3(w), 'height_m': r3(h), 'area_m2': r3(w * h) if w and h else None, 'source': src})
        glazed = [p for p in panels if p['area_m2'] and p['material'] and 'Glass' in p['material']]
        mull = collections.defaultdict(lambda: {'count': 0, 'length_m': 0.})
        for m in r.get('mullions', []):
            k = (m['type'], ', '.join(m['materials'])); mull[k]['count'] += 1; mull[k]['length_m'] += m['length_m'] or 0
        s['panels'] = panels
        s['glazing'] = {'material': 'Glass (genérico Revit)', 'panes': len(glazed), 'area_m2': r3(sum(p['area_m2'] for p in glazed)), 'method': 'Σ ancho × alto de paneles vidriados'}
        s['frame'] = {'system': 'Montantes de muro cortina', 'profiles': [{'type': k[0], 'material': k[1], 'count': v['count'], 'length_m': r3(v['length_m'])} for k, v in mull.items()],
                      'border': txt(tp, 'Border 1 Type'), 'interior': txt(tp, 'Interior Type')}
        if any(p['source'] == 'sin geometría' for p in panels): s['notes'].append(f"{sum(1 for p in panels if p['source'] == 'sin geometría')} paneles sin geometría (vacíos o recortados): no se computan.")
        if any(p['source'] == 'geometría' for p in panels): s['notes'].append('Algunos paneles sin parámetro de ancho/alto (no rectangulares o de borde): medidos por su caja geométrica.')
    else:
        gm = ', '.join(sorted({m['name'] for m in glass})) or None
        s['glazing'] = {'material': gm, 'spec': txt(tp, 'Analytic Construction') if gm else None, 'thickness_m': txt(tp, 'GrosorAcristalamiento'),
                        'area_m2': r3(sum(m['area_m2'] for m in glass) / 2) if glass else 0, 'method': 'Área del material vidrio / 2 caras (aprox.)' if glass else 'Sin vidrio modelado'}
        s['frame'] = {'material': ', '.join(sorted({m['name'] for m in frame})) or txt(tp, 'MAT - MADERA LACADA', 'Material marco'),
                      'exterior': txt(tp, 'Frame Exterior Material', 'Material marco'), 'interior': txt(tp, 'Frame Interior Material'),
                      'width_m': txt(tp, 'AnchoMarco', 'Anchura de marco', 'Tapajuntas_Anchura'), 'depth_m': txt(tp, 'GrosorMarco', 'Thickness'),
                      'subframe': txt(tp, 'Material premarco'), 'leaf': txt(tp, 'Material hoja'), 'handle': txt(tp, 'Material tirador')}
        s['thermal'] = {'U': txt(tp, 'Heat Transfer Coefficient (U)', 'TransmitanciaTermica'), 'water': txt(tp, 'EstanqueidadAgua'), 'wind': txt(tp, 'ResistenciaAlViento')}
        s['description'] = txt(tp, 'Type Comments', 'Description')
        if r['family'] == 'Ventanas': s['notes'].append('Aluprom 44 (BIMobject Aluval): perfilería aluminio con poliamida; vidrio claro templado.')
    used = {m['name'] for m in mats} | {x for p in s.get('panels', []) for x in (p['material'] or '').split(', ') if x}
    if used & GENERIC: s['notes'].append('Materiales genéricos de Revit (' + ', '.join(sorted(used & GENERIC)) + '): definir especificación comercial antes de presupuestar.')
    return s


def sheet_lines(s):
    """Two short lines for the sheet data block (comma decimals)."""
    c = lambda v: ('%.2f' % v).replace('.', ',')
    g = s['glazing']; f = s['frame']
    l1 = 'Apertura: ' + s['openingType']
    if s.get('panels') is not None:
        n = g['panes']
        l2 = f"Vidrio: {n} {'paño' if n == 1 else 'paños'} · {c(g['area_m2'] or 0)} m² · Perfiles: " + '; '.join(f"{p['type']} {p['count']} u. {c(p['length_m'])} m" for p in f['profiles'])
    else:
        gl = f"Vidrio: {g['material']} ≈ {c(g['area_m2'])} m²" if g['material'] else 'Sin vidrio'
        if f.get('leaf'):
            fr = f"Hoja {f['leaf']} · Marco {f.get('exterior') or f['material']}" + (f" · Premarco {f['subframe']}" if f.get('subframe') else '')
        else:
            fr = 'Marco: ' + (f['material'] or 'sin material') + (f" {f['width_m'].replace('.', ',')}" if f.get('width_m') else '')
        l2 = gl + ' · ' + fr
    return [l1, l2]


def main():
    d = dec(json.loads((OUT / 'survey.json').read_text(encoding='utf-8-sig')))
    out = {}
    for r in d['items']:
        s = summarize(r); s['sheetLines'] = sheet_lines(s); out[str(r['id'])] = s
    (OUT / 'survey-summary.json').write_text(json.dumps(out, ensure_ascii=True, indent=1), encoding='utf-8')
    tot = sum(v['glazing']['area_m2'] or 0 for v in out.values())
    print(json.dumps({'items': len(out), 'glazing_m2': round(tot, 2), 'sample': out[next(iter(out))]['sheetLines']}, ensure_ascii=False))


if __name__ == '__main__': main()
