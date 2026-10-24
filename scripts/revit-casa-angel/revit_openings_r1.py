# -*- coding: utf-8 -*-
"""Casa Angel openings: fixed jobs, native geometry remains unchanged."""
import os,io,json,datetime,math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List
from routes.json_safety import sanitize_for_json
ROOT=os.path.dirname(__file__)
OUT=os.path.join(ROOT,'openings-r1')
if not os.path.isdir(OUT):os.makedirs(OUT)
def read(p):
    with io.open(p,encoding='utf8') as f:return json.load(f)
def write(p,d):
    with io.open(p,'w',encoding='utf8') as f:f.write(unicode(json.dumps(sanitize_for_json(d),ensure_ascii=True,indent=2)))
def eid(e):return int(e.Id.Value)
def name(e):return DB.Element.Name.GetValue(e) if e else ''
def xyz(p):return [p.X,p.Y,p.Z]
def bbox(e):
    b=e.get_BoundingBox(None)
    return {'min':xyz(b.Min),'max':xyz(b.Max)} if b else None
def params(e):
    result=[]
    for p in e.Parameters:
        try:
            value=p.AsString() if p.StorageType==DB.StorageType.String else p.AsValueString()
            result.append({'name':p.Definition.Name,'id':int(p.Id.Value),'value':value,'storage':str(p.StorageType),'raw':p.AsDouble() if p.StorageType==DB.StorageType.Double else None})
        except:pass
    return result
def openings(doc):
    return [e for cat in [DB.BuiltInCategory.OST_Windows,DB.BuiltInCategory.OST_Doors] for e in DB.FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType()]
def physical(doc):
    return [{'id':eid(e),'uid':e.UniqueId,'type':int(e.GetTypeId().Value),'bbox':bbox(e),'transform':[xyz(e.GetTransform().Origin),xyz(e.GetTransform().BasisX),xyz(e.GetTransform().BasisY),xyz(e.GetTransform().BasisZ)],'params':params(e)} for e in openings(doc)]
def clean(s):
    import re
    if not isinstance(s,unicode):
        try:s=s.decode('utf8')
        except:s=s.decode('cp1252')
    return re.sub(r'\\x([0-9a-fA-F]{2})',lambda m:unichr(int(m.group(1),16)),s)
def schedule(doc,cat,title,material=False):
    existing=next((s for s in DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule) if name(s)==title),None)
    if existing:return existing
    s=DB.ViewSchedule.CreateMaterialTakeoff(doc,DB.ElementId(cat)) if material else DB.ViewSchedule.CreateSchedule(doc,DB.ElementId(cat))
    s.Name=title;d=s.Definition;d.IsItemized=True
    available=list(d.GetSchedulableFields())
    wanted=[('Level','Nivel'),('From Room: Number','Local origen'),('From Room: Name','Ambiente origen'),('To Room: Number','Local destino'),('To Room: Name','Ambiente destino'),('Mark','Marca'),('Family and Type','Familia y tipo'),('Width','Ancho'),('Height','Alto'),('Sill Height','Antepecho / arranque'),('Head Height','Altura superior'),('Thickness','Espesor de hoja'),('Count','Cantidad')]
    if material:wanted=[('Mark','Marca'),('Family and Type','Familia y tipo'),('Material: Name','Material modelado'),('Material: Area','Superficie de material'),('Material: Volume','Volumen de material')]
    if cat==DB.BuiltInCategory.OST_Walls:wanted=[('Family and Type','Tipo de cerramiento'),('Base Constraint','Nivel base'),('Length','Longitud del muro'),('Unconnected Height','Altura del muro'),('Width','Espesor del muro'),('Area','Superficie del muro'),('Count','Cantidad')]
    for key,label in wanted:
        candidates=[f for f in available if f.GetName(doc)==key]
        if not candidates:continue
        sf=next((f for f in candidates if f.ParameterId.Value<0),candidates[0]);f=d.AddField(sf);f.ColumnHeading=label
        f.SheetColumnWidth=.22 if key in ('Family and Type','Material: Name') else .14
        if key in ('Level','From Room: Number','Mark') and d.GetSortGroupFieldCount()<4:d.AddSortGroupField(DB.ScheduleSortGroupField(f.FieldId))
    return s
