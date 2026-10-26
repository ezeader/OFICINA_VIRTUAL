# -*- coding: utf-8 -*-
"""R32 Climatización etapa 2 (DOC-Climatizacion): CLI-CO-N and CLI-CO-S, one sheet per collector:
plan 1:20 around the collector with the circuits it feeds (one colour per circuit), front elevation 1:10 with cabinet and
dimensions, outlet scheme (S01.. → CI → local, ml, m², state) with thermostats and risers, and a table per collector."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
P = imp.load_source('ader_clidoc_r32_for_co', os.path.join(ROOT, 'revit_clima_doc_r32.py'))
C = P.C; B = P.B; L = P.L; S = P.S; X = P.X; R1 = P.R1; CTX = P.CTX
M = L.M; OUT = L.OUT; eid = L.eid; u = P.u; name = P.name; c2 = P.c2
PRE = 'ADER CLI R32 - '
CABINET = {'CO-N': 'GA-N', 'CO-S': 'GA-S'}

def outlets(plan, cc, sheets_circ, co):
    """Circuits of this collector ordered by the collector connector they leave from; S01.. numbering."""
    rows = []
    for c in sheets_circ:
        if c['collector'] != co: continue
        x = next(e for e in plan if e['code'] == c['code']); k = (cc.get(c['code'], {}).get('outlets') or [99])
        rows.append((min(k), x, c))
    rows.sort(key=lambda r: (r[0], r[1]['code']))
    return [(u'S%02d' % (i + 1), x, c, k) for i, (k, x, c) in enumerate(rows)]

def plan_around(doc, ld, co_el, lvname, vname, plan, rows, curves):
    p = P.loc(ld, co_el['id'])
    v, lev = P.plan_view(doc, lvname, vname, [DB.XYZ(p.X - .7 / M, p.Y - .7 / M, 0), DB.XYZ(p.X + .7 / M, p.Y + .7 / M, 0)], 20, pad=.3)   # crop ±1,0 m: cabinet and first metres of each outlet
    v.DetailLevel = DB.ViewDetailLevel.Fine; z = lev.Elevation; cr = C.crop_of(v); placed = []
    inside = lambda c: any(cr[0] < q[0] < cr[2] and cr[1] < q[1] < cr[3] for q in ((c[0], c[1]), (c[3], c[4])))
    for k, (sn, x, c, _) in enumerate(rows):
        sty = P.style(doc, x['code'], P.PAL[k % len(P.PAL)], 5)
        for pid in x['pipeIds']:
            cv = curves.get(str(pid))
            if cv and inside(cv): P.seg(doc, v, cv, z, sty)
    for x in plan:
        if x['kind'] == 'DI':
            for pid in x['pipeIds']:
                cv = curves.get(str(pid))
                if cv and inside(cv):
                    if not P.seg(doc, v, cv, z, P.style(doc, 'DI', (70, 70, 70), 3)) and abs(cv[5] - cv[2]) > .3 / M:
                        B.circle(doc, v, DB.XYZ(cv[0], cv[1], z), .08 / M, (70, 70, 70))
    q = DB.XYZ(p.X, p.Y, z); B.circle(doc, v, q, .15 / M, (0, 0, 0))
    C.place(doc, v, q, u'%s · colector · %d salidas' % (co_el['code'], len(rows)), placed, cr, 'tag', z)
    return X.item(v, v.CropBox, u'%s · planta' % co_el['code'], 'plan', lvname, [co_el['code']], [], [co_el['id']])

def elevation(doc, ld, co_el, ga_el, vname, rows=()):
    e = ld.GetElement(DB.ElementId(Int64(co_el['id']))); p = P.loc(ld, co_el['id'])
    bb = e.get_BoundingBox(None)
    gb = ld.GetElement(DB.ElementId(Int64(ga_el['id']))).get_BoundingBox(None) if ga_el else None
    k = gb or bb   # look along the thin horizontal axis of the cabinet (its depth), toward its face
    f = DB.XYZ.BasisX if (k.Max.X - k.Min.X) < (k.Max.Y - k.Min.Y) else DB.XYZ.BasisY
    o = getattr(e, 'FacingOrientation', None)
    if o is not None and o.DotProduct(f) < 0: f = f.Negate()
    right = DB.XYZ.BasisZ.CrossProduct(f)
    zb = bb.Min.Z
    lo_z = min(zb, gb.Min.Z if gb else zb) - .3 / M; hi_z = max(bb.Max.Z, gb.Max.Z if gb else bb.Max.Z) + .3 / M
    v, bx = X.section(doc, DB.XYZ(p.X, p.Y, lo_z) + f * (.6 / M), right, -.9 / M, .9 / M, 0, hi_z - lo_z, 1.4 / M, vname)
    try: v.SetCategoryHidden(DB.ElementId(DB.BuiltInCategory.OST_Levels), True)
    except Exception: pass
    v.Scale = 10; v.DetailLevel = DB.ViewDetailLevel.Fine; doc.Regenerate(); fr = L.Frame(v); dims = []
    for el_, lab in ((bb, co_el['code']), (gb, u'Gabinete')):
        if el_ is None or (lab == co_el['code'] and gb is not None and el_.Min.IsAlmostEqualTo(gb.Min) and el_.Max.IsAlmostEqualTo(gb.Max)): continue   # same box as the cabinet: dimension once
        xs = sorted([fr.x(el_.Min), fr.x(el_.Max)]); zs = [el_.Min.Z - fr.o.Z, el_.Max.Z - fr.o.Z]
        dims.append(L.tick_dim(doc, fr, lab + u' ancho', xs, True, zs[1] + (.12 if lab != u'Gabinete' else .22) / M, tick=.03 / M))
        dims.append(L.tick_dim(doc, fr, lab + u' alto', zs, False, xs[1] + (.12 if lab != u'Gabinete' else .22) / M, tick=.03 / M))
    # the Hidroflex families show no geometry in section: draw the cabinet outline and both bars from their boxes
    o = v.Origin; k = gb or bb
    def pt(xw, zw): return DB.XYZ(o.X, o.Y, 0) + right * xw + DB.XYZ(0, 0, zw)
    def ln(a, b, w=None):
        c = doc.Create.NewDetailCurve(v, DB.Line.CreateBound(pt(*a), pt(*b)))
        return c
    xa, xb = sorted([(k.Min - o).DotProduct(right), (k.Max - o).DotProduct(right)]); za, zb2 = k.Min.Z, k.Max.Z
    for a, b in (((xa, za), (xb, za)), ((xb, za), (xb, zb2)), ((xb, zb2), (xa, zb2)), ((xa, zb2), (xa, za))): ln(a, b)
    zm = (za + zb2) / 2; m = .06 / M; n = max(len(rows), 1)
    for zz in (zm + .07 / M, zm - .03 / M):
        ln((xa + m, zz), (xb - m, zz)); ln((xa + m, zz + .02 / M), (xb - m, zz + .02 / M))
        for i in range(n):
            xx = xa + m + (i + .5) * (xb - xa - 2 * m) / n; ln((xx, zz), (xx, zz - .04 / M))
    L.tn(doc, v.Id, pt(xa if v.RightDirection.DotProduct(right) > 0 else xb, za - .06 / M), u'ida (arriba) / retorno (abajo) · %d salidas' % len(rows), 'text')
    return X.item(v, bx, u'%s · alzado frontal con gabinete' % co_el['code'], 'section', u'Colector', [co_el['code'], ga_el['code'] if ga_el else u''], dims, [co_el['id']] + ([ga_el['id']] if ga_el else []))

def scheme(doc, co_el, rows, tes, risers, vname):
    v = C.drafting(doc, vname, 20); n = max(len(rows), 1); W = .50 * n
    C.rect(doc, v, 0, 0, W, .06, 'acero', 4)                                   # barra de ida
    C.rect(doc, v, 0, -.12, W, -.06, None, 4)                                  # barra de retorno
    L.tn(doc, v.Id, C.V((-.05, .40)), u'%s · ida (arriba) / retorno (abajo)' % co_el['code'], 'room')
    for i, (sn, x, c, k) in enumerate(rows):
        cx = .25 + i * .50; col = P.PAL[i % len(P.PAL)]
        C.dl(doc, v, (cx - .03, 0), (cx - .03, -.45), 3); C.dl(doc, v, (cx + .03, -.12), (cx + .03, -.45), 3)
        L.tn(doc, v.Id, C.V((cx - .06, .14)), sn, 'tag')
        t = u'%s\n%s\n%s ml\n%s m²\n%s m/m²\n%s%s' % (x['code'], R1.clean(x['room'] or u''), c2(x['length_m']), c2(x['area_m2']), c2(x['density']), c['status'], u'\n(cercanía)' if c['method'] != u'conectividad' else u'')
        L.tn(doc, v.Id, C.V((cx - .20, -.50)), t, 'text')
    tot_l = sum(x['length_m'] for _, x, _, _ in rows); tot_a = sum(x['area_m2'] for _, x, _, _ in rows)
    blocks = [(u'Cuadro %s' % co_el['code'], [u'Salidas usadas: %d' % len(rows), u'Serpentín: %s ml · %s m² servidos' % (c2(tot_l), c2(tot_a)),
               u'Completos (≥ 4 m/m²): %d de %d' % (len([r for r in rows if r[2]['status'] == u'completo']), len(rows)), u'Asignados por cercanía: %d' % len([r for r in rows if r[2]['method'] != u'conectividad'])]),
              (u'Termostatos que comanda', tes or [u'(ninguno identificado)']), (u'Montantes de llegada', risers or [u'(ninguno en el modelo)'])]
    C.legend(doc, v, 0, -1.6 / M, 0, blocks, [])
    return C.item(doc, v, u'%s · esquema de salidas' % co_el['code'], [r[1]['code'] for r in rows], [])

def sheet(doc, ld, co, plan, cc, curves, circ):
    co_el = next(x for x in plan if x['code'] == co); ga_el = next((x for x in plan if x['code'] == CABINET[co]), None)
    rows = outlets(plan, cc, circ, co)
    rooms = set(x['room'] for _, x, _, _ in rows)
    tes = [u'%s · %s' % (x['code'], R1.clean(x['room'])) for x in plan if x['kind'] == 'TE' and x.get('room') in rooms]
    lvn = co_el['level']; dis = [x for x in plan if x['kind'] == 'DI']
    cp = P.loc(ld, co_el['id']); risers = []   # only risers arriving at this collector: vertical DI segments within 1,5 m of it
    for x in dis:
        n = len([1 for pid in x['pipeIds'] for cv in [curves.get(str(pid))] if cv and abs(cv[5] - cv[2]) > .3 / M and abs(cv[0] - cv[3]) + abs(cv[1] - cv[4]) < .05 / M
                 and math.hypot(cv[0] - cp.X, cv[1] - cp.Y) < 1.5 / M])
        if n: risers.append(u'%s · %d tramos verticales junto al colector' % (x['code'], n))
    its = [plan_around(doc, ld, co_el, lvn, PRE + co + ' PLANTA', plan, rows, curves), elevation(doc, ld, co_el, ga_el, PRE + co + ' ALZADO', rows), scheme(doc, co_el, rows, tes, risers, PRE + co + ' ESQUEMA')]
    old = list(L.SCALES); L.SCALES[:] = [10, 20, 25]
    try: s = S.lay_sheet(doc, 'CLI-' + co, u'Colector %s · detalle' % co, u'%s · %s · %d circuitos · planta, alzado con gabinete y esquema de salidas' % (co_el['label'], lvn, len(rows)), its, P.FOOT, plan_region=True, rubro=P.RUBRO, sheet_name=u'Climatización · ' + co)
    finally: L.SCALES[:] = old
    return dict(s, kind='element', element=co, elementId=str(co_el['id']), elementKind='CO', level=lvn, sector=u'Colector',
                outlets=[{'outlet': sn, 'code': x['code'], 'room': x['room'], 'connector': k, 'method': c['method']} for sn, x, c, k in rows])

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L, S, X.F, X, None])
    assert ld is not None, 'Abrir Casa-Angel-DOC-Climatizacion.rvt'
    part = job['part']
    if part == 'debug':
        r = {}
        for i in (2243525, 2243527, 2263387, 2263389):
            e = ld.GetElement(DB.ElementId(Int64(i))); b = e.get_BoundingBox(None); q = P.loc(ld, i)
            r[i] = {'min': [round(b.Min.X * M, 3), round(b.Min.Y * M, 3), round(b.Min.Z * M, 3)], 'max': [round(b.Max.X * M, 3), round(b.Max.Y * M, 3), round(b.Max.Z * M, 3)],
                    'loc': [round(q.X * M, 3), round(q.Y * M, 3), round(q.Z * M, 3)], 'facing': str(getattr(e, 'FacingOrientation', None)), 'hand': str(getattr(e, 'HandOrientation', None)),
                    'cat': e.Category.Name, 'super': str(getattr(e, 'SuperComponent', None) and e.SuperComponent.Id)}
        return r
    path = os.path.join(OUT, 'cli32-collectors.json')
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
        B.plain(doc, 'ADER CLI R32 - borrar colectores', wipe); os.remove(path)
    L.register_font()
    plan, cc, curves = P.data()
    circ = [c for s in R1.read(os.path.join(OUT, 'cli32-plans.json'))['sheets'] for c in s['circuits']]
    sheets = B.plain(doc, 'ADER CLI R32 - colectores', lambda: [sheet(doc, ld, co, plan, cc, curves, circ) for co in ('CO-N', 'CO-S')])
    for sh in sheets:
        for x in sh['views']: x.pop('view', None)
    R1.write(path, {'part': 'collectors', 'revision': 'R32', 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'sheets': [(sh['number'], [x['scale'] for x in sh['views']], [(o['outlet'], o['code']) for o in sh['outlets']]) for sh in sheets]}
