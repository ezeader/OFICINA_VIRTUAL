# -*- coding: utf-8 -*-
"""R4 read-only inventory for Estructura and Climatizacion. IronPython 2.7.

No transaction is opened. Output: openings-r4/inventory-structure.json and
openings-r4/inventory-hvac.json.
"""
import os, re, datetime, imp
from Autodesk.Revit import DB

ROOT = os.path.dirname(__file__)
OUT = os.path.join(ROOT, 'openings-r4')
R1 = imp.load_source('ader_inventory_r4_lib', os.path.join(ROOT, 'revit_openings_r1.py'))
clean = R1.clean; name = R1.name; eid = R1.eid; xyz = R1.xyz
M = .3048; M2 = M * M; M3 = M * M * M
KEYS = re.compile(u'(radiant|serpent|losa radiante|piso radiante|calefac|climat|colector|manifold|bomba|inverter|aerotermo|heat|pex|carpeta|contrapiso|aislac|aislante|poliestireno|eps|termo|frio|calor)', re.I)

def u(s):
    if s is None: return u''
    return s if isinstance(s, unicode) else clean(s)

def B(n):
    return getattr(DB.BuiltInParameter, n, None)

def pval(e, bip, scale=1.):
    if bip is None: return None
    try:
        p = e.get_Parameter(bip)
        if p is None or not p.HasValue: return None
        if p.StorageType == DB.StorageType.Double: return p.AsDouble() * scale
        if p.StorageType == DB.StorageType.Integer: return p.AsInteger()
        if p.StorageType == DB.StorageType.String: return u(p.AsString())
        return u(p.AsValueString())
    except: return None

def lname(doc, lid):
    l = doc.GetElement(lid) if lid and lid != DB.ElementId.InvalidElementId else None
    return u(name(l)) if l else u'(sin nivel)'

def base_level(doc, e):
    for bip in [B('WALL_BASE_CONSTRAINT'), B('FAMILY_BASE_LEVEL_PARAM'),
                B('SCHEDULE_LEVEL_PARAM'), B('INSTANCE_REFERENCE_LEVEL_PARAM'),
                B('RBS_START_LEVEL_PARAM')]:
        try:
            if bip is None: continue
            p = e.get_Parameter(bip)
            if p and p.AsElementId() != DB.ElementId.InvalidElementId: return lname(doc, p.AsElementId())
        except: pass
    return lname(doc, e.LevelId)

def materials(doc, e):
    out = []
    try:
        for i in e.GetMaterialIds(False):
            m = doc.GetElement(i)
            out.append({'name': u(name(m)), 'area_m2': e.GetMaterialArea(i, False) * M2, 'volume_m3': e.GetMaterialVolume(i) * M3})
    except: pass
    return out

def layers(doc, t):
    try:
        cs = t.GetCompoundStructure()
        if cs is None: return []
        return [{'function': str(l.Function), 'material': u(name(doc.GetElement(l.MaterialId))) if l.MaterialId != DB.ElementId.InvalidElementId else u'', 'thickness_m': l.Width * M} for l in cs.GetLayers()]
    except: return []

def collect(doc, bic):
    return list(DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType())