def configure_view(doc,v):
    v.ViewTemplateId=DB.ElementId.InvalidElementId
    v.DetailLevel=DB.ViewDetailLevel.Fine;v.DisplayStyle=DB.DisplayStyle.HLR
    try:v.get_Parameter(DB.BuiltInParameter.VIEW_DISCIPLINE).Set(1)
    except:pass
    # Documentation-only visibility; no model elements are moved or deleted.
    for cat in doc.Settings.Categories:
        try:
            if cat.CategoryType==DB.CategoryType.Annotation and v.CanCategoryBeHidden(cat.Id):v.SetCategoryHidden(cat.Id,True)
        except:pass
    for cat in [DB.BuiltInCategory.OST_PipeCurves,DB.BuiltInCategory.OST_PipeFitting,DB.BuiltInCategory.OST_PipeAccessory,DB.BuiltInCategory.OST_MechanicalEquipment,DB.BuiltInCategory.OST_DuctCurves,DB.BuiltInCategory.OST_Furniture]:
        try:v.SetCategoryHidden(DB.ElementId(cat),True)
        except:pass
def box_from(points,pad=.7):
    b=DB.BoundingBoxXYZ();b.Min=DB.XYZ(*[min(p[i] for p in points)-pad for i in range(3)]);b.Max=DB.XYZ(*[max(p[i] for p in points)+pad for i in range(3)]);return b
