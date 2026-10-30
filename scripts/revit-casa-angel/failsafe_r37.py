# -*- coding: utf-8 -*-
"""R37: failure handling for every ADER transaction so no job ever waits on a Revit dialog.
- warnings: deleted;
- "Can't keep elements joined": resolved with Unjoin (DetachElements) when Revit offers it;
- any other error, or a join error without that resolution: RollBack (never 'Delete elements');
every failure is logged (doc, element ids, category, room) to openings-r4/failures.jsonl and kept in LOG for the job reply."""
import os, json, io, datetime
from Autodesk.Revit import DB

OUT = os.path.join(os.path.dirname(__file__), 'openings-r4')
LOG = []

def _desc(doc, ids):
    out = []
    for i in ids:
        e = doc.GetElement(i)
        rm = None
        try:
            ph = doc.Phases.get_Item(doc.Phases.Size - 1)
            loc = getattr(e, 'Location', None); p = getattr(loc, 'Point', None) or (loc.Curve.Evaluate(.5, True) if hasattr(loc, 'Curve') else None)
            r = doc.GetRoomAtPoint(p, ph) if p is not None else None
            rm = r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString() if r is not None else None
        except Exception: pass
        out.append({'id': i.IntegerValue, 'category': e.Category.Name if e is not None and e.Category is not None else None, 'room': rm})
    return out

def _write(rec):
    LOG.append(rec)
    try:
        with io.open(os.path.join(OUT, 'failures.jsonl'), 'a', encoding='utf-8') as f: f.write(json.dumps(rec, ensure_ascii=False) + u'\n')
    except Exception: pass

class Preprocessor(DB.IFailuresPreprocessor):
    def __init__(self, label): self.label = label
    def PreprocessFailures(self, fa):
        doc = fa.GetDocument(); result = DB.FailureProcessingResult.Continue
        for f in list(fa.GetFailureMessages()):
            sev = f.GetSeverity(); text = f.GetDescriptionText()
            rec = {'at': datetime.datetime.utcnow().isoformat(), 'tx': self.label, 'doc': os.path.basename(doc.PathName), 'severity': str(sev), 'text': text,
                   'elements': _desc(doc, list(f.GetFailingElementIds()) + list(f.GetAdditionalElementIds()))}
            if sev == DB.FailureSeverity.Warning:
                fa.DeleteWarning(f); rec['action'] = 'warning borrado'; _write(rec); continue
            if f.HasResolutionOfType(DB.FailureResolutionType.DetachElements):
                f.SetCurrentResolutionType(DB.FailureResolutionType.DetachElements); fa.ResolveFailure(f)
                rec['action'] = 'desunido (Unjoin)'; _write(rec); result = DB.FailureProcessingResult.ProceedWithCommit; continue
            rec['action'] = 'rollback'; _write(rec)
            return DB.FailureProcessingResult.ProceedWithRollBack
        return result

def arm(tx, label=None):
    """Attach the preprocessor to a started or not-yet-started transaction (no modal dialogs)."""
    o = tx.GetFailureHandlingOptions()
    o.SetFailuresPreprocessor(Preprocessor(label or tx.GetName())); o.SetForcedModalHandling(False); o.SetClearAfterRollback(True)
    tx.SetFailureHandlingOptions(o)
    return tx

def _on_failures(sender, args):
    """Application.FailuresProcessing handler, active only while an ADER job runs (same rules as Preprocessor)."""
    fa = args.GetFailuresAccessor()
    if fa.GetFailureMessages().Count == 0: return
    r = Preprocessor(fa.GetTransactionName()).PreprocessFailures(fa)
    if r == DB.FailureProcessingResult.ProceedWithRollBack: args.SetProcessingResult(DB.FailureProcessingResult.ProceedWithRollBack)
    elif r == DB.FailureProcessingResult.ProceedWithCommit: args.SetProcessingResult(DB.FailureProcessingResult.ProceedWithCommit)

def during(app, fn):
    """Run fn() with the handler attached; the job reply carries the failures logged meanwhile."""
    del LOG[:]
    app.FailuresProcessing += _on_failures
    try: res = fn()
    finally: app.FailuresProcessing -= _on_failures
    if LOG and isinstance(res, dict): res = dict(res, failures=list(LOG))
    return res