def host_row(doc, e):
    t = doc.GetElement(e.GetTypeId())
    row = {'id': eid(e), 'type': u(name(t)) if t else u'', 'family': u(t.FamilyName) if t else u'', 'level': base_level(doc, e),
           'area_m2': pval(e, B('HOST_AREA_COMPUTED'), M2), 'volume_m3': pval(e, B('HOST_VOLUME_COMPUTED'), M3),
           'mark': pval(e, B('ALL_MODEL_MARK')), 'comments': pval(e, B('ALL_MODEL_INSTANCE_COMMENTS')),
           'bbox': R1.bbox(e)}
    try: row['structural'] = bool(e.get_Parameter(B('WALL_STRUCTURAL_SIGNIFICANT')).AsInteger()) if isinstance(e, DB.Wall) else bool(pval(e, B('FLOOR_PARAM_IS_STRUCTURAL')))
    except: row['structural'] = None
    if isinstance(e, DB.Wall):
        row['length_m'] = pval(e, B('CURVE_ELEM_LENGTH'), M); row['height_m'] = pval(e, B('WALL_USER_HEIGHT_PARAM'), M)
        row['width_m'] = e.Width * M; row['kind'] = str(e.WallType.Kind)
        row['topConstraint'] = lname(doc, e.get_Parameter(B('WALL_HEIGHT_TYPE')).AsElementId())
        row['baseOffset_m'] = pval(e, B('WALL_BASE_OFFSET'), M)
    if isinstance(e, DB.Floor):
        row['thickness_m'] = pval(e, B('FLOOR_ATTR_THICKNESS_PARAM'), M); row['offset_m'] = pval(e, B('FLOOR_HEIGHTABOVELEVEL_PARAM'), M)
        row['perimeter_m'] = pval(e, B('HOST_PERIMETER_COMPUTED'), M)
    row['materials'] = materials(doc, e)
    return row

def fam_row(doc, e):
    t = doc.GetElement(e.GetTypeId())
    row = {'id': eid(e), 'type': u(name(t)) if t else u'', 'family': u(t.FamilyName) if t else u'', 'level': base_level(doc, e),
           'mark': pval(e, B('ALL_MODEL_MARK')), 'volume_m3': pval(e, B('HOST_VOLUME_COMPUTED'), M3),
           'length_m': pval(e, B('INSTANCE_LENGTH_PARAM'), M) or pval(e, B('CURVE_ELEM_LENGTH'), M),
           'structuralMaterial': u(name(doc.GetElement(e.StructuralMaterialId))) if hasattr(e, 'StructuralMaterialId') and e.StructuralMaterialId != DB.ElementId.InvalidElementId else u'',
           'bbox': R1.bbox(e), 'materials': materials(doc, e)}
    try: row['structuralType'] = str(e.StructuralType)
    except: pass
    return row

def summarize(rows, keyf):
    out = {}
    for r in rows:
        k = keyf(r); s = out.setdefault(k, {'count': 0, 'area_m2': 0., 'volume_m3': 0., 'length_m': 0.})
        s['count'] += 1
        for f in ['area_m2', 'volume_m3', 'length_m']:
            if r.get(f): s[f] += r[f]
    return [dict(key=k, **v) for k, v in sorted(out.items())]

def warnings_for(doc, ids):
    ids = set(ids); out = []
    for w in doc.GetWarnings():
        f = [int(i.Value) for i in w.GetFailingElements()] + [int(i.Value) for i in w.GetAdditionalElements()]
        if ids.intersection(f): out.append({'text': u(w.GetDescriptionText()), 'elementIds': f})
    return out

