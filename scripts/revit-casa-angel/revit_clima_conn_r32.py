# -*- coding: utf-8 -*-
"""R32 read-only: circuit -> collector by MEP connectivity (Connector.AllRefs) from CO-N / CO-S, plus each pipe's
centerline (for drawing the serpentine with detail lines in the DOC file). Runs in the pilot or a DOC file (via the link)."""
import os, imp
from Autodesk.Revit import DB
from System import Int64

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_cliconn', os.path.join(ROOT, 'revit_openings_r4.py'))
CTX = imp.load_source('ader_docctx_r30_cliconn', os.path.join(ROOT, 'docctx_r30.py'))
M = L.M; R1 = L.R1; OUT = L.OUT
COLLECTORS = {'CO-N': 2243525, 'CO-S': 2263387}

def cm(e):
    try:
        if isinstance(e, DB.FamilyInstance): return e.MEPModel.ConnectorManager if e.MEPModel else None
        return e.ConnectorManager
    except Exception: return None

def walk(ld, start):
    """BFS from one collector through pipes/fittings/accessories; does not pass through other equipment."""
    seen = set(); out = {}  # element id -> collector connector index (outlet) it came from
    s = ld.GetElement(DB.ElementId(Int64(start))); m = cm(s)
    if m is None: return out, 0
    q = []; n = 0
    for k, c in enumerate(m.Connectors):
        n += 1
        for r in c.AllRefs:
            o = r.Owner
            if o is not None and o.Id.Value != start: q.append((o, k))
    while q:
        e, k = q.pop()
        i = e.Id.Value
        if i in seen: continue
        seen.add(i)
        cat = e.Category.Id.Value if e.Category else 0
        if cat == int(DB.BuiltInCategory.OST_MechanicalEquipment): continue
        out[i] = k
        mm = cm(e)
        if mm is None: continue
        for c in mm.Connectors:
            for r in c.AllRefs:
                o = r.Owner
                if o is not None and o.Id.Value not in seen and o.Id.Value != start: q.append((o, k))
    return out, n

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L]) or doc
    plan = L.read('hvac-plan')['elements']
    reach = {}; outlets = {}
    for k, i in COLLECTORS.items(): reach[k], outlets[k] = walk(ld, i)
    circuits = []; pipes = {}
    for x in plan:
        ids = x.get('pipeIds') or []
        hit = dict((k, [p for p in ids if p in reach[k]]) for k in COLLECTORS)
        best = max(COLLECTORS, key=lambda k: len(hit[k])) if ids else None
        rec = {'code': x['code'], 'kind': x['kind'], 'room': x.get('room'), 'level': x.get('levelCode'), 'pipes': len(ids),
               'reached': dict((k, len(v)) for k, v in hit.items())}
        if best and hit[best]:
            outs = sorted(set(reach[best][p] for p in hit[best]))
            rec.update(collector=best, method='conectividad', outlets=outs)
        else: rec.update(collector=None, method='sin camino')
        circuits.append(rec)
        for p in ids:
            e = ld.GetElement(DB.ElementId(Int64(p)))
            c = getattr(e.Location, 'Curve', None) if e else None
            if c is not None:
                a, b = c.GetEndPoint(0), c.GetEndPoint(1)
                pipes[str(p)] = [round(a.X, 4), round(a.Y, 4), round(a.Z, 4), round(b.X, 4), round(b.Y, 4), round(b.Z, 4)]
    res = {'readAt': L.now(), 'collectors': dict((k, {'id': COLLECTORS[k], 'connectors': outlets[k], 'reached': len(reach[k])}) for k in COLLECTORS),
           'circuits': circuits, 'pipeCurves_ft': pipes}
    R1.write(os.path.join(OUT, 'cli32-conn.json'), res)
    return {'status': 'success', 'collectors': res['collectors'],
            'summary': [(c['code'], c.get('collector'), c['method'], c['reached']) for c in circuits]}
