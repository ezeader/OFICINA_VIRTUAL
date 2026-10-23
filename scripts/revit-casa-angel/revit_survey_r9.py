# -*- coding: utf-8 -*-
"""R9 read-only jobs: opening survey data (materials, params, curtain panels) and
projection of each element's box onto every exported view. No transaction is opened."""
import os, imp, datetime
from Autodesk.Revit import DB
from System import Int64

ROOT = os.path.dirname(__file__)
OUT = os.path.join(ROOT, 'openings-r4')
R1 = imp.load_source('ader_survey_r9_lib', os.path.join(ROOT, 'revit_openings_r1.py'))
clean = R1.clean; name = R1.name; eid = R1.eid; xyz = R1.xyz
M = .3048; M2 = M * M

def el(doc, i): return doc.GetElement(DB.ElementId(Int64(int(i))))
def u(s):
    if s is None: return u''
    return s if isinstance(s, unicode) else clean(s)

def pdump(e):
    out = {}
    if e is None: return out
    for p in e.Parameters:
        try:
            if not p.HasValue: continue
            if p.StorageType == DB.StorageType.Double: v = p.AsDouble()
            elif p.StorageType == DB.StorageType.String: v = u(p.AsString())
            elif p.StorageType == DB.StorageType.Integer: v = p.AsInteger()
            else: v = u(p.AsValueString())
            out[u(p.Definition.Name)] = {'v': v, 'txt': u(p.AsValueString() or u'')}
        except: pass
    return out

def mats(doc, e):
    rows = []
    try:
        for i in e.GetMaterialIds(False):
            m = doc.GetElement(i)
            rows.append({'name': u(name(m)), 'class': u(m.MaterialClass), 'area_m2': e.GetMaterialArea(i, False) * M2, 'volume_m3': e.GetMaterialVolume(i) * M2 * M})
    except: pass
    return rows

def survey(doc):
    reg = R1.read(os.path.join(OUT, 'plan.json'))
    rows = []
    for it in reg['items']:
        e = el(doc, it['id']); t = doc.GetElement(e.GetTypeId())
        row = {'id': it['id'], 'code': it['code'], 'category': u(e.Category.Name), 'type': u(name(t)), 'family': u(getattr(t, 'FamilyName', u'')),
               'instance': pdump(e), 'typeParams': pdump(t), 'materials': mats(doc, e)}
        if isinstance(e, DB.FamilyInstance):
            row['subComponents'] = []
            for sid in e.GetSubComponentIds():
                s = doc.GetElement(sid); st = doc.GetElement(s.GetTypeId())
                row['subComponents'].append({'id': eid(s), 'family': u(getattr(st, 'FamilyName', u'')), 'type': u(name(st)), 'materials': mats(doc, s)})
        if isinstance(e, DB.Wall) and e.CurtainGrid:
            panels = []
            for pid in e.CurtainGrid.GetPanelIds():
                pnl = doc.GetElement(pid); pt = doc.GetElement(pnl.GetTypeId())
                w = pnl.get_Parameter(DB.BuiltInParameter.CURTAIN_WALL_PANELS_WIDTH); h = pnl.get_Parameter(DB.BuiltInParameter.CURTAIN_WALL_PANELS_HEIGHT)
                a = pnl.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED)
                bb = pnl.get_BoundingBox(None); c = e.Location.Curve; dvec = (c.GetEndPoint(1) - c.GetEndPoint(0)).Normalize()
                geo = None
                if bb:
                    xs = [DB.XYZ(x, y, 0).DotProduct(dvec) for x in [bb.Min.X, bb.Max.X] for y in [bb.Min.Y, bb.Max.Y]]
                    geo = {'width_m': (max(xs) - min(xs)) * M, 'height_m': (bb.Max.Z - bb.Min.Z) * M}
                panels.append({'bbox': geo,'id': eid(pnl), 'type': u(name(pt)), 'family': u(getattr(pt, 'FamilyName', u'')),
                               'width_m': w.AsDouble() * M if w and w.HasValue else None, 'height_m': h.AsDouble() * M if h and h.HasValue else None,
                               'area_m2': a.AsDouble() * M2 if a and a.HasValue else None, 'materials': [m['name'] for m in mats(doc, pnl)],
                               'thickness_m': (pt.get_Parameter(DB.BuiltInParameter.CURTAIN_WALL_SYSPANEL_THICKNESS).AsDouble() * M) if pt and pt.get_Parameter(DB.BuiltInParameter.CURTAIN_WALL_SYSPANEL_THICKNESS) else None})
            mull = []
            for mid in e.CurtainGrid.GetMullionIds():
                m = doc.GetElement(mid); mt = doc.GetElement(m.GetTypeId())
                L = m.get_Parameter(DB.BuiltInParameter.CURVE_ELEM_LENGTH)
                mull.append({'id': eid(m), 'type': u(name(mt)), 'length_m': L.AsDouble() * M if L and L.HasValue else None, 'materials': [x['name'] for x in mats(doc, m)],
                             'typeParams': dict((k, v['txt']) for k, v in pdump(mt).items() if k in (u'Width on side 1', u'Width on side 2', u'Thickness', u'Profile', u'Material'))})
            row['panels'] = panels; row['mullions'] = mull
        rows.append(row)
    R1.write(os.path.join(OUT, 'survey.json'), {'readAt': datetime.datetime.utcnow().isoformat() + 'Z', 'items': rows})
    return {'status': 'success', 'items': len(rows), 'panels': sum(len(r.get('panels', [])) for r in rows)}

