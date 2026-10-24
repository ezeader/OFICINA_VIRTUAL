"""R31: add the read-only structure checks (est31-checks.json) and the user's decisions to public/casa-angel/structure/manifest.json (additive)."""
import json, sys
from pathlib import Path

W = Path(__file__).parent


def clean(s): return s.encode('latin-1', 'backslashreplace').decode('unicode_escape') if isinstance(s, str) and '\\x' in s else s


def main(public):
    c = json.loads((W / 'openings-r4' / 'est31-checks.json').read_text(encoding='utf-8'))
    E = {k: dict(v, materials=[clean(x) for x in v['materials']], type=clean(v['type'])) for k, v in c['elements'].items()}
    p = Path(public) / 'structure' / 'manifest.json'; m = json.loads(p.read_text(encoding='utf-8'))
    code = {str(x['id']): x['code'] for x in m['codes']}
    P = {(x['a'], x['b']): x for x in c['pairs']}
    elev = [k for k in E if code.get(k, '').startswith('LO-P') and code[k][3:5] in ('PA', 'PE')]
    m['checks'] = {
        'revision': 'R31', 'readAt': c['readAt'], 'source': 'lectura del modelo principal vinculado (sin cambios)',
        'loPb01VsPlatea': {'LO-PB-01': 714161, 'PL-01': 2287528, 'intersection_m2': P[(714161, 2287528)]['intersection_m2'], 'loPb01OutsidePlatea_m2': P[(714161, 2287528)]['aOutsideB_m2'],
                           'levels_m': {'LO-PB-01': [E['714161']['zBottom_m'], E['714161']['zTop_m']], 'PL-01': [E['2287528']['zBottom_m'], E['2287528']['zTop_m']]},
                           'note': 'No se superponen en planta: no hay hormigón contado dos veces. Para que toda la PB vaya sobre platea, PL-01 debe crecer 124,13 m² (huella de LO-PB-01).'},
        'overlaps': [
            {'a': 'LO-PA-05', 'b': 'LO-PA-06', 'ids': [2156409, 2156920], 'intersection_m2': P[(2156409, 2156920)]['intersection_m2'], 'note': 'despreciable'},
            {'a': '467187 Deck Terraza PA 05cm (madera)', 'b': 'LO-PA-04', 'ids': [467187, 2156155], 'intersection_m2': P[(467187, 2156155)]['intersection_m2'], 'note': 'deck de madera sobre la losa: terminación, no hormigón'},
            {'a': '467187 Deck Terraza PA 05cm (madera)', 'b': 'LO-PA-05', 'ids': [467187, 2156409], 'intersection_m2': P[(467187, 2156409)]['intersection_m2'], 'note': 'idem'},
            {'a': '734491 Calle (tierra)', 'b': 'LO-PB-01', 'ids': [734491, 714161], 'intersection_m2': P[(734491, 714161)]['intersection_m2'], 'note': 'sin superposición en planta (el caso de revisión era por caja envolvente)'}],
        'materials': {'VE-PA-01': E['667007']['materials'], 'VE-PE-01': E['614629']['materials'], 'note': 'Hormigón de fachada (confirmado por el usuario)'},
        'perimeters_m': dict([('PL-01', E['2287528']['perimeter_m'])] + sorted((code[k], E[k]['perimeter_m']) for k in elev))}
    m.setdefault('decisions', [])
    for t in ['Usuario: toda la PB va sobre la platea; LO-PB-01 se documenta como paquete de piso sobre platea (pendiente: archivo DOC de Estructura).',
              'Usuario: vigas de encuentro VE-PA-01 / VE-PE-01 son de hormigón.', 'Usuario: acero por cuantía de referencia hasta tener el cálculo estructural.']:
        if t not in m['decisions']: m['decisions'].append(t)
    p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(m['checks']['perimeters_m'], ensure_ascii=False))


if __name__ == '__main__': main(sys.argv[1])
