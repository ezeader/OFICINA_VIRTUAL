# -*- coding: utf-8 -*-
"""Inspect native annotation capability for the Casa Angel kitchen pilot."""
import os, io, json, datetime, math, re
from Autodesk.Revit import DB
from System import Int64
from routes.json_safety import sanitize_for_json

ROOT = os.path.dirname(__file__)
EXPECTED = r'C:\Users\ezead\OneDrive\Escritorio\ANGEL\CASA ANGEL BRUSCA.rvt'
OUTPUT = os.path.abspath(os.path.join(ROOT,'..','..','outputs','casa-angel'))
PILOT_RVT = os.path.join(OUTPUT,'Casa-Angel-piloto-documentacion.rvt')
VIEW_IDS = [1445818, 1439889, 1489196]

def eid(v):
    return int(v.Value)

def el(doc, v):
    return doc.GetElement(DB.ElementId(Int64(v)))

def name(e):
    try: return DB.Element.Name.GetValue(e)
    except Exception: return e.Name

def xyz(p):
    return [p.X, p.Y, p.Z]

def parameters(e):
    result = []
    for p in e.Parameters:
        row = {'id': eid(p.Id), 'name': p.Definition.Name, 'storage': str(p.StorageType)}
        try:
            row['display'] = p.AsValueString()
            if p.StorageType == DB.StorageType.String: row['value'] = p.AsString()
            elif p.StorageType == DB.StorageType.Double: row['value'] = p.AsDouble()
            elif p.StorageType == DB.StorageType.Integer: row['value'] = p.AsInteger()
            elif p.StorageType == DB.StorageType.ElementId: row['value'] = eid(p.AsElementId())
        except Exception: pass
        result.append(row)
    return result

def write(action, data):
    path = os.path.join(ROOT, 'native-' + action + '.json')
    data['utc'] = datetime.datetime.utcnow().isoformat() + 'Z'
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(unicode(json.dumps(sanitize_for_json(data), ensure_ascii=True, indent=2)))
    return {'status': 'success', 'action': action, 'path': path,
            'summary': data.get('summary', {})}

def inspect(doc):
    data = {'document': doc.PathName, 'views': [], 'tag_types': [], 'sheets': []}
    cats = [DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_PipeFitting,
            DB.BuiltInCategory.OST_PipeAccessory]
    target_ids = VIEW_IDS + [eid(v.Id) for v in DB.FilteredElementCollector(doc).OfClass(DB.View)
                            if name(v).startswith('ADER SAN - PILOTO COCINA')]
    for vid in target_ids:
        v = el(doc, vid)
        if not v: continue
        row = {'id': vid, 'name': name(v), 'type': str(v.ViewType), 'scale': v.Scale,
               'right': xyz(v.RightDirection), 'up': xyz(v.UpDirection),
               'direction': xyz(v.ViewDirection), 'origin': xyz(v.Origin), 'elements': []}
        for cat in cats:
            for e in DB.FilteredElementCollector(doc, v.Id).OfCategory(cat).WhereElementIsNotElementType():
                r = {'id': eid(e.Id), 'name': name(e), 'category': str(cat),
                     'type_id': eid(e.GetTypeId()), 'parameters': parameters(e)}
                if isinstance(e, DB.Plumbing.Pipe):
                    c = e.Location.Curve
                    r.update({'p0': xyz(c.GetEndPoint(0)), 'p1': xyz(c.GetEndPoint(1)),
                              'length_ft': c.Length, 'diameter_ft': e.Diameter})
                else:
                    try: r['point'] = xyz(e.Location.Point)
                    except Exception: pass
                row['elements'].append(r)
        data['views'].append(row)
    for t in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_PipeTags).WhereElementIsElementType():
        data['tag_types'].append({'id': eid(t.Id), 'name': name(t), 'family': t.FamilyName,
                                  'family_id': eid(t.Family.Id), 'parameters': parameters(t)})
    for s in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet):
        views = [eid(el(doc,eid(vp)).ViewId) for vp in s.GetAllViewports()]
        if set(views).intersection(VIEW_IDS):
            data['sheets'].append({'id': eid(s.Id), 'number': s.SheetNumber, 'name': name(s), 'views': views})
    data['summary'] = {'views': len(data['views']), 'tag_types': len(data['tag_types']), 'sheets': data['sheets']}
    return write('inspect', data)