def make_room(doc,room_id):
    audit=read(os.path.join(OUT,'audit.json'));curtains=read(os.path.join(OUT,'curtain-audit.json'))
    r=next(r for r in audit['rooms'] if r['id']==room_id);room=doc.GetElement(DB.ElementId(Int64(room_id)))
    path=os.path.join(OUT,'room-'+str(room_id)+'.json')
    if os.path.exists(path):
        record=read(path)
        if doc.GetElement(DB.ElementId(Int64(record['sheet_id']))):return record
    assert r['bbox'] and r['area_m2']>0,'Room unplaced or unenclosed'
    items=[e for e in audit['items'] if room_id in [e['rooms'].get('FromRoom'),e['rooms'].get('ToRoom')]]
    cw=[w for w in curtains if room_id in w['rooms']]
    allitems=items+cw;points=[r['bbox']['min'],r['bbox']['max']]+[p for e in allitems for p in [e['bbox']['min'],e['bbox']['max']]]
    bounds=box_from(points,1.2);level=doc.GetElement(room.LevelId);bounds.Min=DB.XYZ(bounds.Min.X,bounds.Min.Y,level.Elevation-.5)
    # Avoid the room's unbounded height cutting off an opening above it.
    bounds.Max=DB.XYZ(bounds.Max.X,bounds.Max.Y,max(bounds.Max.Z,level.Elevation+9))
    label=clean(r['level_name'])+' / '+r['number']+' '+clean(r['name']);prefix='ADER ABR - '+str(room_id)
    tx=DB.Transaction(doc,'ADER openings - '+clean(r['name']));tx.Start()
    try:
        sheet=DB.ViewSheet.Create(doc,DB.ElementId(Int64(4428)));sheet.SheetNumber='ABR-'+str(room_id);sheet.Name=clean(r['name'])+' - Aberturas'
        # Existing A1 family is retained, with room name in its native sheet parameter.
        views=[]
        plan=DB.ViewPlan.Create(doc,DB.ElementId(Int64(49552)),room.LevelId);configure_view(doc,plan);plan.Name=prefix+' - PLANTA';plan.CropBox=bounds;plan.CropBoxActive=True;plan.CropBoxVisible=False
        vr=plan.GetViewRange();vr.SetLevelId(DB.PlanViewPlane.CutPlane,room.LevelId);vr.SetOffset(DB.PlanViewPlane.CutPlane,4.8);vr.SetLevelId(DB.PlanViewPlane.TopClipPlane,room.LevelId);vr.SetOffset(DB.PlanViewPlane.TopClipPlane,max(10,bounds.Max.Z-level.Elevation));plan.SetViewRange(vr)
        views.append((plan,'Planta del local'))
        ax=DB.View3D.CreateIsometric(doc,DB.ElementId(Int64(49559)));configure_view(doc,ax);ax.Name=prefix+' - AXONOMETRICA';ax.SetSectionBox(bounds);ax.IsSectionBoxActive=True
        direction=DB.XYZ(-1,-1,-.7).Normalize();right=direction.CrossProduct(DB.XYZ.BasisZ).Normalize();up=right.CrossProduct(direction).Normalize();ax.SetOrientation(DB.ViewOrientation3D(DB.XYZ(0,0,0),up,direction));views.append((ax,'Axonometrica del local'))
        for e in allitems:
            element=doc.GetElement(DB.ElementId(Int64(e['id'])))
            eb=element.get_BoundingBox(None);center=(eb.Min+eb.Max)*.5
            normal=element.FacingOrientation if isinstance(element,DB.FamilyInstance) else element.Orientation
            normal=DB.XYZ(normal.X,normal.Y,0).Normalize();x=DB.XYZ.BasisZ.CrossProduct(normal).Normalize();t=DB.Transform.Identity;t.Origin=center;t.BasisX=x;t.BasisY=DB.XYZ.BasisZ;t.BasisZ=normal
            corners=[t.Inverse.OfPoint(DB.XYZ(a,b,c)) for a in [eb.Min.X,eb.Max.X] for b in [eb.Min.Y,eb.Max.Y] for c in [eb.Min.Z,eb.Max.Z]]
            for mode in ['VISTA','DETALLE']:
                b=DB.BoundingBoxXYZ();b.Transform=t;b.Min=DB.XYZ(min(p.X for p in corners)-.6,min(p.Y for p in corners)-.5,min(p.Z for p in corners)-.7);b.Max=DB.XYZ(max(p.X for p in corners)+.6,max(p.Y for p in corners)+.5,max(p.Z for p in corners)+.7)
                if mode=='DETALLE':
                    # Perpendicular native section through the jamb/head, not an invented construction detail.
                    t2=DB.Transform.Identity;t2.Origin=center;t2.BasisX=-normal;t2.BasisY=DB.XYZ.BasisZ;t2.BasisZ=x;b.Transform=t2;b.Min=DB.XYZ(-1.5,min(p.Y for p in corners)-.4,-.4);b.Max=DB.XYZ(1.5,max(p.Y for p in corners)+.4,.4)
                v=DB.ViewSection.CreateSection(doc,DB.ElementId(Int64(49554)),b);configure_view(doc,v);v.Name=prefix+' - '+mode+' - '+str(e['id']);v.CropBoxVisible=False
                views.append((v,('Vista frontal' if mode=='VISTA' else 'Seccion de detalle modelado')+' · '+str(e.get('mark') or e['id'])))
        doc.Regenerate()
        # Flexible A1 grid; each drawing is fitted independently without cropping.
        columns=3 if len(views)>4 else 2;rowcount=int(math.ceil(float(len(views))/columns));left=.10;bottom=.30;totalw=2.20;totalh=1.50;cwgrid=totalw/columns;ch=totalh/rowcount
        typ=next((q for q in DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType) if name(q)=='ADER ABR - texto'),None)
        if not typ:
            base=next(iter(DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType)));typ=base.Duplicate('ADER ABR - texto');typ.get_Parameter(DB.BuiltInParameter.TEXT_FONT).Set('Bahnschrift SemiBold Condensed');typ.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).Set(.0082)
        exported=[]
        for index,(v,title) in enumerate(views):
            row=index//columns;col=index%columns;xpos=left+(col+.5)*cwgrid;ypos=bottom+totalh-(row+.5)*ch
            v.Scale=25;vp=DB.Viewport.Create(doc,sheet.Id,v.Id,DB.XYZ(xpos,ypos,0));doc.Regenerate();outline=vp.GetBoxOutline();size=outline.MaximumPoint-outline.MinimumPoint
            required=25*max(size.X/(cwgrid-.10),size.Y/(ch-.14),1);v.Scale=next((s for s in [25,30,40,50,60,75,100,125,150,200,250,300,400,500] if s>=required),int(math.ceil(required)))
            doc.Regenerate();vp.SetBoxCenter(DB.XYZ(xpos,ypos,0))
            # Hide the native viewport label only on a dedicated duplicate type.
            vt=doc.GetElement(vp.GetTypeId());vtname='ADER ABR - viewport'
            custom=next((q for q in DB.FilteredElementCollector(doc).OfClass(DB.ElementType) if name(q)==vtname),None)
            if not custom:
                custom=vt.Duplicate(vtname)
                p=custom.get_Parameter(DB.BuiltInParameter.VIEWPORT_ATTR_SHOW_LABEL)
                if p:p.Set(0)
            vp.ChangeTypeId(custom.Id)
            doc.Regenerate();vp.SetBoxCenter(DB.XYZ(xpos,ypos,0))
            DB.TextNote.Create(doc,sheet.Id,DB.XYZ(left+col*cwgrid,bottom+totalh-row*ch-.02,0),clean(title)+'  1:'+str(v.Scale),typ.Id)
            out=vp.GetBoxOutline();exported.append({'id':eid(v),'name':clean(title),'scale':v.Scale,'box':[xyz(out.MinimumPoint),xyz(out.MaximumPoint)]})
        DB.TextNote.Create(doc,sheet.Id,DB.XYZ(.10,1.90,0),label,typ.Id)
        DB.TextNote.Create(doc,sheet.Id,DB.XYZ(.10,.23,0),u'Geometria nativa · Datos y materiales: schedules ADER ABR · Detalles limitados a lo modelado.',typ.Id)
        if not allitems:DB.TextNote.Create(doc,sheet.Id,DB.XYZ(.10,.16,0),u'Sin aberturas asociadas por Revit a este local: revisar asignacion. No equivale a cantidad cero.',typ.Id)
        assert tx.Commit()==DB.TransactionStatus.Committed
    except:
        if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
        raise
    record={'room_id':room_id,'sheet_id':eid(sheet),'sheet_number':sheet.SheetNumber,'name':label,'item_ids':[e['id'] for e in items],'curtain_ids':[e['id'] for e in cw],'views':exported,'exported':False}
    write(path,record);doc.Save();return record
