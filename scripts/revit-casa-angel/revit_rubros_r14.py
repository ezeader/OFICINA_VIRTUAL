# -*- coding: utf-8 -*-
"""R14 read-only inventory for the pending trades (rubros). No transaction is opened."""
import os, re, imp, datetime
from Autodesk.Revit import DB

ROOT = os.path.dirname(__file__)
R1 = imp.load_source('ader_rubros_r14_lib', os.path.join(ROOT, 'revit_openings_r1.py'))
clean = R1.clean; name = R1.name; eid = R1.eid
M = .3048; M2 = M * M; M3 = M2 * M
CATS = ['OST_Walls', 'OST_Floors', 'OST_Ceilings', 'OST_Roofs', 'OST_RoofSoffit', 'OST_Fascia', 'OST_Gutter', 'OST_Cornices', 'OST_StructuralFraming',
        'OST_Stairs', 'OST_StairsRailing', 'OST_Railings', 'OST_Casework', 'OST_Furniture', 'OST_FurnitureSystems', 'OST_SpecialityEquipment',
        'OST_PlumbingFixtures', 'OST_MechanicalEquipment', 'OST_ElectricalEquipment', 'OST_ElectricalFixtures', 'OST_LightingFixtures', 'OST_LightingDevices',
        'OST_Conduit', 'OST_ConduitFitting', 'OST_CableTray', 'OST_Wire', 'OST_CommunicationDevices', 'OST_DataDevices', 'OST_SecurityDevices',
        'OST_FireAlarmDevices', 'OST_TelephoneDevices', 'OST_NurseCallDevices', 'OST_PipeCurves', 'OST_PipeFitting', 'OST_PipeAccessory', 'OST_DuctCurves',
        'OST_DuctTerminal', 'OST_GenericModel', 'OST_Topography', 'OST_Toposolid', 'OST_Planting', 'OST_Site', 'OST_Hardscape', 'OST_Parking',
        'OST_Entourage', 'OST_Roads', 'OST_Mass', 'OST_Columns', 'OST_Doors', 'OST_Windows', 'OST_Rooms', 'OST_Areas', 'OST_DetailComponents']

def u(s):
    if s is None: return u''
    return s if isinstance(s, unicode) else clean(s)

def pd(e, bip, f=1.):
    try:
        p = e.get_Parameter(bip)
        return p.AsDouble() * f if p and p.HasValue and p.StorageType == DB.StorageType.Double else None
    except: return None

def sysname(e):
    for b in [DB.BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM, DB.BuiltInParameter.RBS_SYSTEM_NAME_PARAM]:
        try:
            p = e.get_Parameter(b)
            if p and p.HasValue: return u(p.AsValueString() or p.AsString())
        except: pass
    return u''

def layers(doc, t):
    try:
        cs = t.GetCompoundStructure()
        if cs is None: return []
        return [{'function': str(l.Function), 'material': u(name(doc.GetElement(l.MaterialId))) if l.MaterialId != DB.ElementId.InvalidElementId else u'', 'thickness_m': l.Width * M} for l in cs.GetLayers()]
    except: return []

def run(doc, uidoc, job):
    assert os.path.basename(doc.PathName).lower() == 'casa-angel-piloto-documentacion.rvt'
    out = {'readAt': datetime.datetime.utcnow().isoformat() + 'Z', 'categories': {}, 'types': {}, 'keywordFamilies': []}
    for cn in CATS:
        bic = getattr(DB.BuiltInCategory, cn, None)
        if bic is None: continue
        try: col = list(DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType())
        except: continue
        agg = {}
        for e in col:
            t = doc.GetElement(e.GetTypeId())
            fam = u(getattr(t, 'FamilyName', u'')) if t else u''
            tn = u(name(t)) if t else u(name(e))
            k = fam + u' | ' + tn + (u' | ' + sysname(e) if cn in ('OST_PipeCurves', 'OST_DuctCurves', 'OST_Conduit') else u'')
            a = agg.setdefault(k, {'count': 0, 'area_m2': 0., 'volume_m3': 0., 'length_m': 0., 'levels': {}, 'materials': {}})
            a['count'] += 1
            a['area_m2'] += pd(e, DB.BuiltInParameter.HOST_AREA_COMPUTED, M2) or (pd(e, DB.BuiltInParameter.ROOM_AREA, M2) if cn == 'OST_Rooms' else 0) or 0
            a['volume_m3'] += pd(e, DB.BuiltInParameter.HOST_VOLUME_COMPUTED, M3) or 0
            a['length_m'] += pd(e, DB.BuiltInParameter.CURVE_ELEM_LENGTH, M) or 0
            try:
                lv = doc.GetElement(e.LevelId); ln = u(name(lv)) if lv else u'(sin nivel)'
            except: ln = u'(sin nivel)'
            a['levels'][ln] = a['levels'].get(ln, 0) + 1
            if cn in ('OST_Walls', 'OST_Floors', 'OST_Ceilings', 'OST_Roofs'):
                try:
                    for mid in e.GetMaterialIds(False):
                        mn = u(name(doc.GetElement(mid))); mm = a['materials'].setdefault(mn, {'area_m2': 0., 'volume_m3': 0.})
                        mm['area_m2'] += e.GetMaterialArea(mid, False) * M2; mm['volume_m3'] += e.GetMaterialVolume(mid) * M3
                except: pass
            if t is not None and k not in out['types'] and cn in ('OST_Walls', 'OST_Floors', 'OST_Ceilings', 'OST_Roofs'):
                out['types'][k] = layers(doc, t)
        out['categories'][cn] = {'count': len(col), 'byType': agg}
    kw = re.compile(u'(solar|fotovolt|photovolt|\\bPV\\b|gas|caldera|termotanque|domot|knx|sensor|parrilla|pileta|piscina|pool|bomba|filtro|canaleta|gutter|zocalo|zócalo|cielorraso|ceiling|teja|aislac|membrana|revest|ceram|porcelan|tablero|toma|enchufe|luminaria|interruptor|panel|cesped|planta|arbol|tree|deck)', re.I)
    for f in DB.FilteredElementCollector(doc).OfClass(DB.Family):
        n = u(f.Name)
        if kw.search(n):
            cat = u(f.FamilyCategory.Name) if f.FamilyCategory else u''
            placed = 0
            for sid in f.GetFamilySymbolIds():
                placed += DB.FilteredElementCollector(doc).WherePasses(DB.FamilyInstanceFilter(doc, sid)).GetElementCount()
            out['keywordFamilies'].append({'family': n, 'category': cat, 'placed': placed})
    out['materials'] = sorted(set(u(name(m)) for m in DB.FilteredElementCollector(doc).OfClass(DB.Material)))
    out['views'] = sorted(set(u(name(v)) for v in DB.FilteredElementCollector(doc).OfClass(DB.View) if not v.IsTemplate and kw.search(u(name(v)))))
    out['sheets'] = sorted(set(u(s.SheetNumber) + u' ' + u(s.Name) for s in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet)))
    R1.write(os.path.join(ROOT, 'openings-r4', 'rubros-raw.json'), out)
    return {'status': 'success', 'categories': dict((k, v['count']) for k, v in out['categories'].items() if v['count']), 'keywordFamilies': len(out['keywordFamilies'])}
