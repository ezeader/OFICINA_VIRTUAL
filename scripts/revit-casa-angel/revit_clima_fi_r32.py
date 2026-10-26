# -*- coding: utf-8 -*-
"""R32 Climatización etapa 3 (DOC-Climatizacion): one sheet CLI-F-<CI> per room circuit (replaces the R19 CLI-F-CI-* fichas).
Plan of the room at 1:20/1:25 with its serpentine (other circuits not drawn), overall dimensions and room label; table with
ml, m², density, equivalent pitch (1/density), collector + outlet S## (cercanía flagged), thermostat and state."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
P = imp.load_source('ader_clidoc_r32_for_fi', os.path.join(ROOT, 'revit_clima_doc_r32.py'))
C = P.C; B = P.B; L = P.L; S = P.S; X = P.X; R1 = P.R1; CTX = P.CTX
M = L.M; OUT = L.OUT; eid = L.eid; u = P.u; c2 = P.c2
PRE = 'ADER CLI R32 - FICHA '

def ficha(doc, ld, x, k, plan, curves, circ, outlets):
    lvn = x['level']; cs = [curves[str(p)] for p in x['pipeIds'] if str(p) in curves]
    pts = [DB.XYZ(c[i], c[i + 1], 0) for c in cs for i in (0, 3)]
    rp = P.loc(ld, x['roomId']) if x.get('roomId') else None
    v, lev = P.plan_view(doc, lvn, PRE + x['code'], pts or [rp], 20, pad=.8); z = lev.Elevation
    crop = C.crop_of(v); placed = []
    sty = P.style(doc, x['code'], P.PAL[k % len(P.PAL)], 5)
    for c in cs: P.seg(doc, v, c, z, sty)
    c_ = next((c for c in circ if c['code'] == x['code']), {}); co = c_.get('collector', u'?'); how = c_.get('method', u'')
    o = outlets.get(x['code'], {}); st = u'completo' if x['density'] >= 4 else u'incompleto'
    if rp is None or not (crop[0] < rp.X < crop[2] and crop[1] < rp.Y < crop[3]):
        rp = DB.XYZ(sum(p.X for p in pts) / len(pts), sum(p.Y for p in pts) / len(pts), z)
    C.place(doc, v, DB.XYZ(rp.X, rp.Y, z), u'%s · %s\n%s ml · %s m² · %s m/m²' % (R1.clean(x['room'] or u''), x['code'], c2(x['length_m']), c2(x['area_m2']), c2(x['density'])), placed, crop, 'tag', z)
    tes = [t for t in plan if t['kind'] == 'TE' and t.get('room') == x['room']]
    for t in tes:
        p = P.loc(ld, t['id'])
        if p is None or not (crop[0] < p.X < crop[2] and crop[1] < p.Y < crop[3]): continue
        q = DB.XYZ(p.X, p.Y, z); s = .08 / M
        for a, b in [((-s, -s), (s, -s)), ((s, -s), (s, s)), ((s, s), (-s, s)), ((-s, s), (-s, -s))]:
            B.line(doc, v, DB.XYZ(q.X + a[0], q.Y + a[1], z), DB.XYZ(q.X + b[0], q.Y + b[1], z), (0, 0, 0), 4)
        C.place(doc, v, q, t['code'], placed, crop, 'text', z)
    dims = []
    if pts:
        f = L.AxisFrame(v, DB.XYZ(0, 0, z), DB.XYZ.BasisX, DB.XYZ.BasisY)
        xs = [min(p.X for p in pts), max(p.X for p in pts)]; ys = [min(p.Y for p in pts), max(p.Y for p in pts)]
        if xs[1] - xs[0] > .2 / M: dims.append(L.tick_dim(doc, f, u'Serpentín extensión X', xs, True, ys[0] - .45 / M, tick=.06 / M))
        if ys[1] - ys[0] > .2 / M: dims.append(L.tick_dim(doc, f, u'Serpentín extensión Y', ys, False, xs[1] + .45 / M, tick=.06 / M))
    pitch = 1.0 / x['density'] if x['density'] else 0
    rows = [u'Local: %s · %s' % (R1.clean(x['room'] or u''), lvn), u'Circuito: %s' % x['code'],
            u'Tubo PEX Ø20: %s ml (ida %s · retorno %s)' % (c2(x['length_m']), c2(x.get('supply_m') or 0), c2(x.get('return_m') or 0)),
            u'Superficie servida: %s m²' % c2(x['area_m2']), u'Densidad: %s m/m² · paso equivalente %s m' % (c2(x['density']), c2(pitch)),
            u'Colector: %s · salida %s%s' % (co, o.get('outlet', u'—'), u' (asignado por cercanía)' if how and how != u'conectividad' else u''),
            u'Termostato: %s' % (u', '.join(t['code'] for t in tes) or u'(ninguno en el modelo)'), u'Estado: %s (completo ≥ 4 m/m²)' % st]
    refs = [u'Trazo de color: serpentín de este circuito sobre el eje del tubo del modelo', u'Cuadrado: termostato · arquitectura vinculada en medio tono', u'Cotas: extensión del serpentín (m)']
    tv = P.text_view(doc, PRE + x['code'] + ' CUADRO', [(u'Ficha ' + x['code'], rows), (u'Referencias', refs)])
    its = [X.item(v, v.CropBox, u'%s · planta' % x['code'], 'plan', lvn, [x['code']], dims, [x['roomId']] if x.get('roomId') else []), C.item(doc, tv, u'Datos del circuito', [], [])]
    old = list(L.SCALES); L.SCALES[:] = [10, 20, 25, 50]
    try: s = S.lay_sheet(doc, 'CLI-F-' + x['code'], u'Ficha %s · %s' % (x['code'], R1.clean(x['room'] or u'')), u'%s · %s ml · %s m² · %s m/m² · %s %s · %s' % (lvn, c2(x['length_m']), c2(x['area_m2']), c2(x['density']), co, o.get('outlet', u''), st),
                         its, P.FOOT, plan_region=True, rubro=P.RUBRO, sheet_name=u'Climatiz. · ' + x['code'])
    finally: L.SCALES[:] = old
    return dict(s, kind='element', element=x['code'], elementId=str(x['roomId']) if x.get('roomId') else None, elementKind='CI', level=lvn, sector=u'3 · Fichas por local',
                data={'collector': co, 'method': how, 'outlet': o.get('outlet'), 'pitch_m': round(pitch, 3), 'thermostats': [t['code'] for t in tes], 'status': st})

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L, S, X.F, X, None])
    assert ld is not None, 'Abrir Casa-Angel-DOC-Climatizacion.rvt'
    part = job['part']; path = os.path.join(OUT, 'cli32-fichas.json')
    if part == 'export':
        L.register_font()
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        rec = R1.read(path); done = []
        for sh in rec['sheets']:
            opts.FileName = 'r32-' + sh['number']; sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([DB.ElementId(Int64(sh['sheetId']))]), opts)); done.append(sh['number'])
        R1.write(path, rec); return {'status': 'success', 'exported': done}
    if os.path.exists(path) and not job.get('redo'): return {'status': 'success', 'existing': True}
    if os.path.exists(path):
        rec = R1.read(path)
        def wipe():
            for sh in rec['sheets']:
                for i in [sh['sheetId']] + [x['id'] for x in sh['views']]:
                    e = doc.GetElement(DB.ElementId(Int64(int(i))))
                    if e is not None: doc.Delete(e.Id)
        B.plain(doc, 'ADER CLI R32 - borrar fichas', wipe); os.remove(path)
    L.register_font()
    plan, cc, curves = P.data()
    circ = [c for s in R1.read(os.path.join(OUT, 'cli32-plans.json'))['sheets'] for c in s['circuits']]
    outlets = dict((o['code'], o) for s in R1.read(os.path.join(OUT, 'cli32-collectors.json'))['sheets'] for o in s['outlets'])
    cis = sorted([x for x in plan if x['kind'] == 'CI'], key=lambda x: x['code'])
    only = job.get('only')
    if only: cis = [x for x in cis if x['code'] in only]
    sheets = []
    for k, x in enumerate(cis):   # one transaction per ficha: a failure leaves the previous ones in place
        sheets.append(B.plain(doc, 'ADER CLI R32 - ficha ' + x['code'], lambda: ficha(doc, ld, x, k, plan, curves, circ, outlets)))
        for y in sheets[-1]['views']: y.pop('view', None)
    R1.write(path, {'part': 'fichas', 'revision': 'R32', 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'sheets': [(sh['number'], [y['scale'] for y in sh['views']]) for sh in sheets]}