def run(doc,uidoc):
    expected=os.path.abspath(os.path.join(ROOT,'../../outputs/casa-angel/Casa-Angel-piloto-documentacion.rvt'))
    docdir=os.path.abspath(os.path.join(ROOT,'../../outputs/casa-angel/documentacion'))
    isdoc=os.path.normcase(os.path.dirname(doc.PathName))==os.path.normcase(docdir) and os.path.basename(doc.PathName).startswith('Casa-Angel-DOC-')
    assert isdoc or os.path.normcase(doc.PathName)==os.path.normcase(expected),'Wrong document'
    job=read(os.path.join(ROOT,'openings-job.json'));action=job['action']
    if job.get('revision')=='r4':
        import imp
        return imp.load_source('ader_openings_r4',os.path.join(ROOT,'revit_openings_r4.py')).run(doc,uidoc,job)
    if job.get('revision')=='r2':
        import imp
        module=imp.load_source('ader_openings_r2',os.path.join(ROOT,'revit_openings_r2.py'))
        return module.run(doc,uidoc,job)
    if action=='paginate':
        p=os.path.join(OUT,'room-'+str(job['room_id'])+'.json');r=read(p)
        if r.get('pages'):return {'status':'success','pages':len(r['pages']),'existing':True}
        views=r['views'];chunks=[views[i:i+6] for i in range(0,len(views),6)];pages=[]
        tx=DB.Transaction(doc,'ADER openings - legible room sheets');tx.Start()
        try:
            first=doc.GetElement(DB.ElementId(Int64(r['sheet_id'])));typ=next(q for q in DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType) if name(q)=='ADER ABR - texto');vptype=next(q for q in DB.FilteredElementCollector(doc).OfClass(DB.ElementType) if name(q)=='ADER ABR - viewport')
            for n in list(DB.FilteredElementCollector(doc,first.Id).OfClass(DB.TextNote)):doc.Delete(n.Id)
            for vid in list(first.GetAllViewports()):doc.Delete(vid)
            for pageindex,group in enumerate(chunks):
                sheet=first if pageindex==0 else DB.ViewSheet.Create(doc,DB.ElementId(Int64(4428)))
                if pageindex>0:sheet.SheetNumber=r['sheet_number']+'-'+str(pageindex+1);sheet.Name=first.Name+' - Detalles '+str(pageindex+1)
                columns=2 if len(group)<=4 else 3;nr=int(math.ceil(float(len(group))/columns));w=2.2/columns;h=1.5/nr
                for i,meta in enumerate(group):
                    v=doc.GetElement(DB.ElementId(Int64(meta['id'])));v.Scale=25;vp=DB.Viewport.Create(doc,sheet.Id,v.Id,DB.XYZ.Zero);vp.ChangeTypeId(vptype.Id);doc.Regenerate();o=vp.GetBoxOutline();d=o.MaximumPoint-o.MinimumPoint;required=25*max(d.X/(w-.08),d.Y/(h-.10),1);v.Scale=next((s for s in [25,30,40,50,60,75,100,125,150,200,250,300,400,500] if s>=required),int(math.ceil(required)))
                    doc.Regenerate();vp.SetBoxCenter(DB.XYZ(.1+(i%columns+.5)*w,1.8-(i//columns+.5)*h,0));doc.Regenerate();o=vp.GetBoxOutline();meta.update(scale=v.Scale,box=[xyz(o.MinimumPoint),xyz(o.MaximumPoint)],sheet_id=eid(sheet),page=pageindex+1)
                    DB.TextNote.Create(doc,sheet.Id,DB.XYZ(.1+(i%columns)*w,1.8-(i//columns)*h-.02,0),clean(meta['name'])+'  1:'+str(meta['scale']),typ.Id)
                DB.TextNote.Create(doc,sheet.Id,DB.XYZ(.1,1.90,0),clean(r['name'])+' / '+str(pageindex+1)+' de '+str(len(chunks)),typ.Id)
                DB.TextNote.Create(doc,sheet.Id,DB.XYZ(.1,.23,0),u'Geometria nativa · Datos y materiales: schedules ADER ABR · Detalles limitados a lo modelado.',typ.Id)
                if not r['item_ids'] and not r['curtain_ids']:DB.TextNote.Create(doc,sheet.Id,DB.XYZ(.1,.16,0),u'Sin aberturas asociadas por Revit a este local: revisar asignacion. No equivale a cantidad cero.',typ.Id)
                pages.append({'sheet_id':eid(sheet),'number':sheet.SheetNumber,'views':group,'page':pageindex+1})
            assert tx.Commit()==DB.TransactionStatus.Committed
        except:
            if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
            raise
        r['pages']=pages;r['exported']=False;write(p,r);doc.Save();return {'status':'success','pages':len(pages)}
    if action=='layout':
        p=os.path.join(OUT,'room-'+str(job['room_id'])+'.json');r=read(p);sheet=doc.GetElement(DB.ElementId(Int64(r['sheet_id'])))
        tx=DB.Transaction(doc,'ADER openings - sheet layout');tx.Start()
        try:
            views=r['views'];columns=3 if len(views)>4 else 2;nr=int(math.ceil(float(len(views))/columns));w=2.2/columns;h=1.5/nr
            for i,meta in enumerate(views):
                v=doc.GetElement(DB.ElementId(Int64(meta['id'])));vp=next(doc.GetElement(k) for k in sheet.GetAllViewports() if doc.GetElement(k).ViewId==v.Id)
                v.Scale=25;doc.Regenerate();o=vp.GetBoxOutline();d=o.MaximumPoint-o.MinimumPoint;required=25*max(d.X/(w-.10),d.Y/(h-.14),1);v.Scale=next((s for s in [25,30,40,50,60,75,100,125,150,200,250,300,400,500] if s>=required),int(math.ceil(required)))
                doc.Regenerate();vp.SetBoxCenter(DB.XYZ(.1+(i%columns+.5)*w,.3+1.5-(i//columns+.5)*h,0));meta['scale']=v.Scale
            for n in DB.FilteredElementCollector(doc,sheet.Id).OfClass(DB.TextNote):
                for i,meta in enumerate(views):
                    if clean(n.Text).startswith(clean(meta['name'])+'  '):n.Coord=DB.XYZ(.1+(i%columns)*w,.3+1.5-(i//columns)*h-.02,0);n.Text=clean(meta['name'])+'  1:'+str(meta['scale']);break
            doc.Regenerate()
            for meta in views:
                vp=next(doc.GetElement(k) for k in sheet.GetAllViewports() if int(doc.GetElement(k).ViewId.Value)==meta['id']);o=vp.GetBoxOutline();meta['box']=[xyz(o.MinimumPoint),xyz(o.MaximumPoint)]
            tx.Commit()
        except:
            if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
            raise
        write(p,r);doc.Save();return {'status':'success','updated':job['room_id']}
    if action=='curtain_schedules':
        audit=read(os.path.join(OUT,'curtain-audit.json'));types=sorted(set(clean(w['type']) for w in audit));ss=[]
        tx=DB.Transaction(doc,'ADER openings - curtain wall schedules');tx.Start()
        try:
            for typ in types:
                title=u'ADER ABR - Cerramientos - '+typ
                old=next((s for s in DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule) if name(s)==title),None)
                if old:ss.append(old);continue
                s=schedule(doc,DB.BuiltInCategory.OST_Walls,title);d=s.Definition
                sf=next(f for f in d.GetSchedulableFields() if f.GetName(doc)=='Type');f=d.AddField(sf);f.IsHidden=True;d.AddFilter(DB.ScheduleFilter(f.FieldId,DB.ScheduleFilterType.Equal,next(w.WallType.Id for w in DB.FilteredElementCollector(doc).OfClass(DB.Wall) if w.WallType.Kind==DB.WallKind.Curtain and name(w.WallType)==typ)));ss.append(s)
            assert tx.Commit()==DB.TransactionStatus.Committed
        except:
            if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
            raise
        p=os.path.join(OUT,'schedules.json');old=read(p);write(p,old+[{'id':eid(s),'name':name(s)} for s in ss]);doc.Save();return {'status':'success','schedules':len(ss)}
    if action=='schedules':
        tx=DB.Transaction(doc,'ADER openings - native schedules');tx.Start()
        try:
            ss=[]
            for cat,label in [(DB.BuiltInCategory.OST_Windows,'Ventanas'),(DB.BuiltInCategory.OST_Doors,'Puertas')]:
                ss.append(schedule(doc,cat,'ADER ABR - '+label+' por local'))
                ss.append(schedule(doc,cat,'ADER ABR - Materiales de '+label.lower(),True))
            sw=schedule(doc,DB.BuiltInCategory.OST_Walls,'ADER ABR - Cerramientos de muro cortina')
            # Filter by exact type names found in the live curtain-wall audit.
            # Wall Kind is not a schedulable field, so isolate each exact type with a separate native schedule.
            # The all-walls probe is rolled back below; create per-type schedules outside this helper.
            doc.Delete(sw.Id)
            assert tx.Commit()==DB.TransactionStatus.Committed
        except:
            if tx.GetStatus()==DB.TransactionStatus.Started:tx.RollBack()
            raise
        write(os.path.join(OUT,'schedules.json'),[{'id':eid(s),'name':name(s)} for s in ss]);doc.Save()
        return {'status':'success','schedules':[{'id':eid(s),'name':name(s)} for s in ss]}
    if action=='room':
        record=make_room(doc,int(job['room_id']));return {'status':'success','room':record}
    if action=='export':
        p=os.path.join(OUT,'room-'+str(job['room_id'])+'.json');r=read(p);sheet=doc.GetElement(DB.ElementId(Int64(r['sheet_id'])))
        opts=DB.PDFExportOptions();opts.Combine=True;opts.FileName='aberturas-'+str(job['room_id']);opts.PaperFormat=DB.ExportPaperFormat.ISO_A1;opts.PaperOrientation=DB.PageOrientationType.Landscape;opts.ZoomType=DB.ZoomType.FitToPage;opts.ColorDepth=DB.ColorDepthType.Color;opts.StopOnError=True
        sheets=[doc.GetElement(DB.ElementId(Int64(x['sheet_id']))) for x in r.get('pages',[])] or [sheet]
        r['exported']=bool(doc.Export(OUT,List[DB.ElementId]([s.Id for s in sheets]),opts));write(p,r)
        return {'status':'success','exported':r['exported'],'room_id':job['room_id']}
    if action=='verify':
        before=read(os.path.join(OUT,'physical-before.json'));after=sanitize_for_json(physical(doc));assert before==after,'Opening geometry or parameters changed'
        curtains=read(os.path.join(OUT,'curtain-audit.json'))
        for original in curtains:
            e=doc.GetElement(DB.ElementId(Int64(original['id'])));assert original['bbox']==bbox(e),'Curtain wall geometry changed';assert original['params']==sanitize_for_json(params(e)),'Curtain wall parameters changed'
        result={'status':'success','geometry_and_parameters_unchanged':True,'elements':len(after),'curtain_walls':len(curtains)};write(os.path.join(OUT,'verification.json'),result);return result
    if action=='curtain_audit':
        data=[]
        rooms=list(DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType())
        for w in DB.FilteredElementCollector(doc).OfClass(DB.Wall):
            if w.WallType.Kind!=DB.WallKind.Curtain:continue
            boundary_rooms=[]
            for r in rooms:
                try:
                    loops=r.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
                    if loops and any(seg.ElementId==w.Id for loop in loops for seg in loop):boundary_rooms.append(eid(r))
                except:pass
            data.append({'id':eid(w),'uid':w.UniqueId,'type':name(w.WallType),'bbox':bbox(w),'rooms':boundary_rooms,'level':int(w.LevelId.Value),'panels':[int(i.Value) for i in w.CurtainGrid.GetPanelIds()],'mullions':[int(i.Value) for i in w.CurtainGrid.GetMullionIds()],'params':params(w),'type_parameters':params(w.WallType)})
        write(os.path.join(OUT,'curtain-audit.json'),data)
        return {'status':'success','curtain_walls':len(data),'with_boundary_rooms':len([w for w in data if w['rooms']])}
    if action=='audit':
        rooms=[r for r in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType()]
        rows=[];phase=doc.Phases.get_Item(doc.Phases.Size-1)
        for e in openings(doc):
            associations={}
            for side in ['FromRoom','ToRoom','Room']:
                try:
                    r=getattr(e,'get_'+side)(phase)
                    if r:associations[side]=eid(r)
                except:pass
            rows.append({'id':eid(e),'uid':e.UniqueId,'category':e.Category.Name,'family':e.Symbol.FamilyName,'type':name(e.Symbol),'mark':e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK).AsString(),'host':eid(e.Host) if e.Host else None,'host_thickness_m':e.Host.Width*.3048 if isinstance(e.Host,DB.Wall) else None,'parent':eid(e.SuperComponent) if e.SuperComponent else None,'level':int(e.LevelId.Value),'bbox':bbox(e),'point':xyz(e.Location.Point) if isinstance(e.Location,DB.LocationPoint) else None,'facing':xyz(e.FacingOrientation),'hand':xyz(e.HandOrientation),'rooms':associations,'instance':params(e),'type_parameters':params(e.Symbol),'materials':[name(doc.GetElement(i)) for i in e.GetMaterialIds(False)]})
        fields={};tx=DB.Transaction(doc,'ADER openings capability probe - rollback');tx.Start()
        try:
            for cat in [DB.BuiltInCategory.OST_Windows,DB.BuiltInCategory.OST_Doors]:
                s=DB.ViewSchedule.CreateSchedule(doc,DB.ElementId(cat));fields[str(cat)]=[{'name':f.GetName(doc),'id':int(f.ParameterId.Value),'field_type':str(f.FieldType)} for f in s.Definition.GetSchedulableFields()]
        finally:tx.RollBack()
        data={'model':os.path.basename(doc.PathName),'readAt':datetime.datetime.utcnow().isoformat()+'Z','phase':name(phase),'items':rows,'rooms':[{'id':eid(r),'name':r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString(),'number':r.Number,'area_m2':r.Area*.09290304,'level':int(r.LevelId.Value),'level_name':name(doc.GetElement(r.LevelId)),'bbox':bbox(r)} for r in rooms],'fields':fields,'view_types':[{'id':eid(v),'name':name(v),'family':str(v.ViewFamily)} for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)],'titleblocks':[{'id':eid(t),'name':name(t),'family':t.FamilyName} for t in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType()],'links':[{'id':eid(l),'name':name(l)} for l in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance)],'curtain_panels':DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_CurtainWallPanels).WhereElementIsNotElementType().GetElementCount()}
        write(os.path.join(OUT,'audit.json'),data);write(os.path.join(OUT,'physical-before.json'),physical(doc))
        return {'status':'success','windows_doors':len(rows),'rooms':len(rooms),'path':os.path.join(OUT,'audit.json')}
    raise Exception('Unsupported openings job')