def structure(doc):
    walls = [host_row(doc, e) for e in collect(doc, DB.BuiltInCategory.OST_Walls)]
    floors = [host_row(doc, e) for e in collect(doc, DB.BuiltInCategory.OST_Floors)]
    found = [host_row(doc, e) for e in collect(doc, DB.BuiltInCategory.OST_StructuralFoundation)]
    framing = [fam_row(doc, e) for e in collect(doc, DB.BuiltInCategory.OST_StructuralFraming)]
    columns = [fam_row(doc, e) for e in collect(doc, DB.BuiltInCategory.OST_StructuralColumns)]
    archcols = [fam_row(doc, e) for e in collect(doc, DB.BuiltInCategory.OST_Columns)]
    roofs = [host_row(doc, e) for e in collect(doc, DB.BuiltInCategory.OST_Roofs)]
    stairs = [{'id': eid(e), 'type': u(name(doc.GetElement(e.GetTypeId()))), 'level': base_level(doc, e)} for e in collect(doc, DB.BuiltInCategory.OST_Stairs)]
    rebar = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rebar).WhereElementIsNotElementType().GetElementCount()
    concrete = lambda r: any(re.search(u'hormig|concrete|H\\d\\d', m['name'], re.I) for m in r.get('materials', [])) or re.search(u'hormig|concrete|H[AoO]', r['type'], re.I)
    wall_types = {}
    for t in DB.FilteredElementCollector(doc).OfClass(DB.WallType):
        wall_types[u(name(t))] = {'kind': str(t.Kind), 'width_m': t.Width * M if t.Kind == DB.WallKind.Basic else None, 'layers': layers(doc, t), 'function': pval(t, B('FUNCTION_PARAM'))}
    floor_types = {}
    for t in DB.FilteredElementCollector(doc).OfClass(DB.FloorType):
        floor_types[u(name(t))] = {'layers': layers(doc, t), 'structural': pval(t, B('FLOOR_ATTR_DEFAULT_IS_STRUCTURAL'))}
    ids = [r['id'] for r in walls if concrete(r)] + [r['id'] for r in floors + found + framing + columns]
    levels = [{'id': eid(l), 'name': u(name(l)), 'elevation_m': l.Elevation * M, 'structural': pval(l, B('LEVEL_IS_STRUCTURAL')), 'building': pval(l, B('LEVEL_IS_BUILDING_STORY'))} for l in DB.FilteredElementCollector(doc).OfClass(DB.Level)]
    grids = [u(name(g)) for g in DB.FilteredElementCollector(doc).OfClass(DB.Grid)]
    data = {'readAt': datetime.datetime.utcnow().isoformat() + 'Z', 'levels': levels, 'grids': grids,
            'walls': walls, 'floors': floors, 'foundations': found, 'framing': framing, 'structuralColumns': columns,
            'architecturalColumns': archcols, 'roofs': roofs, 'stairs': stairs, 'rebarCount': rebar,
            'wallTypes': wall_types, 'floorTypes': floor_types,
            'summary': {'concreteWallsByLevel': summarize([r for r in walls if concrete(r)], lambda r: r['level']),
                        'concreteWallsByType': summarize([r for r in walls if concrete(r)], lambda r: r['type']),
                        'floorsByLevelType': summarize(floors, lambda r: r['level'] + u' | ' + r['type']),
                        'foundationsByType': summarize(found, lambda r: r['type']), 'framingByType': summarize(framing, lambda r: r['type']),
                        'columnsByType': summarize(columns + archcols, lambda r: r['family'] + u' | ' + r['type'])},
            'warnings': warnings_for(doc, ids)}
    R1.write(os.path.join(OUT, 'inventory-structure.json'), data)
    return {'walls': len(walls), 'concreteWalls': len([r for r in walls if concrete(r)]), 'floors': len(floors), 'foundations': len(found),
            'framing': len(framing), 'columns': len(columns), 'archColumns': len(archcols), 'rebar': rebar, 'warnings': len(data['warnings'])}