def probe(doc):
    view = el(doc, 1445818)
    pipes = list(DB.FilteredElementCollector(doc, view.Id).OfCategory(DB.BuiltInCategory.OST_PipeCurves).WhereElementIsNotElementType())
    pipe = max(pipes, key=lambda p: p.Location.Curve.Length)
    result = {'pipe_id': eid(pipe.Id), 'pipe_length_ft': pipe.Location.Curve.Length,
              'pipe_diameter_ft': pipe.Diameter, 'types': [], 'rolled_back': False}
    tx = DB.Transaction(doc, 'ADER: rollback-only native pipe tag probe')
    tx.Start()
    try:
        types = list(DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_PipeTags).WhereElementIsElementType())
        for symbol in types:
            row = {'id': eid(symbol.Id), 'family': symbol.FamilyName}
            sub = DB.SubTransaction(doc); sub.Start()
            try:
                tag = DB.IndependentTag.Create(doc, symbol.Id, view.Id, DB.Reference(pipe), False,
                                              DB.TagOrientation.Horizontal, pipe.Location.Curve.Evaluate(.5, True))
                doc.Regenerate()
                row['text'] = tag.TagText
                row['rotation_supported'] = hasattr(tag, 'RotationAngle')
            except Exception as ex: row['error'] = unicode(ex)
            finally: sub.RollBack()
            result['types'].append(row)
    finally:
        tx.RollBack(); result['rolled_back'] = True
    family_doc=doc.EditFamily(el(doc,1358743).Family)
    try:
        result['family_text_styles']=[]
        for e in DB.FilteredElementCollector(family_doc).WhereElementIsElementType():
            size=e.get_Parameter(DB.BuiltInParameter.TEXT_SIZE)
            if size:
                result['family_text_styles'].append({'id':eid(e.Id),'class':e.GetType().Name,
                                                     'name':name(e),'size_mm':size.AsDouble()*304.8})
    finally:family_doc.Close(False)
    result['summary'] = result.copy()
    return write('probe-tags', result)

GROUPS = {'AmancoWavin AF': ('AF', (25,75,210)),
          'AmancoWavin AC': ('AC', (210,35,35)),
          'AmancoWavin CL - Primario': ('CP', (122,25,56)),
          'AmancoWavin CL - Secundario': ('CS', (170,130,0))}

def view_box(e, view):
    bb = e.get_BoundingBox(view)
    if bb is None: return None
    pts = [bb.Transform.OfPoint(DB.XYZ(x,y,z)) for x in (bb.Min.X,bb.Max.X)
           for y in (bb.Min.Y,bb.Max.Y) for z in (bb.Min.Z,bb.Max.Z)]
    xx = [p.DotProduct(view.RightDirection) for p in pts]
    yy = [p.DotProduct(view.UpDirection) for p in pts]
    return [min(xx),min(yy),max(xx),max(yy)]

def overlap(a,b,pad):
    return (a[0] < b[2]+pad and a[2]+pad > b[0]
            and a[1] < b[3]+pad and a[3]+pad > b[1])

