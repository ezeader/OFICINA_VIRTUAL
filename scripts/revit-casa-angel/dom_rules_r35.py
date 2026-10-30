"""R35 Domótica etapa 2 · placement rules (CPython, no Revit): dom35-model.json + hvac-plan.json -> dom35-plan.json.
Every element: code, kind, system, level (PB/PA/PE), room, x/y (m, project coordinates) or ref (linked element id), mount,
opt (False = base), note; plus cones for cameras and the 'revisar' list (rules that did not close)."""
import json, math, collections
from pathlib import Path

OUT = Path(__file__).parent / 'openings-r4'
LV = {'00. Planta Baja': 'PB', '005. Acceso ppal': 'PB', '01. Planta Alta': 'PA', '02. Planta Entrepiso': 'PE'}
LVN = {'PB': '00. Planta Baja', 'PA': '01. Planta Alta', 'PE': '02. Planta Entrepiso'}
SYS = {'LZ': 'IL', 'TK': 'IL', 'PIR': 'IL', 'PRE': 'IL', 'CM': 'CR', 'SV': 'CR', 'TE': 'CL', 'GW': 'CL', 'CAM': 'CA', 'AP': 'RD', 'RK': 'RD', 'TL': 'RD', 'ME': 'RD',
       'AU': 'AU', 'VP': 'AC', 'CE': 'AC', 'PO': 'AC', 'RG': 'RG', 'LL': 'RG', 'DH': 'SG', 'DA': 'SG', 'MG': 'SG', 'SI': 'SG', 'DG': 'SG', 'EVG': 'SG'}
TYPE = {'LZ': 'Zona de iluminación', 'TK': 'Teclado de escenas', 'PIR': 'Sensor de movimiento', 'PRE': 'Sensor de presencia', 'CM': 'Motor de cortina',
        'SV': 'Estación viento/sol/lluvia', 'TE': 'Termostato (CLI)', 'GW': 'Módulo de actuadores', 'CAM': 'Cámara', 'AP': 'Punto de acceso Wi-Fi', 'RK': 'Rack mural 12U',
        'TL': 'Tablero de iluminación domótica', 'ME': 'Medidor de energía', 'AU': 'Parlante de embutir', 'VP': 'Videoportero', 'CE': 'Cerradura inteligente', 'PO': 'Portón vehicular',
        'RG': 'Controlador de riego', 'LL': 'Sensor de lluvia', 'DH': 'Detector humo/CO', 'DA': 'Detector de agua', 'MG': 'Contacto de apertura', 'SI': 'Sirena', 'DG': 'Detector de gas (GLP)', 'EVG': 'Electroválvula de corte de gas'}

A = {'PB': ['Quincho', 'Cuarto ppal', 'Vestidor ppal', 'Baño ppal'], 'PA': ['Sala de TV', 'Playroom', 'Cocina', 'Comedor', 'Living']}
B = {'PB': ['Toilette Servicio', 'Lavadero', 'Acceso Servicio', 'Baño A Inv.', 'Baño B Inv.', 'Baño C Inv.', 'Pasillo', 'Hall'],
     'PA': ['Sala de Maquinas', 'Baño PA', 'Toilette', 'Cava', 'Puente'], 'PE': ['SM', 'Hall PE']}
Cc = {'PB': ['Cuarto A Inv.', 'Cuarto B Inv.', 'Cuarto C Inv.', 'Hab. servicio'], 'PE': ['Atelier']}
WET = ['Baño', 'Toilette', 'Lavadero', 'Cava', 'Sala de Maquinas', 'SM', 'Ascensor']


def fix(o):
    """IronPython wrote non-ASCII as literal backslash-x escapes: decode them."""
    if isinstance(o, dict): return {k: fix(v) for k, v in o.items()}
    if isinstance(o, list): return [fix(v) for v in o]
    if isinstance(o, str) and '\\x' in o: return o.encode('latin-1', 'backslashreplace').decode('unicode_escape')
    return o