def hvac(doc):
    cats = [('pipes', DB.BuiltInCategory.OST_PipeCurves), ('flexPipes', DB.BuiltInCategory.OST_FlexPipeCurves), ('pipeFittings', DB.BuiltInCategory.OST_PipeFitting),
            ('pipeAccessories', DB.BuiltInCategory.OST_PipeAccessory), ('mechanicalEquipment', DB.BuiltInCategory.OST_MechanicalEquipment),
            ('ducts', DB.BuiltInCategory.OST_DuctCurves), ('airTerminals', DB.BuiltInCategory.OST_DuctTerminal), ('plumbingFixtures', DB.BuiltInCategory.OST_PlumbingFixtures),
            ('spaces', DB.BuiltInCategory.OST_MEPSpaces), ('hvacZones', DB.BuiltInCategory.OST_HVAC_Zones), ('genericModels', DB.BuiltInCategory.OST_GenericModel),
            ('specialtyEquipment', DB.BuiltInCategory.OST_SpecialityEquipment), ('electricalEquipment', DB.BuiltInCategory.OST_ElectricalEquipment)]
    data = {'readAt': datetime.datetime.utcnow().isoformat() + 'Z', 'categories': {}}
    for key, bic in cats:
        rows = []
        for e in collect(doc, bic):
            t = doc.GetElement(e.GetTypeId())
            r = {'id': eid(e), 'type': u(name(t)) if t else u(name(e)), 'family': u(getattr(t, 'FamilyName', u'')) if t else u'', 'level': base_level(doc, e)}
            if key in ('pipes', 'flexPipes'):
                r['system'] = pval(e, B('RBS_PIPING_SYSTEM_TYPE_PARAM')); r['systemName'] = pval(e, B('RBS_SYSTEM_NAME_PARAM'))
                r['length_m'] = pval(e, B('CURVE_ELEM_LENGTH'), M); r['diameter_mm'] = pval(e, B('RBS_PIPE_DIAMETER_PARAM'), 304.8)
                r['classification'] = pval(e, B('RBS_SYSTEM_CLASSIFICATION_PARAM'))
            r['match'] = bool(KEYS.search(r['type'] + u' ' + r['family'] + u' ' + (r.get('system') or u'')))
            rows.append(r)
        data['categories'][key] = {'count': len(rows), 'matches': [r for r in rows if r['match']],
                                   'byType': summarize(rows, lambda r: r['family'] + u' | ' + r['type'] + (u' | ' + (r.get('system') or u'') if key == 'pipes' else u'')),
                                   'sample': rows[:12]}
    data['pipingSystemTypes'] = [{'name': u(name(t)), 'classification': str(t.SystemClassification)} for t in DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.PipingSystemType)]
    data['pipeTypes'] = [u(name(t)) for t in DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.PipeType)]
    data['materialsMatching'] = sorted(set(u(name(m)) for m in DB.FilteredElementCollector(doc).OfClass(DB.Material) if KEYS.search(u(name(m)))))
    data['familiesMatching'] = sorted(set(u(f.Name) + u' [' + u(f.FamilyCategory.Name if f.FamilyCategory else '') + u']' for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if KEYS.search(u(f.Name))))
    data['floorTypesMatching'] = []
    for t in DB.FilteredElementCollector(doc).OfClass(DB.FloorType):
        ls = layers(doc, t); text = u(name(t)) + u' ' + u' '.join(l['material'] for l in ls)
        data['floorTypesMatching'].append({'name': u(name(t)), 'layers': ls, 'match': bool(KEYS.search(text))})
    used = {}
    for e in collect(doc, DB.BuiltInCategory.OST_Floors):
        t = doc.GetElement(e.GetTypeId()); k = u(name(t)) + u' | ' + base_level(doc, e)
        s = used.setdefault(k, {'count': 0, 'area_m2': 0.}); s['count'] += 1; s['area_m2'] += pval(e, B('HOST_AREA_COMPUTED'), M2) or 0
    data['floorsUsed'] = [dict(key=k, **v) for k, v in sorted(used.items())]
    rooms = []
    for r in collect(doc, DB.BuiltInCategory.OST_Rooms):
        rooms.append({'id': eid(r), 'name': u(pval(r, B('ROOM_NAME'))), 'number': u(r.Number), 'level': lname(doc, r.LevelId),
                      'area_m2': r.Area * M2, 'perimeter_m': r.Perimeter * M, 'finishFloor': pval(r, B('ROOM_FINISH_FLOOR')),
                      'height_m': pval(r, B('ROOM_HEIGHT'), M)})
    data['rooms'] = rooms
    data['viewsMatching'] = sorted(set(u(name(v)) for v in DB.FilteredElementCollector(doc).OfClass(DB.View) if KEYS.search(u(name(v)))))
    data['schedulesAll'] = sorted(set(u(name(v)) for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule)))
    R1.write(os.path.join(OUT, 'inventory-hvac.json'), data)
    return dict((k, v['count']) for k, v in data['categories'].items())

def run(doc, uidoc, job):
    assert os.path.basename(doc.PathName).lower() == 'casa-angel-piloto-documentacion.rvt'
    return {'status': 'success', 'structure': structure(doc), 'hvac': hvac(doc)}