# ---------------------------------------------------------------- projection

def viewport_of(doc, v):
    for vp in DB.FilteredElementCollector(doc).OfClass(DB.Viewport):
        if vp.ViewId == v.Id: return vp
    return None

def to_sheet_fn(doc, v, vp):
    try:
        mp = v.GetModelToProjectionTransforms()[0].GetModelToProjectionTransform()
        ps = vp.GetProjectionToSheetTransform()
        return lambda p: ps.OfPoint(mp.OfPoint(p)), 'api'
    except Exception:
        # Fallback: crop centre maps to viewport box centre at 1/scale.
        cb = v.CropBox; inv = cb.Transform.Inverse; c = vp.GetBoxCenter(); s = float(v.Scale)
        cu = (cb.Min.X + cb.Max.X) / 2; cv = (cb.Min.Y + cb.Max.Y) / 2
        def f(p):
            q = inv.OfPoint(p); return DB.XYZ(c.X + (q.X - cu) / s, c.Y + (q.Y - cv) / s, 0)
        return f, 'fallback'

def project_job(doc, job):
    """job['views'] = [{id, box:[[x,y,z],[x,y,z]], margin_ft, elements:[ids]}] -> sheet boxes of each element."""
    req = R1.read(os.path.join(OUT, job.get('request', 'project-request.json'))); out = []
    for r in req['views']:
        v = el(doc, r['id'])
        if v is None: out.append({'id': r['id'], 'error': 'missing view'}); continue
        vp = viewport_of(doc, v)
        if vp is None: out.append({'id': r['id'], 'error': 'not on sheet'}); continue
        fn, method = to_sheet_fn(doc, v, vp); o = vp.GetBoxOutline()
        (bx0, by0, _), (bx1, by1, _) = r['box']; m = r['margin_ft']
        rx0, ry0, rx1, ry1 = bx0 - m, by0 - m, bx1 + m, by1 + m
        rows = []
        for i in r['elements']:
            e = el(doc, i); b = e.get_BoundingBox(None) if e else None
            if b is None: continue
            pts = [fn(DB.XYZ(x, y, z)) for x in [b.Min.X, b.Max.X] for y in [b.Min.Y, b.Max.Y] for z in [b.Min.Z, b.Max.Z]]
            sx0 = min(p.X for p in pts); sx1 = max(p.X for p in pts); sy0 = min(p.Y for p in pts); sy1 = max(p.Y for p in pts)
            f = [(sx0 - rx0) / (rx1 - rx0), (ry1 - sy1) / (ry1 - ry0), (sx1 - rx0) / (rx1 - rx0), (ry1 - sy0) / (ry1 - ry0)]
            clipped = any(x < -.001 or x > 1.001 for x in f)
            rows.append({'elementId': str(i), 'box': [max(0., min(1., x)) for x in f], 'clipped': clipped})
        drift = max(abs(o.MinimumPoint.X - bx0), abs(o.MinimumPoint.Y - by0), abs(o.MaximumPoint.X - bx1), abs(o.MaximumPoint.Y - by1))
        out.append({'id': r['id'], 'method': method, 'boxDrift_ft': drift, 'elements': rows})
    R1.write(os.path.join(OUT, job.get('output', 'view-elements.json')), out)
    return {'status': 'success', 'views': len(out), 'errors': len([x for x in out if x.get('error')]),
            'methods': sorted(set(x.get('method') for x in out if x.get('method'))), 'maxDrift_ft': max([x.get('boxDrift_ft', 0) for x in out] or [0]),
            'clipped': sum(1 for x in out for y in x.get('elements', []) if y['clipped'])}

def run(doc, uidoc, job):
    assert os.path.basename(doc.PathName).lower() == 'casa-angel-piloto-documentacion.rvt'
    if job.get('part') == 'project': return project_job(doc, job)
    return survey(doc)