def build(doc, uidoc):
    manifest_path = os.path.join(ROOT,'native-build-pilot.json')
    if os.path.exists(manifest_path):
        with io.open(manifest_path,'r',encoding='utf-8') as f: old=json.load(f)
        if any(el(doc,r['tag_id']) is not None for r in old.get('tags',[])):
            return horizontal_revision(doc,uidoc,old)
    source_views = [el(doc,v) for v in VIEW_IDS]
    scope = [p for p in DB.FilteredElementCollector(doc,source_views[0].Id)
             .OfCategory(DB.BuiltInCategory.OST_PipeCurves).WhereElementIsNotElementType()
             if name(p) in GROUPS]
    visible = {eid(v.Id): set(eid(p.Id) for p in DB.FilteredElementCollector(doc,v.Id)
               .OfCategory(DB.BuiltInCategory.OST_PipeCurves).WhereElementIsNotElementType()) for v in source_views}
    data = {'document':doc.PathName,'views':[],'tags':[],'pending':[],
            'scope_pipe_ids':[eid(p.Id) for p in scope], 'saved_to_rvt':False}
    tx=DB.Transaction(doc,'ADER - native sanitary annotation pilot');tx.Start()
    try:
        views=[]
        suffixes=['PLANTA','CORTE AA','CORTE BB']
        for source,suffix in zip(source_views,suffixes):
            target_name='ADER SAN - PILOTO COCINA - '+suffix
            existing=[v for v in DB.FilteredElementCollector(doc).OfClass(DB.View) if name(v)==target_name]
            v=existing[0] if existing else el(doc,eid(source.Duplicate(DB.ViewDuplicateOption.WithDetailing)))
            v.Name=target_name;v.ViewTemplateId=DB.ElementId.InvalidElementId;v.Scale=10
            # Keep architectural context, hide heating pipes/fittings only in pilot.
            from System.Collections.Generic import List
            heating=List[DB.ElementId]()
            for e in DB.FilteredElementCollector(doc,v.Id).WhereElementIsNotElementType():
                try:
                    if name(e).startswith('CAL -') and e.CanBeHidden(v): heating.Add(e.Id)
                except Exception:pass
            if heating.Count:v.HideElements(heating)
            views.append(v)
            data['views'].append({'id':eid(v.Id),'source_id':eid(source.Id),'name':name(v),'scale':v.Scale})
        doc.Regenerate()
        boxes={eid(v.Id):[] for v in views}
        assignments=[]
        for p in scope:
            c=p.Location.Curve; d=c.GetEndPoint(1)-c.GetEndPoint(0)
            vertical=abs(d.Z)>.9*c.Length
            options=[(v,s) for v,s in zip(views,source_views)
                     if eid(p.Id) in visible[eid(s.Id)] and (s.ViewType==DB.ViewType.Section if vertical else s.ViewType==DB.ViewType.FloorPlan)]
            if not options:
                data['pending'].append({'pipe_id':eid(p.Id),'reason':'No appropriate quantity view'});continue
            # Prefer section AA when both show the vertical; BB covers remaining risers.
            v=options[0][0]
            assignments.append((v,p,vertical))
        # Long runs first; small pieces get leaders and available white space.
        assignments.sort(key=lambda x:-x[1].Location.Curve.Length)
        for view,p,vertical in assignments:
            c=p.Location.Curve;delta=c.GetEndPoint(1)-c.GetEndPoint(0)
            dx=delta.DotProduct(view.RightDirection);dy=delta.DotProduct(view.UpDirection)
            if math.hypot(dx,dy)<1e-5:
                data['pending'].append({'pipe_id':eid(p.Id),'reason':'Projected segment too short'});continue
            angle=math.atan2(dy,dx)
            while angle>math.pi/2:angle-=math.pi
            while angle<-math.pi/2:angle+=math.pi
            normal=view.RightDirection.Multiply(-math.sin(angle))+view.UpDirection.Multiply(math.cos(angle))
            mid=c.Evaluate(.5,True)
            tag=DB.IndependentTag.Create(doc,el(doc,1358743).Id,view.Id,DB.Reference(p),False,
                                         DB.TagOrientation.AnyModelDirection,mid)
            tag.RotationAngle=angle
            doc.Regenerate()
            # Revit's bounding box can retain the invisible leader anchor when
            # the head moves. Measure at the host midpoint, then translate only
            # that text footprint when evaluating candidate placements.
            base_bb=view_box(tag,view)
            if not base_bb:raise Exception('Tag has no visible bounds')
            chosen=None;leader=False
            offsets=[3,5.5,8,11,15,20,26,33,42,52,65,80]
            for offset in offsets:
                for sign in (1,-1):
                    pos=mid+normal.Multiply(offset/304.8*view.Scale*sign)
                    shift=pos-mid
                    sx=shift.DotProduct(view.RightDirection);sy=shift.DotProduct(view.UpDirection)
                    bb=[base_bb[0]+sx,base_bb[1]+sy,base_bb[2]+sx,base_bb[3]+sy]
                    if bb and not any(overlap(bb,b,1.0/304.8*view.Scale) for b in boxes[eid(view.Id)]):
                        chosen=(pos,bb,offset);break
                if chosen:break
            if not chosen:
                write('placement-debug',{'pipe_id':eid(p.Id),'view':eid(view.Id),'box':bb,
                                         'existing_boxes':boxes[eid(view.Id)],'placed':data['tags'],
                                         'head':xyz(tag.TagHeadPosition),'mid':xyz(mid),'angle':angle})
                raise Exception('Could not place readable tag for pipe '+str(eid(p.Id)))
            pos,bb,offset=chosen
            tag.TagHeadPosition=pos
            if offset>5.5 or c.Length/view.Scale*304.8<28:
                tag.HasLeader=True
                tag.LeaderEndCondition=DB.LeaderEndCondition.Free
                tag.SetLeaderEnd(DB.Reference(p),mid)
                tag.TagHeadPosition=pos
                leader=True
            group,color=GROUPS[name(p)]
            settings=DB.OverrideGraphicSettings();settings.SetProjectionLineColor(DB.Color(*color))
            view.SetElementOverrides(tag.Id,settings)
            boxes[eid(view.Id)].append(bb)
            data['tags'].append({'tag_id':eid(tag.Id),'pipe_id':eid(p.Id),'view_id':eid(view.Id),
                                 'group':group,'type':name(p),'text':tag.TagText,'vertical':vertical,
                                 'length_m':c.Length*.3048,'diameter_mm':p.Diameter*304.8,
                                 'angle':angle,'leader':leader,'offset_mm_paper':offset,'text_box':bb})
        doc.Regenerate()
        if tx.Commit()!=DB.TransactionStatus.Committed:raise Exception('Pilot transaction did not commit')
    except Exception:
        if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
        raise
    uidoc.ActiveView=views[0]
    data['summary']={'tag_count':len(data['tags']),'pending':len(data['pending']),
                     'views':data['views'],'native_parameter_tags':True,'saved_to_rvt':False}
    return write('build-pilot',data)

def verify(doc):
    with io.open(os.path.join(ROOT,'native-build-pilot.json'),'r',encoding='utf-8') as f:data=json.load(f)
    checks=[]
    for row in data['tags']:
        tag=el(doc,row['tag_id']);pipe=el(doc,row['pipe_id'])
        hosts=[eid(i) for i in tag.GetTaggedLocalElementIds()]
        text=tag.TagText
        lengths=re.findall(r'([0-9]+[.,][0-9]+)\s*m\b',text)
        length=float(lengths[-1].replace(',','.')) if lengths else None
        checks.append({'pipe_id':row['pipe_id'],'tag_id':row['tag_id'],'host_ok':hosts==[row['pipe_id']],
                       'orientation':str(tag.TagOrientation),
                       'orientation_ok':row['pipe_id'] in (1437779,1438638) or tag.TagOrientation==DB.TagOrientation.Horizontal,
                       'native_length_m':pipe.Location.Curve.Length*.3048,'label_length_m':length,
                       'length_ok':length is not None and abs(length-pipe.Location.Curve.Length*.3048)<=.000051})
    data={'checks':checks,'summary':{'checked':len(checks),'host_errors':sum(not r['host_ok'] for r in checks),
                                   'length_errors':sum(not r['length_ok'] for r in checks),
                                   'orientation_errors':sum(not r['orientation_ok'] for r in checks),
                                   'unique_hosts':len(set(r['pipe_id'] for r in checks))}}
    return write('verify',data)

