# -*- coding: utf-8 -*-
"""R39 Ascensor A1 (user-approved in this session: "Sí, hacelo"; backup -antes-ascensor-R35 first). Runs in the MAIN model.
part 'shaft' : west partitions 368795 (PB) + 1156693 (PA) 10 cm west (hosted Center Openings follow); floor PA 1011940 and
               ceiling 2488781 sketch edges at x 4,243 -> 4,143; reticulado 2250136 Longitud (X) -0,10; wine racks 870143/1452870
               moved 10 cm west. Shaft becomes 1,40 x 2,60.
part 'roof'  : framing over the Ø1,40 circle trimmed to a brochal rectangle x 4,243..5,643 · y 9,318..10,718 (pieces beyond it
               re-created as copies, nothing deleted); 4 brochal LVL 50x150; roof opening on 1086089; 'linterna': flat roof
               on the rectangle with underside >= +8,50, 3 solid walls and a glazed east face in the plane of MC-1020586.
Each step is its own transaction (failures: rollback, logged)."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_ascmodel', os.path.join(ROOT, 'revit_openings_r4.py'))
M = L.M; u = L.u
X0, X1, Y0, Y1 = 4.243, 5.643, 9.318, 10.718      # brochal rectangle (m): circle Ø1,40 on the shaft axis (4,943 · 10,018)
DX = -0.10

def E(doc, i): return doc.GetElement(DB.ElementId(Int64(i)))
def V(x, y, z): return DB.XYZ(x / M, y / M, z / M)
def nm(e):
    try: return u(DB.Element.Name.GetValue(e))
    except Exception: return u''

def step(doc, label, fn, log):
    tx = DB.Transaction(doc, 'ADER ASC R39 - ' + label); tx.Start()
    try:
        r = fn(); st = tx.Commit()
        log.append({'step': label, 'status': str(st), 'result': r})
        return st == DB.TransactionStatus.Committed
    except Exception as ex:
        if tx.GetStatus() == DB.TransactionStatus.Started: tx.RollBack()
        import traceback
        log.append({'step': label, 'status': 'error', 'error': str(ex), 'trace': traceback.format_exc()[-600:]}); return False

def sketch_shift(doc, host_id, xold, xnew):
    """move every sketch-line end at x = xold to xnew (floor / ceiling boundary), via SketchEditScope."""
    host = E(doc, host_id); sk = doc.GetElement(host.SketchId); tol = .005 / M; moved = 0
    scope = DB.SketchEditScope(doc, 'ADER ASC R39 - borde ' + str(host_id)); scope.Start(sk.Id)
    tx = DB.Transaction(doc, 'ADER ASC R39 - lineas ' + str(host_id)); tx.Start()
    try:
        for i in sk.GetAllElements():
            ce = doc.GetElement(i)
            if not isinstance(ce, DB.CurveElement): continue
            c = ce.GeometryCurve
            if not isinstance(c, DB.Line): continue
            a, b = c.GetEndPoint(0), c.GetEndPoint(1)
            na = DB.XYZ(xnew / M, a.Y, a.Z) if abs(a.X - xold / M) < tol else a
            nb = DB.XYZ(xnew / M, b.Y, b.Z) if abs(b.X - xold / M) < tol else b
            if (na.IsAlmostEqualTo(a) and nb.IsAlmostEqualTo(b)) or na.DistanceTo(nb) < .01: continue
            ce.SetGeometryCurve(DB.Line.CreateBound(na, nb), True); moved += 1
        tx.Commit()
        scope.Commit(Fail())
    except Exception:
        if tx.GetStatus() == DB.TransactionStatus.Started: tx.RollBack()
        if scope.IsActive: scope.Cancel()
        raise
    return moved

class Fail(DB.IFailuresPreprocessor):
    def PreprocessFailures(self, fa):
        for f in list(fa.GetFailureMessages()):
            if f.GetSeverity() == DB.FailureSeverity.Warning: fa.DeleteWarning(f)
            else: return DB.FailureProcessingResult.ProceedWithRollBack
        return DB.FailureProcessingResult.Continue

def shaft(doc, log):
    step(doc, 'tabiques 10 cm al oeste', lambda: [DB.ElementTransformUtils.MoveElement(doc, DB.ElementId(Int64(i)), V(DX, 0, 0)) for i in (368795, 1156693)] and 2, log)
    for hid in (1011940, 2488781):
        try: log.append({'step': 'borde %d' % hid, 'status': 'Committed', 'result': sketch_shift(doc, hid, X0, X0 + DX)})
        except Exception as ex: log.append({'step': 'borde %d' % hid, 'status': 'error', 'error': str(ex)})
    def ret():
        r = E(doc, 2250136); p = r.LookupParameter(u'Longitud (X)'); old = p.AsDouble() * M; p.Set((old + DX) / M); return [round(old, 4), round(old + DX, 4)]
    step(doc, 'reticulado -0,10', ret, log)
    step(doc, 'vinotecas 10 cm al oeste', lambda: [DB.ElementTransformUtils.MoveElement(doc, DB.ElementId(Int64(i)), V(DX, 0, 0)) for i in (870143, 1452870)] and 2, log)

def clip(a, b):
    """parametric interval of segment a-b inside the rectangle (Liang–Barsky); None if it does not cross it."""
    t0, t1 = 0., 1.; dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] - X0), (dx, X1 - a[0]), (-dy, a[1] - Y0), (dy, Y1 - a[1])):
        if abs(p) < 1e-9:
            if q < 0: return None
            continue
        r = q / p
        if p < 0: t0 = max(t0, r)
        else: t1 = min(t1, r)
    return (t0, t1) if t1 - t0 > 1e-4 else None

def roof(doc, log):
    ids = [1087410, 1087610, 1088057, 1090014, 1090563, 1090857, 1090438, 1090462, 1090674, 1090675]
    steps = job_steps[0]
    inside = []
    def trim():
        out = []
        for i in ids:
            e = E(doc, i); c = e.Location.Curve; A, Bp = c.GetEndPoint(0), c.GetEndPoint(1)
            a = (A.X * M, A.Y * M); b = (Bp.X * M, Bp.Y * M); iv = clip(a, b)
            if iv is None: out.append((i, 'fuera')); continue
            t0, t1 = iv; P = lambda t: A + (Bp - A) * t
            if t0 <= 1e-4 and t1 >= 1 - 1e-4: inside.append(i); out.append((i, 'entera dentro')); continue
            if t0 > 1e-4 and t1 < 1 - 1e-4:      # crosses: keep A..t0 on this element, new beam (same type) for t1..B
                lv_ = next(l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if nm(l) == u'03. Planta de Techos')
                nb = doc.Create.NewFamilyInstance(DB.Line.CreateBound(P(t1), Bp), e.Symbol, lv_, DB.Structure.StructuralType.Beam)
                e.Location.Curve = DB.Line.CreateBound(A, P(t0)); out.append((i, 'partida', nb.Id.IntegerValue))
            elif t0 <= 1e-4: e.Location.Curve = DB.Line.CreateBound(P(t1), Bp); out.append((i, 'recortada inicio'))
            else: e.Location.Curve = DB.Line.CreateBound(A, P(t0)); out.append((i, 'recortada fin'))
        return out
    if 'trim' in steps: step(doc, 'cortar estructura sobre el hueco', trim, log)
    cab = E(doc, 1090014); sym = cab.Symbol; lev = doc.GetElement(cab.LevelId) if cab.LevelId.IntegerValue > 0 else next(l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if nm(l) == u'03. Planta de Techos')
    zb = 7.95
    def brochal():
        made = []
        pts = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
        for k in range(4):
            a, b = pts[k], pts[(k + 1) % 4]
            fi = doc.Create.NewFamilyInstance(DB.Line.CreateBound(V(a[0], a[1], zb), V(b[0], b[1], zb)), sym, lev, DB.Structure.StructuralType.Beam)
            fi.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK).Set(u'ASC-BR-%02d' % (k + 1)); made.append(fi.Id.IntegerValue)
        return made
    if 'brochal' in steps: step(doc, 'brochal LVL 50x150', brochal, log)
    def opening():
        rf = E(doc, 1086089); ca = DB.CurveArray(); pts = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
        for k in range(4):
            a, b = pts[k], pts[(k + 1) % 4]; ca.Append(DB.Line.CreateBound(V(a[0], a[1], 8.5), V(b[0], b[1], 8.5)))
        return doc.Create.NewOpening(rf, ca, True).Id.IntegerValue
    if 'opening' in steps: step(doc, 'abertura en la cubierta', opening, log)
    techos = next(l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if nm(l) == u'03. Planta de Techos')
    def lantern():
        made = {}
        rt = next((t for t in DB.FilteredElementCollector(doc).OfClass(DB.RoofType) if u'Generic' in nm(t) or u'Gen' in nm(t)), None) or next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.RoofType))
        ca = DB.CurveArray(); e_ = .10; pts = [(X0 - e_, Y0 - e_), (X1 + e_, Y0 - e_), (X1 + e_, Y1 + e_), (X0 - e_, Y1 + e_)]
        for k in range(4):
            a, b = pts[k], pts[(k + 1) % 4]; ca.Append(DB.Line.CreateBound(V(a[0], a[1], techos.Elevation * M), V(b[0], b[1], techos.Elevation * M)))
        import clr
        mc = clr.Reference[DB.ModelCurveArray](DB.ModelCurveArray())
        assert rt is not None, 'sin tipo de cubierta'
        r = doc.Create.NewFootPrintRoof(ca, techos, rt, mc)
        assert r is not None, 'NewFootPrintRoof devolvió null'
        po = r.get_Parameter(DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM)
        if po is not None: po.Set(.30 / M)                                                    # underside about +8,80 (≥ +8,50 clear)
        mk = r.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if mk is not None: mk.Set(u'ASC-LI-01')
        made['roof'] = r.Id.IntegerValue; made['roofType'] = nm(rt)
        wt = next((t for t in DB.FilteredElementCollector(doc).OfClass(DB.WallType) if nm(t) == u'Muro Interior 10cm'), None)
        ct = next((t for t in DB.FilteredElementCollector(doc).OfClass(DB.WallType) if nm(t) == u'Ventanales Patio'), None)
        assert wt is not None and ct is not None, 'tipos de muro: %s / %s' % (wt, ct)
        base = 7.40; top = 8.80; walls = []
        sides = [((X0 - .05, Y0 - .05), (X0 - .05, Y1 + .05), wt), ((X0 - .05, Y1 + .05), (X1 + .1, Y1 + .05), wt), ((X1 + .1, Y0 - .05), (X0 - .05, Y0 - .05), wt), ((5.743, Y0 - .05), (5.743, Y1 + .05), ct)]
        for a, b, t in sides:
            w = DB.Wall.Create(doc, DB.Line.CreateBound(V(a[0], a[1], 0), V(b[0], b[1], 0)), t.Id, techos.Id, (top - base) / M, (base - techos.Elevation * M) / M, False, False)
            mk = w.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
            if mk is not None: mk.Set(u'ASC-LI-%s' % (u'VID' if t is ct else u'MU'))
            walls.append(w.Id.IntegerValue)
        made['walls'] = walls; return made
    if 'lantern' in steps: step(doc, 'linterna', lantern, log)
    return inside

job_steps = [[]]

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    assert os.path.basename(doc.PathName).lower() == L.PILOT, 'Solo en el modelo principal'
    log = []; part = job['part']; job_steps[0] = job.get('steps') or ['trim', 'brochal', 'opening', 'lantern']
    if part == 'shaft': shaft(doc, log)
    elif part == 'fix':
        orig = dict((f['id'], f) for f in L.R1.read(os.path.join(L.OUT, 'asc39-check3.json'))['framing'])
        def retrim():
            SFU = DB.Structure.StructuralFramingUtils; out = []
            for i in (1090014, 1090438, 1090462, 1090674, 1090857, 1087410, 1087610, 1088057, 1090563):
                e = E(doc, i); f = orig[i]; A = V(*f['a']); Bp = V(*f['b'])
                iv = clip((f['a'][0], f['a'][1]), (f['b'][0], f['b'][1]))
                if iv is None: continue
                t0, t1 = iv; P = lambda t: A + (Bp - A) * t
                for k in (0, 1):
                    try: SFU.DisallowJoinAtEnd(e, k)
                    except Exception: pass
                nc = DB.Line.CreateBound(A, P(t0)) if t0 > 1e-4 else DB.Line.CreateBound(P(t1), Bp)
                e.Location.Curve = nc; c = e.Location.Curve
                out.append((i, [round(c.GetEndPoint(0).X * M, 3), round(c.GetEndPoint(0).Y * M, 3)], [round(c.GetEndPoint(1).X * M, 3), round(c.GetEndPoint(1).Y * M, 3)]))
            return out
        if job.get('retrim', True): step(doc, 'recorte con uniones liberadas', retrim, log)
        if job.get('dropOpening'): step(doc, 'quitar la abertura parcial 2489301 (creada en R39)', lambda: [x.IntegerValue for x in doc.Delete(DB.ElementId(Int64(2489301)))], log)
        def shaft_open():
            lv = dict((nm(l), l) for l in DB.FilteredElementCollector(doc).OfClass(DB.Level))
            ca = DB.CurveArray(); pts = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
            for k in range(4):
                a, b = pts[k], pts[(k + 1) % 4]; ca.Append(DB.Line.CreateBound(V(a[0], a[1], 6.0), V(b[0], b[1], 6.0)))
            o = doc.Create.NewOpening(lv[u'02. Planta Entrepiso'], lv[u'03. Planta de Techos'], ca)
            o.get_Parameter(DB.BuiltInParameter.WALL_BASE_OFFSET).Set(1.0 / M); o.get_Parameter(DB.BuiltInParameter.WALL_TOP_OFFSET).Set(.25 / M)
            return o.Id.IntegerValue
        step(doc, 'abertura de pasadizo en la cubierta (+7,00 a +8,75)', shaft_open, log)
    elif part == 'clear':   # keep the Ø1,338 cylinder free at its edge: brochal 2,5 cm outward, trimmed ends 5 cm outward
        def br():
            out = []
            for i, d in ((2489285, (0, -.025)), (2489286, (.025, 0)), (2489287, (0, .025)), (2489288, (-.025, 0))):
                e = E(doc, i)
                if e is None: continue
                c = e.Location.Curve; a, b = c.GetEndPoint(0), c.GetEndPoint(1)
                def ext(p, q):   # stretch along the axis by 2,5 cm each side so corners still meet
                    v = (q - p).Normalize(); return p - v * (.025 / M), q + v * (.025 / M)
                a2, b2 = ext(a, b); off = V(d[0], d[1], 0)
                e.Location.Curve = DB.Line.CreateBound(a2 + off, b2 + off); out.append(i)
            return out
        step(doc, 'brochal 2,5 cm hacia afuera', br, log)
        def ends():
            out = []; G = .05
            for i in (1090857, 1087410, 1087610, 1088057, 1090014, 1090563, 1090438, 1090462, 1090674, 2489312):
                e = E(doc, i)
                if e is None: continue
                c = e.Location.Curve; a, b = c.GetEndPoint(0), c.GetEndPoint(1)
                def inside(p): return X0 - G - .001 < p.X * M < X1 + G + .001 and Y0 - G - .001 < p.Y * M < Y1 + G + .001
                if inside(a) and not inside(b): a = a + (a - b).Normalize().Negate() * (G / M)
                elif inside(b) and not inside(a): b = b + (b - a).Normalize().Negate() * (G / M)
                else: continue
                e.Location.Curve = DB.Line.CreateBound(a, b); out.append(i)
            return out
        step(doc, 'extremos 5 cm hacia afuera', ends, log)
    elif part == 'state':
        out = {}
        for i in (1087410, 1087610, 1088057, 1090014, 1090563, 1090857, 1090438, 1090462, 1090674, 2489312, 2489285, 2489301, 2489337):
            e = E(doc, i)
            if e is None: out[i] = None; continue
            loc = getattr(e, 'Location', None); c = getattr(loc, 'Curve', None)
            out[i] = {'cat': e.Category.Name if e.Category else type(e).__name__, 'curve': [[round(c.GetEndPoint(k).X * M, 3), round(c.GetEndPoint(k).Y * M, 3), round(c.GetEndPoint(k).Z * M, 3)] for k in (0, 1)] if c else None,
                      'bbox': [round(v * M, 3) for v in (e.get_BoundingBox(None).Min.X, e.get_BoundingBox(None).Min.Y, e.get_BoundingBox(None).Max.X, e.get_BoundingBox(None).Max.Y)] if e.get_BoundingBox(None) else None}
        return {'status': 'success', 'state': out, 'modified': doc.IsModified}
    elif part == 'debug':
        out = []
        for hid in (1011940, 2488781):
            sk = doc.GetElement(E(doc, hid).SketchId)
            for i in sk.GetAllElements():
                ce = doc.GetElement(i); c = getattr(ce, 'GeometryCurve', None)
                out.append((hid, type(ce).__name__, [round(c.GetEndPoint(k).X * M, 4) for k in (0, 1)] if c else None))
        return {'status': 'success', 'debug': out}
    elif part == 'delete1090675':   # user OK in this session ("Sí, borralo"): the one LVL batten left inside the shaft circle
        step(doc, 'borrar listón 1090675', lambda: [x.IntegerValue for x in doc.Delete(DB.ElementId(Int64(1090675)))], log)
    elif part == 'roof': log.append({'insideToDelete': roof(doc, log)})
    else: raise Exception('Unknown part')
    doc.Save()
    L.R1.write(os.path.join(L.OUT, 'asc39-model-%s-%s.json' % (part, '-'.join(job_steps[0]))), {'readAt': L.now(), 'log': log})
    return {'status': 'success', 'log': log}