def load():
    d = fix(json.loads((OUT / 'dom35-model.json').read_text(encoding='utf-8')))
    hv = json.loads((OUT / 'hvac-plan.json').read_text(encoding='utf-8'))['elements']
    return d, hv


def pip(p, poly):
    x, y = p; ins = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1: ins = not ins
    return ins


def centroid(poly):
    a = cx = cy = 0.
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]; c = x1 * y2 - x2 * y1; a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    return (cx / (3 * a), cy / (3 * a)) if abs(a) > 1e-9 else tuple(poly[0])


def bbox(poly): xs = [p[0] for p in poly]; ys = [p[1] for p in poly]; return min(xs), min(ys), max(xs), max(ys)


def main():
    d, hv = load()
    rooms = {}
    for r in d['rooms']:
        lv = LV.get(r['level'])
        if lv and r['poly']: rooms[(lv, r['name'])] = dict(r, lv=lv, c=centroid(r['poly']))
    out = []; rev = []; cnt = collections.Counter()

    def add(k, lv, room, p, mount, opt=False, note='', ref=None, **kw):
        num = cnt[(k, lv)] = cnt[(k, lv)] + 1
        code = kw.pop('code', None) or '%s-%s-%02d' % (k, lv, num)
        e = {'code': code, 'kind': k, 'type': TYPE[k], 'system': SYS[k], 'level': lv, 'room': room, 'mount': mount, 'opt': opt, 'note': note}
        if p is not None: e['x'], e['y'] = round(p[0], 3), round(p[1], 3)
        if ref: e['ref'] = ref
        e.update(kw); out.append(e); return e

    def R(lv, n):
        r = rooms.get((lv, n))
        if r is None: rev.append('Local «%s» (%s) no está en el modelo' % (n, lv))
        return r

    def inside(r, p, toward=None):
        """keep p inside the room: pull toward the centroid until inside."""
        c = toward or r['c']
        for t in [0, .2, .4, .6, .8, 1.]:
            q = (p[0] + (c[0] - p[0]) * t, p[1] + (c[1] - p[1]) * t)
            if pip(q, r['poly']): return q
        return c

    def nudge(r, p, d=.3):
        """point on a wall/opening line -> just inside the room (first of 8 directions that lands inside)."""
        if r is None: return p
        for k in range(8):
            a = k * math.pi / 4; q = (p[0] + d * math.cos(a), p[1] + d * math.sin(a))
            if pip(q, r['poly']): return q
        return inside(r, p)

    def axis_pts(r, fr):
        x0, y0, x1, y1 = bbox(r['poly']); cx, cy = r['c']
        if x1 - x0 >= y1 - y0: return [inside(r, (x0 + (x1 - x0) * f, cy)) for f in fr]
        return [inside(r, (cx, y0 + (y1 - y0) * f)) for f in fr]

    ops = d['openings']; ext_ops = []
    NOT_EXT = {2274577: 'puerta', 2274582: 'ventana'}   # face the west passage of the Pasillo, which has no room: interior
    for i, k in NOT_EXT.items(): rev.append('%s %s de Cuarto A Inv.: da al paso al oeste del Pasillo, que no tiene local; se toma como interior' % (k.capitalize(), i))
    for o in ops:
        fr, to = o['from'], o['to']; lv = LV.get(o['level'])
        if o['id'] in NOT_EXT: continue
        if lv and (fr is None) != (to is None):
            rm = (fr or to)['name']; ext_ops.append(dict(o, lv=lv, room=rm, w=o['width_m'] or 0))
    for w in d['curtain']:
        l, r_ = w['left'], w['right']
        if w['id'] in (1020050, 1020586): continue                       # ascensor: fuera de alcance
        if (l is None) == (r_ is None):
            rev.append('Muro cortina %s (%s, %s m) sin lado exterior claro: no lleva motor; revisar' % (w['id'], w['type'], w['length_m'])); continue
        rm = (l or r_)['name']; lv = next((k[0] for k in rooms if k[1] == rm), LV.get(w['level']))
        mid = ((w['a'][0] + w['b'][0]) / 2, (w['a'][1] + w['b'][1]) / 2)
        ext_ops.append({'id': w['id'], 'kind': 'curtain', 'family': w['type'], 'lv': lv, 'room': rm, 'w': w['length_m'], 'point': list(mid), 'curtain': True})

    def door_of(room, lv):
        cand = [o for o in ops if o['kind'] == 'door' and LV.get(o['level']) == lv and room in [(o['from'] or {}).get('name'), (o['to'] or {}).get('name')]]
        if not cand: return None
        circ = ('Hall', 'Pasillo', 'Puente', 'Hall PE')
        cand.sort(key=lambda o: (0 if (o['from'] is None or o['to'] is None) else 1 if any((x or {}).get('name') in circ for x in (o['from'], o['to'])) else 2, -(o['width_m'] or 0)))
        return cand[0]

    def by_door(r, o, side=.25, into=.20):
        """point beside the door, lock side (opposite the hinge = +hand), inside room r."""
        px, py = o['point'][:2]; hx, hy = o['hand']; w = (o['width_m'] or .9) / 2 + side
        p = (px + hx * w, py + hy * w); q = (px - hx * w, py - hy * w)
        for cand in (p, q):
            fx, fy = o['facing']
            for s in (1, -1):
                t = (cand[0] + fx * into * s, cand[1] + fy * into * s)
                if pip(t, r['poly']): return t
        return inside(r, p)

    # ---------------- IL
    for lv, names in A.items():
        for n in names:
            r = R(lv, n)
            if r: add('LZ', lv, n, r['c'], 'etiqueta', code='LZ-%s-%s' % (lv, len([1 for e in out if e['kind'] == 'LZ' and e['level'] == lv]) + 1), zone='A')
    for lv, names in B.items():
        for n in names:
            r = R(lv, n)
            if r: add('LZ', lv, n, r['c'], 'etiqueta', zone='B')
    for lv, names in Cc.items():
        for n in names:
            r = R(lv, n)
            if r: add('LZ', lv, n, r['c'], 'etiqueta', zone='C')
    # renumber LZ per level in plan order (left→right, top→bottom)
    for lv in ('PB', 'PA', 'PE'):
        zs = sorted([e for e in out if e['kind'] == 'LZ' and e['level'] == lv], key=lambda e: (-round(e['y'] / 3), e['x']))
        for i, e in enumerate(zs): e['code'] = 'LZ-%s-%02d' % (lv, i + 1)
    tk_rooms = [('PB', 'Quincho'), ('PB', 'Cuarto ppal'), ('PB', 'Vestidor ppal'), ('PB', 'Baño ppal'), ('PA', 'Sala de TV'), ('PA', 'Playroom'), ('PA', 'Cocina'), ('PA', 'Living')]
    for lv, n in tk_rooms:
        r = R(lv, n)
        if not r: continue
        o = door_of(n, lv)
        if o: p = by_door(r, o); note = 'junto a la puerta, lado cerradura'
        else:
            # no door in the model: nearest point of the room to the nearest circulation room
            circ = [rooms[k] for k in rooms if k[0] == lv and k[1] in ('Hall', 'Pasillo', 'Puente', 'Vestidor ppal', 'Comedor')]
            tgt = min(circ, key=lambda c: math.hypot(c['c'][0] - r['c'][0], c['c'][1] - r['c'][1]))['c'] if circ else r['c']
            p = inside(r, min(r['poly'], key=lambda q: math.hypot(q[0] - tgt[0], q[1] - tgt[1]))); note = 'sin puerta en el modelo: en el acceso desde la circulación'
            rev.append('TK en %s (%s): el local no tiene puerta modelada; ubicado en el acceso desde la circulación' % (n, lv))
        add('TK', lv, n + (' / Comedor' if n == 'Living' else ''), p, 'muro h 1,10', note=note)
        if n == 'Cuarto ppal':
            x0, y0, x1, y1 = bbox(r['poly']); far = max(r['poly'], key=lambda q: math.hypot(q[0] - p[0], q[1] - p[1]))
            add('TK', lv, n, inside(r, ((far[0] + r['c'][0]) / 2, (far[1] + r['c'][1]) / 2)), 'muro h 1,10 (cabecera)', note='cabecera: a confirmar con el lay-out de la cama')
            rev.append('TK de cabecera del Cuarto ppal: posición estimada, confirmar con el lay-out de la cama')
    hall = R('PB', 'Hall'); acc = next((o for o in ops if o['id'] == 381946), None)
    if hall and acc: add('TK', 'PB', 'Hall', by_door(hall, acc), 'muro h 1,10', note='escena general «Salgo / Llego»')
    # PIR
    pas = R('PB', 'Pasillo')
    if pas:
        for p in axis_pts(pas, (.08, .92)): add('PIR', 'PB', 'Pasillo', p, 'cielorraso', note='extremo del pasillo')
    for lv, n in [('PB', 'Hall'), ('PB', 'Acceso Servicio'), ('PB', 'Vestidor ppal'), ('PA', 'Cava'), ('PA', 'Sala de Maquinas'), ('PE', 'SM'), ('PA', 'Puente'), ('PE', 'Hall PE')]:
        r = R(lv, n)
        if r: add('PIR', lv, n, inside(r, (r['c'][0] + .4, r['c'][1] + .4)) if n == 'Hall' else r['c'], 'cielorraso')
    for st in d['stairs']:
        x0, y0, z0, x1, y1, z1 = st['bbox']; long_x = x1 - x0 > y1 - y0
        ends = [((x0 + .3, (y0 + y1) / 2), (x1 - .3, (y0 + y1) / 2))] if long_x else [(((x0 + x1) / 2, y0 + .3), ((x0 + x1) / 2, y1 - .3))]
        lo_lv = 'PB'; hi_lv = 'PA' if z1 <= 3.5 else 'PE'
        add('PIR', lo_lv, 'Escalera', ends[0][0], 'cielorraso', note='arranque de escalera (extremo a confirmar)')
        add('PIR', hi_lv, 'Escalera', ends[0][1], 'cielorraso', note='llegada de escalera (extremo a confirmar)')
        if hi_lv == 'PE': add('PIR', 'PA', 'Escalera', ((ends[0][0][0] + ends[0][1][0]) / 2, (ends[0][0][1] + ends[0][1][1]) / 2), 'cielorraso', note='paso por PA')
    rev.append('PIR de escaleras: el modelo no indica qué extremo es el arranque; ubicados en los dos extremos de cada escalera')
    ext_doors = [o for o in ext_ops if o.get('kind') == 'door']
    for o in ext_doors:
        fx, fy = o['facing']; px, py = o['point'][:2]
        r = rooms.get((o['lv'], o['room'])); s = -1 if r and pip((px + fx * .5, py + fy * .5), r['poly']) else 1
        add('PIR', o['lv'], 'Exterior', (px + fx * .6 * s, py + fy * .6 * s), 'sobre el dintel, afuera', note='puerta %s' % o['room'])
    rev.append('Acceso Servicio: no hay puerta exterior modelada (PIR exterior, cámara, videoportero y cerradura ubicados sobre el muro exterior del local; confirmar)')
    for lv, n in [('PB', 'Baño A Inv.'), ('PB', 'Baño B Inv.'), ('PB', 'Baño C Inv.'), ('PB', 'Toilette Servicio'), ('PB', 'Lavadero'), ('PB', 'Baño ppal'), ('PA', 'Baño PA'),
                  ('PA', 'Toilette'), ('PA', 'Cocina'), ('PB', 'Hall'), ('PE', 'Atelier')]:
        r = R(lv, n)
        if r: add('PRE', lv, n, r['c'], 'cielorraso, centro', note='combinado con PIR' if n == 'Hall' else ('solo apaga' if n == 'Atelier' else ''))
    # ---------------- CR
    for o in ext_ops:
        n = o['room']; wide = (o['w'] or 0) >= 1.2
        if o.get('kind') == 'door': continue                               # opaque doors: no blind
        if any(k in n for k in WET) and not wide:
            rev.append('Sin motor de cortina: %s en %s (%s, %s m) por ser local de servicio' % (o.get('family'), n, o['lv'], o['w'])); continue
        r = rooms.get((o['lv'], n)); px, py = o['point'][:2]
        p = nudge(r, (px, py))
        add('CM', o['lv'], n, p, 'dintel interior', note='vano %.2f m' % (o['w'] or 0), width=o['w'], ref_open=o['id'])
    rf = max(d['roofs'], key=lambda r: r['bbox'][5]); x0, y0, _, x1, y1, z1 = rf['bbox']
    add('SV', 'PE', 'Cubierta', ((x0 + x1) / 2, (y0 + y1) / 2), 'cubierta, punto alto', opt=True, code='SV-01', note='cumbrera +%.2f' % z1)
    # ---------------- CL
    for t in [x for x in hv if x['kind'] == 'TE']:
        lv = LV.get(t.get('level'))
        if lv is None:
            rm = next((k for k in rooms if k[1] == t.get('room')), None); lv = rm[0] if rm else 'PB'
            rev.append('%s sin nivel en el modelo: mostrado en %s (%s)' % (t['code'], lv, t.get('room') or 'sin local'))
        if not t.get('room'): rev.append('%s sin local (ya avisado en CLI)' % t['code'])
        add('TE', lv, t.get('room') or '(sin local)', None, 'muro h 1,50', ref=t['id'], code=t['code'], note='existente (CLI)')
    co = {x['code']: x for x in hv if x['kind'] == 'CO'}
    add('GW', 'PE', 'SM', None, 'gabinete del colector', ref=co['CO-N']['id'], code='GW-CL-N', note='CO-N · 14 canales')
    add('GW', 'PA', 'Sala de Maquinas', None, 'gabinete del colector', ref=co['CO-S']['id'], code='GW-CL-S', note='CO-S · 12 canales')
    smr = R('PE', 'SM')
    if smr: add('GW', 'PE', 'SM', inside(smr, (smr['c'][0] - .5, smr['c'][1] - .4)), 'junto al equipo', code='GW-CL-CA', note='equipo térmico (a definir)')
    # portón vehicular (user, via rubro-domotica): fachada «de Toneo», al lado del ascensor; not modelled
    asc = next((w for w in d['curtain'] if w['id'] == 1020050), None)
    gate = (asc['a'][0] + .35, min(asc['a'][1], asc['b'][1]) - 1.8) if asc else None
    rev.append('PO-01 portón vehicular: no está modelado; ubicado en la fachada «de Toneo» junto al ascensor (posición y ancho a confirmar)')
    # ---------------- CA
    allp = [p for (lv, n), r in rooms.items() if lv in ('PB', 'PA') for p in r['poly']]
    X0, Y0, X1, Y1 = min(p[0] for p in allp), min(p[1] for p in allp), max(p[0] for p in allp), max(p[1] for p in allp)
    cams = []
    for o in ext_doors:
        fx, fy = o['facing']; px, py = o['point'][:2]; r = rooms.get((o['lv'], o['room']))
        s = -1 if r and pip((px + fx * .5, py + fy * .5), r['poly']) else 1
        cams.append(('PB', 'Exterior · ingreso %s' % o['room'], (px + fx * .3 * s + o['hand'][0] * 1.0, py + fy * .3 * s + o['hand'][1] * 1.0), math.atan2(fy * s, fx * s)))
    asv = R('PB', 'Acceso Servicio')
    if asv:
        q = max(asv['poly'], key=lambda p: p[1]); cams.append(('PB', 'Exterior · Acceso Servicio', (q[0], q[1] + .3), math.pi / 2))
    for (cx, cy), ang in [((X0, Y0), -3 * math.pi / 4), ((X1, Y0), -math.pi / 4), ((X1, Y1), math.pi / 4), ((X0, Y1), 3 * math.pi / 4)]:
        cams.append(('PB', 'Exterior · esquina', (cx + .3 * math.cos(ang), cy + .3 * math.sin(ang)), ang))
    if gate: cams.insert(1, ('PB', 'Exterior · portón vehicular', (gate[0] + .3, gate[1] + 1.2), 0.0))
    for lv, n, p, ang in cams[:8]: add('CAM', lv, n, p, 'fachada h 2,70 / bajo alero', cone=[round(ang, 4), 90, 10])
    rev.append('Cámaras de esquina sobre el rectángulo envolvente del edificio: ajustar a las esquinas reales y al alero')
    for lv, n in [('PB', 'Hall'), ('PA', 'Living')]:
        r = R(lv, n)
        if r:
            x0, y0, x1, y1 = bbox(r['poly']); p = inside(r, (x0 + .4, y1 - .4))
            add('CAM', lv, n, p, 'cielorraso / esquina', opt=True, cone=[round(math.atan2(r['c'][1] - p[1], r['c'][0] - p[0]), 4), 90, 6], note='interior opc')
    # ---------------- RD
    sm = R('PA', 'Sala de Maquinas')
    if sm:
        cs_ = next((x for x in hv if x['code'] == 'CO-S'), None)
        edges = [(sm['poly'][i - 1], sm['poly'][i]) for i in range(len(sm['poly']))]
        edges = [e for e in edges if math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]) >= .6]
        e = max(edges, key=lambda e: math.hypot((e[0][0] + e[1][0]) / 2 - sm['c'][0], 0) + math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]) * .1)
        mid = ((e[0][0] + e[1][0]) / 2, (e[0][1] + e[1][1]) / 2)
        add('RK', 'PA', 'Sala de Maquinas', inside(sm, mid), 'muro, rack 12U (0,60 m)', code='RK-01', note='router, switch PoE, controlador, NVR, amplificador, UPS')
        rev.append('RK-01: muro de Sala de Máquinas elegido por geometría (4,79 m²); verificar que no sea el del gabinete CO-S')
    def ap(code, lv, rms, opt=False, note=''):
        rs = [R(lv, n) for n in rms]; rs = [r for r in rs if r]
        if not rs: return
        p = (sum(r['c'][0] for r in rs) / len(rs), sum(r['c'][1] for r in rs) / len(rs))
        host = next((r for r in rs if pip(p, r['poly'])), rs[0]); add('AP', lv, ' / '.join(rms), inside(host, p), 'cielorraso', opt=opt, code=code, note=note)
    ap('AP-PB-01', 'PB', ['Hall']); ap('AP-PB-02', 'PB', ['Quincho'])
    if pas:
        x0, y0, x1, y1 = bbox(pas['poly']); add('AP', 'PB', 'Pasillo', inside(pas, (x0 + 2.0, pas['c'][1])), 'cielorraso', code='AP-PB-03', note='extremo de cuartos de invitados')
    ap('AP-PB-04', 'PB', ['Cuarto ppal', 'Vestidor ppal']); ap('AP-PA-01', 'PA', ['Living', 'Comedor'])
    ap('AP-PA-02', 'PA', ['Playroom', 'Sala de TV'], note='cubre Playroom y Sala de TV; la Cocina queda con AP-PA-01')
    rev.append('AP-PA-02: Cocina y Playroom/Sala de TV están en extremos opuestos de PA; ubicado entre Playroom y Sala de TV, Cocina cubierta por AP-PA-01')
    ap('AP-PE-01', 'PE', ['Atelier'])
    qw = next((o for o in ext_ops if o['room'] == 'Quincho' and o.get('curtain')), None); q = R('PB', 'Quincho')
    if qw and q: add('AP', 'PB', 'Quincho (exterior)', inside(q, qw['point'][:2]), 'cielorraso hacia el jardín', opt=True, code='AP-EXT-01')
    tab = next((e for e in d['equipment'] if e['kind'] == 'electrical'), None)
    r = R('PB', 'Acceso Servicio'); add('TL', 'PB', 'Acceso Servicio', r['c'] if r else None, 'muro', code='TL-PB', note='coordinar con Eléctrica')
    add('TL', 'PA', 'Sala de Maquinas', inside(sm, (sm['c'][0] - .3, sm['c'][1])) if sm else None, 'muro', code='TL-PA', note='coordinar con Eléctrica; alimenta PE')
    rev.append('Tableros seccionales no modelados por nivel: TL-PB en Acceso Servicio y TL-PA en Sala de Máquinas (coordinar con Eléctrica)')
    if tab:
        add('ME', LV.get(tab['level'], 'PA'), tab['room'] or '', tab['point'][:2], 'en el tablero', code='ME-01', note='tablero ABB del modelo (%s)' % tab['type'])
        rev.append('ME-01 en el único tablero modelado (ABB %s, %s / %s): confirmar que es el tablero general' % (tab['type'], tab['level'], tab['room']))
    # ---------------- AU
    for lv, n, k, opt in [('PA', 'Living', 2, False), ('PA', 'Comedor', 2, False), ('PA', 'Cocina', 2, False), ('PA', 'Sala de TV', 2, False), ('PB', 'Quincho', 4, False),
                          ('PB', 'Cuarto ppal', 2, True), ('PB', 'Baño ppal', 1, True)]:
        r = R(lv, n)
        if not r: continue
        if k == 1: pts = [r['c']]
        elif k == 2: pts = axis_pts(r, (.25, .75))
        else:
            x0, y0, x1, y1 = bbox(r['poly']); pts = [inside(r, (x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy)) for fy in (.75, .25) for fx in (.25, .75)]
        for p in pts: add('AU', lv, n, p, 'cielorraso', opt=opt)
    if qw:
        (ax, ay) = qw['point'][:2]; w_ = next(w for w in d['curtain'] if w['id'] == qw['id'])
        dx, dy = w_['b'][0] - w_['a'][0], w_['b'][1] - w_['a'][1]; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
        if q and pip((ax + nx * .8, ay + ny * .8), q['poly']): nx, ny = -nx, -ny
        for f in (.25, .75): add('AU', 'PB', 'Exterior Quincho', (w_['a'][0] + dx * f + nx * 1.0, w_['a'][1] + dy * f + ny * 1.0), 'alero / exterior', opt=True)
    # ---------------- AC
    for i, o in enumerate(ext_doors[:1]):
        fx, fy = o['facing']; px, py = o['point'][:2]; r = rooms.get((o['lv'], o['room']))
        s = -1 if r and pip((px + fx * .5, py + fy * .5), r['poly']) else 1; w = (o['width_m'] or 1) / 2 + .25
        add('VP', 'PB', 'Ingreso principal', (px + o['hand'][0] * w + fx * .25 * s, py + o['hand'][1] * w + fy * .25 * s), 'muro exterior h 1,40', code='VP-01')
        add('CE', 'PB', 'Ingreso principal', (px, py), 'en la puerta', code='CE-01')
    if asv:
        q_ = max(asv['poly'], key=lambda p: p[1]); add('VP', 'PB', 'Acceso Servicio', (q_[0] - .5, q_[1] + .25), 'muro exterior h 1,40', code='VP-02', note='puerta exterior no modelada')
        add('CE', 'PB', 'Acceso Servicio', (q_[0] - 1.0, q_[1] - .1), 'en la puerta', code='CE-02', note='puerta exterior no modelada')
    if gate:
        add('PO', 'PB', 'Portón vehicular', gate, 'fachada, motor del portón', code='PO-01', note='fachada «de Toneo», junto al ascensor')
    # ---------------- RG
    lav = R('PB', 'Lavadero')
    if lav:
        q_ = max(lav['poly'], key=lambda p: p[1]); add('RG', 'PB', 'Lavadero', inside(lav, (lav['c'][0], q_[1] - .15)), 'muro hacia el exterior', code='RG-01')
        add('LL', 'PB', 'Exterior', (lav['c'][0], q_[1] + .6), 'exterior, libre de alero', opt=True, code='LL-01')
    # ---------------- SG
    for lv, n in [('PA', 'Cocina'), ('PB', 'Quincho'), ('PA', 'Sala de Maquinas'), ('PE', 'SM'), ('PB', 'Pasillo'), ('PB', 'Cuarto ppal'), ('PE', 'Hall PE'), ('PA', 'Living')]:
        r = R(lv, n)
        if not r: continue
        p = r['c']
        if n == 'Quincho':
            x0, y0, x1, y1 = bbox(r['poly']); p = inside(r, (x0 + (x1 - x0) * .5, y1 - 1.0)); rev.append('DH en Quincho: verificar más de 3 m a la parrilla')
        add('DH', lv, n, p, 'cielorraso')
    fx_ = [e for e in d['equipment'] if e['kind'] == 'plumbing']
    for lv, n in [('PB', 'Baño A Inv.'), ('PB', 'Baño B Inv.'), ('PB', 'Baño C Inv.'), ('PB', 'Baño ppal'), ('PB', 'Toilette Servicio'), ('PA', 'Baño PA'), ('PA', 'Toilette'),
                  ('PB', 'Lavadero'), ('PA', 'Cocina')]:
        r = R(lv, n)
        if not r: continue
        f = [e for e in fx_ if pip(e['point'][:2], r['poly']) and abs(e['point'][2] - (0 if lv == 'PB' else 3)) < 2.5]
        f.sort(key=lambda e: (0 if ('Bacha' in e['family'] or 'Sink' in e['family']) else 1))
        p = f[0]['point'][:2] if f else r['c']
        if not f: rev.append('DA en %s: sin artefacto modelado, en el centro del local' % n)
        add('DA', lv, n, inside(r, p), 'piso, bajo bacha / artefacto')
    add('DA', 'PE', 'SM', None, 'piso, bajo el colector', ref=co['CO-N']['id'], note='CO-N')
    add('DA', 'PA', 'Sala de Maquinas', None, 'piso, bajo el colector', ref=co['CO-S']['id'], note='CO-S')
    for o in ext_doors: add('MG', o['lv'], o['room'], o['point'][:2], 'marco de puerta exterior', note='puerta %s' % o['room'])
    if gate: add('MG', 'PB', 'Portón vehicular', (gate[0], gate[1] - .4), 'portón', note='portón vehicular')
    for o in ext_ops:
        if o['lv'] == 'PB' and o.get('kind') != 'door':
            r = rooms.get(('PB', o['room'])); add('MG', 'PB', o['room'], nudge(r, o['point'][:2], .45), 'marco de ventana', opt=True, note='ventana PB opc')
    if hall: add('SI', 'PB', 'Hall', inside(hall, (hall['c'][0] - .6, hall['c'][1] - .4)), 'cielorraso / muro alto', code='SI-01')
    if acc:
        fx, fy = acc['facing']; px, py = acc['point'][:2]; s = -1 if hall and pip((px + fx * .5, py + fy * .5), hall['poly']) else 1
        add('SI', 'PB', 'Fachada ingreso', (px - acc['hand'][0] * 1.3 + fx * .3 * s, py - acc['hand'][1] * 1.3 + fy * .3 * s), 'fachada h 2,70', code='SI-02')
    # quantities
    q = collections.OrderedDict()
    for e in out:
        k = (e['system'], e['kind']); q.setdefault(k, {'system': e['system'], 'kind': e['kind'], 'type': e['type'], 'base': 0, 'opc': 0})
        q[k]['opc' if e['opt'] else 'base'] += 1
    rec = {'revision': 'R35', 'elements': out, 'quantities': list(q.values()), 'revisar': rev, 'rooms': [{'id': r['id'], 'name': r['name'], 'level': lv,
            'zone': next((z for z, g in (('A', A), ('B', B), ('C', Cc)) if r['name'] in g.get(lv, [])), None), 'c': [round(r['c'][0], 3), round(r['c'][1], 3)]} for (lv, n), r in rooms.items()]}
    (OUT / 'dom35-plan.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
    print(len(out), collections.Counter(e['system'] for e in out)); print('\n'.join(rev))


if __name__ == '__main__': main()