def refine(doc,uidoc,data):
    if data.get('font_upgraded'):return {'status':'success','message':'Pilot already refined; no changes.'}
    # A separate family protects every existing project tag and its formatting.
    existing=[f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if name(f)=='ADER_Sanitaria_Tipo_Diametro_Longitud']
    if existing:family=existing[0]
    else:
        family_doc=doc.EditFamily(el(doc,1358743).Family)
        try:
            family_tx=DB.Transaction(family_doc,'ADER - readable 3mm pipe label');family_tx.Start()
            family_doc.OwnerFamily.Name='ADER_Sanitaria_Tipo_Diametro_Longitud'
            for style in DB.FilteredElementCollector(family_doc).WhereElementIsElementType():
                if style.GetType().Name in ('TextElementType','TextNoteType'):
                    size=style.get_Parameter(DB.BuiltInParameter.TEXT_SIZE)
                    if size and not size.IsReadOnly:size.Set(3.0/304.8)
            family_tx.Commit()
            family_path=os.path.join(ROOT,'ADER_Sanitaria_Tipo_Diametro_Longitud.rfa')
            save_options=DB.SaveAsOptions();save_options.OverwriteExistingFile=True
            family_doc.SaveAs(family_path,save_options)
            family=family_doc.LoadFamily(doc)
        finally:family_doc.Close(False)
    new_types=[el(doc,eid(i)) for i in family.GetFamilySymbolIds()]
    new_symbol=next(t for t in new_types if t.LookupParameter('T+D+L') and t.LookupParameter('T+D+L').AsInteger()==1)
    tx=DB.Transaction(doc,'ADER - improve native annotation legibility');tx.Start()
    try:
        for vr in data['views']:
            v=el(doc,vr['id']);v.AreAnnotationCategoriesHidden=False
            v.SetCategoryHidden(DB.ElementId(DB.BuiltInCategory.OST_PipeTags),False)
            ap=v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
            if ap and not ap.IsReadOnly:ap.Set(0)
            rows=[r for r in data['tags'] if r['view_id']==vr['id']]
            boxes=[]
            for r in rows:
                tag=el(doc,r['tag_id']);p=el(doc,r['pipe_id']);c=p.Location.Curve
                tag.ChangeTypeId(new_symbol.Id)
                mid=c.Evaluate(.5,True)
                plane_mid=mid-v.ViewDirection.Multiply((mid-v.Origin).DotProduct(v.ViewDirection))
                tag.HasLeader=False;tag.TagHeadPosition=plane_mid;doc.Regenerate()
                bb=view_box(tag,v)
                center=DB.XYZ((bb[0]+bb[2])/2,(bb[1]+bb[3])/2,0)
                center_shift=v.RightDirection.Multiply(center.X-plane_mid.DotProduct(v.RightDirection))+v.UpDirection.Multiply(center.Y-plane_mid.DotProduct(v.UpDirection))
                angle=r['angle'];normal=v.RightDirection.Multiply(-math.sin(angle))+v.UpDirection.Multiply(math.cos(angle))
                short=c.Length/v.Scale*304.8<35
                start=12 if short else 6
                choice=None
                for off in [start,start+3,start+6,start+10,start+15,start+22,start+30,start+40,start+55,start+75,start+100,start+130]:
                    for sign in (1,-1):
                        head=plane_mid+normal.Multiply(sign*off*v.Scale/304.8)-center_shift
                        shift=head-plane_mid;sx=shift.DotProduct(v.RightDirection);sy=shift.DotProduct(v.UpDirection)
                        candidate=[bb[0]+sx,bb[1]+sy,bb[2]+sx,bb[3]+sy]
                        if not any(overlap(candidate,b,1.5*v.Scale/304.8) for b in boxes):
                            choice=(head,candidate,off);break
                    if choice:break
                if not choice:raise Exception('No readable refined location for '+str(r['pipe_id']))
                head,bb,off=choice;tag.TagHeadPosition=head
                if short or off>9:
                    tag.HasLeader=True;tag.LeaderEndCondition=DB.LeaderEndCondition.Free
                    tag.SetLeaderEnd(DB.Reference(p),mid);tag.TagHeadPosition=head
                boxes.append(bb)
                r.update({'text_box':bb,'offset_mm_paper':off,'leader':bool(tag.HasLeader)})
        doc.Regenerate()
        if tx.Commit()!=DB.TransactionStatus.Committed:raise Exception('Refinement did not commit')
    except Exception:
        if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
        raise
    data['refined']=True
    data['font_upgraded']=True
    data['native_tag_family']=name(family)
    uidoc.ActiveView=el(doc,data['views'][0]['id'])
    return write('build-pilot',data)

def horizontal_revision(doc,uidoc,data):
    if os.path.normcase(doc.PathName)!=os.path.normcase(PILOT_RVT):
        raise Exception('This revision requires the saved pilot copy.')
    if data.get('horizontal_revision')==3:return {'status':'success','message':'Horizontal revision already applied.'}
    if data.get('horizontal_revision')==2:
        tx=DB.Transaction(doc,'ADER - clear architectural context');tx.Start()
        try:
            for r in data['tags']:
                dx=-4.7 if r['pipe_id'] in (1455360,2014045) else (3.0 if r['pipe_id'] in (1454292,1455065) else 0)
                if not dx:continue
                v=el(doc,r['view_id']);tag=el(doc,r['tag_id']);ref=DB.Reference(el(doc,r['pipe_id']))
                shift=v.RightDirection.Multiply(dx)
                elbow=tag.GetLeaderElbow(ref)+shift
                tag.TagHeadPosition=tag.TagHeadPosition+shift;tag.SetLeaderElbow(ref,elbow)
            tx.Commit()
        except Exception:
            if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
            raise
        data['horizontal_revision']=3
        return write('build-pilot',data)
    with io.open(os.path.join(ROOT,'native-printed-lengths.json'),'r',encoding='utf-8') as f:printed=json.load(f)
    tx=DB.Transaction(doc,'ADER - horizontal callouts and traceable quantities');tx.Start()
    try:
        for key in ('siphon_note_id','quantity_view_id'):
            if data.get(key) and el(doc,data[key]):doc.Delete(el(doc,data[key]).Id)
        def point(v,x,y):
            return v.Origin+v.RightDirection.Multiply(x-v.Origin.DotProduct(v.RightDirection))+v.UpDirection.Multiply(y-v.Origin.DotProduct(v.UpDirection))
        def place(r,x,y,side):
            v=el(doc,r['view_id']);p=el(doc,r['pipe_id']);tag=el(doc,r['tag_id'])
            mid=p.Location.Curve.Evaluate(.5,True)
            tag.HasLeader=False;tag.TagOrientation=DB.TagOrientation.Horizontal
            base=point(v,x,y);tag.TagHeadPosition=base;doc.Regenerate()
            head=base
            tag.HasLeader=True;tag.LeaderEndCondition=DB.LeaderEndCondition.Free
            ref=DB.Reference(p);tag.SetLeaderEnd(ref,mid);tag.TagHeadPosition=head
            # Short horizontal landing at the edge of each aligned text column.
            edge=x+side*1.25
            tag.SetLeaderElbow(ref,point(v,edge,y))
            r.update({'angle':0,'leader':True,'head':xyz(head),'orientation':'Horizontal'})
        # Keep the two long ceiling-run labels aligned with the plan as requested.
        plan=[r for r in data['tags'] if r['view_id']==data['views'][0]['id']]
        right=[r for r in plan if el(doc,r['pipe_id']).Location.Curve.Evaluate(.5,True).X>12]
        right.sort(key=lambda r:-el(doc,r['pipe_id']).Location.Curve.Evaluate(.5,True).Y)
        for i,r in enumerate(right):place(r,19.2,22.3-i*.47,-1)
        bottom=[r for r in plan if r not in right and r['pipe_id'] not in (1437779,1438638)]
        bottom.sort(key=lambda r:el(doc,r['pipe_id']).Location.Curve.Evaluate(.5,True).X)
        positions={1455054:(6.86,14.45),1457173:(6.38,14.05),1454758:(2.35,16.8),1454025:(2.0,15.45),
                   1454828:(4.8,17.5),2321588:(4.8,17.0),1456739:(9.5,16.0),1457151:(9.5,16.5)}
        for r in bottom:
            x,y=positions[r['pipe_id']];place(r,x,y,-1)
        for vr in data['views'][1:]:
            v=el(doc,vr['id']);rows=[r for r in data['tags'] if r['view_id']==vr['id']]
            if vr['source_id']==1439889:
                # Split around the sink so leaders do not all cross one another.
                left=[r for r in rows if el(doc,r['pipe_id']).Location.Curve.Evaluate(.5,True).DotProduct(v.RightDirection)<-19.1]
                right=[r for r in rows if r not in left]
                for bank,x,side in ((left,-24.8,1),(right,-11.0,-1)):
                    bank.sort(key=lambda r:-el(doc,r['pipe_id']).Location.Curve.Evaluate(.5,True).Z)
                    for i,r in enumerate(bank):place(r,x,13.2-i*.52,side)
            else:
                high=[r for r in rows if el(doc,r['pipe_id']).Location.Curve.Evaluate(.5,True).Z>14]
                low=[r for r in rows if r not in high]
                for i,r in enumerate(sorted(high,key=lambda r:-el(doc,r['pipe_id']).Location.Curve.Evaluate(.5,True).Z)):
                    place(r,1.4,16.5-i*.65,-1)
                for i,r in enumerate(sorted(low,key=lambda r:-el(doc,r['pipe_id']).Location.Curve.Evaluate(.5,True).Z)):
                    place(r,-7.0,8.4-i*.55,-1)
        note_type=next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType) if name(t)=='ADER SAN - revision 3mm')
        # The actual model contains an assembly, not an independently named siphon.
        bbview=el(doc,data['views'][2]['id'])
        note=DB.TextNote.Create(doc,bbview.Id,point(bbview,-22,11.8),
            'DESCARGA DE PILETA / SIFON A VERIFICAR\nConjunto modelado con canos, codos y reducciones.\nConfirmar cierre hidraulico y acceso de limpieza\nantes de cerrar el computo de accesorios.',note_type.Id)
        leader=note.AddLeader(DB.TextNoteLeaderTypes.TNLT_STRAIGHT_R)
        anchor=el(doc,2016492).Location.Point
        leader.End=point(bbview,anchor.DotProduct(bbview.RightDirection),anchor.DotProduct(bbview.UpDirection))
        leader.Elbow=point(bbview,-17.4,11.5)
        data['siphon_note_id']=eid(note.Id)
        # Exact lengths, each native element ID counted once; no fitting allowance.
        groups={};details=[]
        for pid in sorted(set(data['scope_pipe_ids'])):
            p=el(doc,pid);g=GROUPS[name(p)][0];dn=round(p.Diameter*304.8,3);length=p.Location.Curve.Length*.3048
            key=(g,dn);groups.setdefault(key,[]).append(length)
            details.append({'pipe_id':pid,'system':g,'diameter_mm':dn,'length_m':length,
                            'printed_m':printed[str(pid)],'view_id':next(r['view_id'] for r in data['tags'] if r['pipe_id']==pid)})
        vft=next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if t.ViewFamily==DB.ViewFamily.Drafting)
        qv=DB.ViewDrafting.Create(doc,vft.Id);qv.Name='ADER SAN - PILOTO COCINA - RESUMEN';qv.Scale=1
        def qtext(x,y,text):return DB.TextNote.Create(doc,qv.Id,DB.XYZ(x,y,0),text,note_type.Id)
        qtext(0,0,'CASA ANGEL | COCINA | RESUMEN DEL PILOTO\n36 tramos unicos identificados en planta y cortes. Longitudes de eje del modelo.')
        qtext(0,-.12,'SISTEMA / DIAMETRO');qtext(.85,-.12,'TRAMOS');qtext(1.15,-.12,'MODELO [m]');qtext(1.6,-.12,'SUMA ROTULOS [m]')
        totals={};y=-.19;out=[]
        labels={'AF':'Agua fria','AC':'Agua caliente','CP':'Cloacal primario','CS':'Cloacal secundario'}
        for g in ('AF','AC','CP','CS'):
            all_lengths=[]
            for key in sorted(k for k in groups if k[0]==g):
                values=groups[key];all_lengths+=values
                qtext(0,y,'%s / DN %g mm'%(g,key[1]));qtext(.85,y,str(len(values)))
                shown=sum(r['printed_m'] for r in details if r['system']==g and r['diameter_mm']==key[1])
                qtext(1.15,y,'%.3f'%sum(values));qtext(1.6,y,'%.2f'%shown)
                out.append({'system':g,'diameter_mm':key[1],'count':len(values),'length_m':sum(values),'printed_sum_m':shown})
                y-=.055
            totals[g]=sum(all_lengths)
            qtext(0,y,'TOTAL '+labels[g]);qtext(.85,y,str(len(all_lengths)));qtext(1.15,y,'%.3f'%totals[g]);qtext(1.6,y,'%.2f'%sum(r['printed_m'] for r in details if r['system']==g));y-=.085
        qtext(0,y,'TOTAL GENERAL');qtext(.85,y,str(len(details)));qtext(1.15,y,'%.3f'%sum(totals.values()));qtext(1.6,y,'%.2f'%sum(r['printed_m'] for r in details));y-=.12
        qtext(0,y,'ALCANCE Y LECTURA\nModelo: sumatoria sin redondeos intermedios, presentada a 0.001 m.\nRotulos: suma de las etiquetas impresas a 0.01 m; puede diferir por redondeo.\nIncluye solo los 36 tramos del piloto de cocina, no toda la instalacion del proyecto.\nNo incluye largos internos de accesorios, desperdicio, cantidades de compra ni presupuesto.\nAccesorios: falta validar piezas reales y excluir subcomponentes auxiliares de las familias.\nSifon de cocina: conjunto senalado en corte BB; solucion y accesorios pendientes de validacion.\nResumen generado desde Revit en esta revision; regenerar si cambia la geometria.')
        data['quantity_view_id']=eid(qv.Id)
        data['quantity_summary']={'by_diameter':out,'totals_m':totals,'grand_total_m':sum(totals.values()),'items':details}
        for vr in data['views']:
            v=el(doc,vr['id'])
            for n in DB.FilteredElementCollector(doc,v.Id).OfClass(DB.TextNote):
                if n.Text.startswith('ADER SAN - PILOTO COCINA'):
                    n.Text=n.Text.replace('Accesorios y revision grafica final pendientes.','Ver resumen final. Accesorios pendientes de validacion.')
        doc.Regenerate()
        if tx.Commit()!=DB.TransactionStatus.Committed:raise Exception('Horizontal revision did not commit')
    except Exception:
        if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
        raise
    data['horizontal_revision']=2
    data['summary']={'horizontal_tags':34,'preserved_vertical_plan_tags':2,'quantity_summary':data['quantity_summary']['totals_m']}
    return write('build-pilot',data)

def run(doc, uidoc, action):
    isdoc = os.path.normcase(os.path.dirname(doc.PathName)) == os.path.normcase(os.path.join(OUTPUT,'documentacion')) and os.path.basename(doc.PathName).startswith('Casa-Angel-DOC-')
    if not isdoc and os.path.normcase(doc.PathName) not in (os.path.normcase(EXPECTED),os.path.normcase(PILOT_RVT)):
        raise Exception('Wrong active document. Expected Casa Angel.')
    if doc.IsReadOnly or doc.IsModifiable:
        raise Exception('Document is not in an editable idle state.')
    if action == 'interactive_geometry':
        import imp
        mod=imp.load_source('ader_interactive_geometry',os.path.join(ROOT,'revit_interactive_geometry.py'))
        return mod.run(doc,uidoc)
    if action == 'inspect':
        if os.path.exists(os.path.join(ROOT,'openings-r1.flag')):
            import imp
            return imp.load_source('ader_openings_r1',os.path.join(ROOT,'revit_openings_r1.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'review-r13.flag')):
            import imp
            return imp.load_source('ader_review_r13',os.path.join(ROOT,'revit_review_r13.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'details-r12.flag')):
            import imp
            return imp.load_source('ader_details_r12',os.path.join(ROOT,'revit_details_r12.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'review-r12.flag')):
            import imp
            return imp.load_source('ader_review_r12',os.path.join(ROOT,'revit_review_r12.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'project-r11.flag')):
            import imp
            return imp.load_source('ader_project_r11',os.path.join(ROOT,'revit_project_r11.py')).run(doc,uidoc)
        import imp
        if os.path.exists(os.path.join(ROOT,'summary-r10.flag')):
            return imp.load_source('ader_summary_r10',os.path.join(ROOT,'revit_summary_r10.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'export-r10.flag')):
            a=imp.load_source('ader_summary_r10',os.path.join(ROOT,'revit_summary_r10.py')).run(doc,uidoc)
            b=imp.load_source('ader_axon_r10',os.path.join(ROOT,'revit_axon_r10.py')).run(doc,uidoc)
            return {'pdf':a,'axon':b}
        if os.path.exists(os.path.join(ROOT,'inventory-r10.flag')):
            return imp.load_source('ader_inventory_r10',os.path.join(ROOT,'revit_inventory_r10.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'valve-r10.flag')):
            return imp.load_source('ader_valve_r10',os.path.join(ROOT,'revit_insert_valve_r10.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'connections-r10.flag')):
            return imp.load_source('ader_connections_r10',os.path.join(ROOT,'revit_connections_r10.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'elbow-r9.flag')):
            return imp.load_source('ader_elbow_r9',os.path.join(ROOT,'revit_elbow_r9.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'layout-r9.flag')):
            return imp.load_source('ader_layout_r9',os.path.join(ROOT,'revit_layout_r9.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'export-r9.flag')):
            a=imp.load_source('ader_summary_r9',os.path.join(ROOT,'revit_summary_r9.py')).run(doc,uidoc)
            b=imp.load_source('ader_axon_r9',os.path.join(ROOT,'revit_axon_r9.py')).run(doc,uidoc)
            return {'pdf':a,'axon':b}
        if os.path.exists(os.path.join(ROOT,'inventory-r9.flag')):
            return imp.load_source('ader_inventory_r9',os.path.join(ROOT,'revit_inventory_r9.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'valve-r9.flag')):
            return imp.load_source('ader_valve_r9',os.path.join(ROOT,'revit_insert_valve_r9.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'connections-r9.flag')):
            return imp.load_source('ader_connections_r9',os.path.join(ROOT,'revit_connections_r9.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'summary-r8.flag')):
            return imp.load_source('ader_summary_r8',os.path.join(ROOT,'revit_summary_r8.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'correct-r8.flag')):
            return imp.load_source('ader_correct_r8',os.path.join(ROOT,'revit_correct_r8.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'review-r8.flag')):
            return imp.load_source('ader_review_r8',os.path.join(ROOT,'revit_review_r8.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'axon-r7.flag')):
            return imp.load_source('ader_axon_r7',os.path.join(ROOT,'revit_axon_r7.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'visible-r7.flag')):
            return imp.load_source('ader_visible_r7',os.path.join(ROOT,'revit_visible_r7.py')).run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'annotation-r6.flag')):
            return imp.load_source('ader_r6',os.path.join(ROOT,'revit_annotation_r6.py')).run(doc)
        if os.path.exists(os.path.join(ROOT,'request-source-reference.flag')):
            mod=imp.load_source('ader_source_reference',os.path.join(ROOT,'revit_source_reference.py'))
            return mod.run(doc,uidoc)
        if os.path.exists(os.path.join(ROOT,'request-interactive-geometry.flag')):
            mod=imp.load_source('ader_interactive_geometry',os.path.join(ROOT,'revit_interactive_geometry.py'))
            return mod.run(doc,uidoc)
        r4=imp.load_source('ader_r4',os.path.join(ROOT,'revit_pilot_r4.py'))
        return r4.inspect(doc,uidoc)
    if action == 'probe_tags': return probe(doc)
    if action in ('build_pilot','verify','export'):
        import imp
        r4=imp.load_source('ader_r4',os.path.join(ROOT,'revit_pilot_r4.py'))
        return {'build_pilot':r4.build,'verify':r4.verify,'export':r4.export}[action](doc,uidoc)
    raise Exception('Action not implemented until native tag inspection is verified.')

def export_pilot(doc,uidoc):
    from System.Collections.Generic import List
    with io.open(os.path.join(ROOT,'native-build-pilot.json'),'r',encoding='utf-8') as f:data=json.load(f)
    if not data.get('review_notes'):
        tx=DB.Transaction(doc,'ADER - pilot review legends');tx.Start()
        try:
            text_type=doc.GetElement(doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType)).Duplicate('ADER SAN - revision 3mm')
            text_type.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).Set(3.0/304.8)
            for vr in data['views']:
                v=el(doc,vr['id']);bb=v.CropBox
                corners=[bb.Transform.OfPoint(DB.XYZ(x,y,z)) for x in (bb.Min.X,bb.Max.X) for y in (bb.Min.Y,bb.Max.Y) for z in (bb.Min.Z,bb.Max.Z)]
                xmin=min(p.DotProduct(v.RightDirection) for p in corners)
                ymax=max(p.DotProduct(v.UpDirection) for p in corners)
                point=v.Origin+v.RightDirection.Multiply(xmin-v.Origin.DotProduct(v.RightDirection))+v.UpDirection.Multiply(ymax-v.Origin.DotProduct(v.UpDirection)+.9)
                count=sum(r['view_id']==vr['id'] for r in data['tags'])
                text=vr['name']+' | '+str(count)+' tramos\n'
                text+='PILOTO DE REVISION | Tipo + diametro + longitud del modelo\n'
                text+='AF azul / AC rojo / CP bordo / CS ocre. Cada tramo se etiqueta una sola vez.\n'
                text+='Familia actual: longitudes impresas a 0.01 m. Accesorios y revision grafica final pendientes.'
                DB.TextNote.Create(doc,v.Id,point,text,text_type.Id)
            tx.Commit()
        except Exception:
            if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
            raise
        data['review_notes']=True
        write('build-pilot',data)
    if not data.get('layout_reviewed'):
        tx=DB.Transaction(doc,'ADER - clear review headings and congested pipe labels');tx.Start()
        try:
            for vr in data['views']:
                v=el(doc,vr['id'])
                for note in DB.FilteredElementCollector(doc,v.Id).OfClass(DB.TextNote):
                    if note.Text.startswith('ADER SAN - PILOTO COCINA'):
                        DB.ElementTransformUtils.MoveElement(doc,note.Id,v.UpDirection.Multiply(2.0))
            adjustments={1454570:(-1.7,.55),1455271:(-1.7,-.55),2016433:(-2.9,-.15),
                         2016380:(-1.5,-.8),2016410:(-1.0,1.0),2014039:(-1.5,.9),
                         2014045:(1.5,.9),2015975:(-2.0,.4),1455360:(-1.2,.8),
                         1455332:(1.2,1.0),2017883:(1.0,0)}
            for row in data['tags']:
                if row['pipe_id'] not in adjustments:continue
                v=el(doc,row['view_id']);tag=el(doc,row['tag_id']);p=el(doc,row['pipe_id'])
                dx,dy=adjustments[row['pipe_id']]
                new_head=tag.TagHeadPosition+v.RightDirection.Multiply(dx)+v.UpDirection.Multiply(dy)
                tag.HasLeader=True;tag.LeaderEndCondition=DB.LeaderEndCondition.Free
                tag.SetLeaderEnd(DB.Reference(p),p.Location.Curve.Evaluate(.5,True));tag.TagHeadPosition=new_head
            tx.Commit()
        except Exception:
            if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
            raise
        data['layout_reviewed']=True;write('build-pilot',data)
    if not data.get('layout_final_spacing'):
        tx=DB.Transaction(doc,'ADER - separate short cold-water label');tx.Start()
        row=next(r for r in data['tags'] if r['pipe_id']==1454570)
        tag=el(doc,row['tag_id']);v=el(doc,row['view_id'])
        tag.TagHeadPosition=tag.TagHeadPosition-v.RightDirection.Multiply(1.0)
        tx.Commit()
        data['layout_final_spacing']=True;write('build-pilot',data)
    uidoc.ActiveView=el(doc,data['views'][0]['id'])
    if os.path.normcase(doc.PathName)!=os.path.normcase(PILOT_RVT):
        options=DB.SaveAsOptions();options.OverwriteExistingFile=False;options.MaximumBackups=1
        doc.SaveAs(PILOT_RVT,options)
    else:doc.Save()
    data['saved_to_rvt']=True;data['rvt_path']=PILOT_RVT
    export_ids=[el(doc,v['id']).Id for v in data['views']]
    if data.get('quantity_view_id'):export_ids.append(el(doc,data['quantity_view_id']).Id)
    ids=List[DB.ElementId](export_ids)
    options=DB.PDFExportOptions();options.Combine=True
    options.FileName='Casa-Angel-cocina-piloto-Revit'
    options.PaperFormat=DB.ExportPaperFormat.ISO_A1
    options.PaperOrientation=DB.PageOrientationType.Landscape
    options.ZoomType=DB.ZoomType.FitToPage
    options.ColorDepth=DB.ColorDepthType.Color
    options.StopOnError=True
    exported=doc.Export(OUTPUT,ids,options)
    data['pdf_exported']=bool(exported)
    data['pdf_path']=os.path.join(OUTPUT,options.FileName+'.pdf')
    data['summary']={'saved_to_rvt':True,'rvt_path':PILOT_RVT,'pdf_exported':bool(exported),
                     'pdf_path':data['pdf_path'],'tag_count':len(data['tags']),'views':data['views']}
    return write('build-pilot',data)
