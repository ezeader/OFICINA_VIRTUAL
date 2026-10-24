"""R27: add `budget` (partidas a cotizar, sin solapes, ids estables) to public/casa-angel/rubros/<clave>/manifest.json.
Run after any rubro publisher (publishers rewrite the manifest). Units: m², ml, m³, u, kg, gl."""
import argparse, json
from pathlib import Path


def c2(v): return ('%.2f' % v).replace('.', ',')


def tot(m, label):
    return next(t for t in m['totals'] if t['label'].startswith(label))


def qsum(m, group, prefix=None):
    return sum(q['value'] for q in m['quantities'] if q.get('group') == group and (prefix is None or q['label'].startswith(prefix)))


def slug(t):
    import unicodedata, re
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub('[^a-z0-9]+', '-', t).strip('-')


def L(id, label, value, unit, detail='', informative=False):
    return {'id': slug(id), 'label': label, 'value': round(value, 2), 'unit': unit, 'detail': detail, 'informative': informative}


def from_total(m, id, label, unit=None, informative=False, name=None):
    t = tot(m, label); return L(id, name or t['label'], t['value'], unit or t['unit'], t.get('detail') or '', informative)


def build(k, m):
    if k == 'albanileria':
        return [from_total(m, 'mamposteria-interior', 'Mampostería y tabiques'), from_total(m, 'durlock', 'Durlock'), from_total(m, 'muros-fachada', 'Muros de fachada'),
                from_total(m, 'muros-todos', 'Muros y tabiques (todos)', informative=True)]
    if k == 'cielorrasos':
        out = [L('cielorraso-' + t['detail'], 'Cielorraso ' + t['label'], t['value'], 'm²', t['detail']) for t in m['totals'] if (t.get('detail') or '').startswith('TC-')]
        return out + [from_total(m, 'faltante-sin-cielorraso', 'Locales sin cielorraso', informative=True, name='Locales sin cielorraso modelado (faltante, no es partida)'),
                      from_total(m, 'faltante-parcial', 'Locales con cielorraso parcial', informative=True), from_total(m, 'cielorrasos-modelados', 'Cielorrasos modelados', informative=True)]
    if k == 'climatizacion':
        return [from_total(m, 'serpentin-pb', 'Serpentín PB'), from_total(m, 'serpentin-pa', 'Serpentín PA'), from_total(m, 'serpentin-pe', 'Serpentín PE'),
                from_total(m, 'distribucion-montantes', 'Distribución y montantes'),
                L('colectores', 'Colectores de piso radiante', qsum(m, 'Colectores'), 'u', 'CO-N, CO-S'), L('gabinetes-colector', 'Gabinetes de colector', qsum(m, 'Gabinetes de colector'), 'u', 'GA-N, GA-S'),
                L('cronotermostatos', 'Cronotermostatos', qsum(m, 'Cronotermostatos'), 'u', 'TE-01 a TE-11'), L('bomba-circulacion', 'Bomba de circulación', qsum(m, 'Bomba (genérica)'), 'u', 'genérica; la bomba de calor no está modelada'),
                from_total(m, 'pex-total', 'Tubo PEX', informative=True, name='Tubo PEX Ø20 total (= serpentines + distribución)')]
    if k == 'cubierta':
        al = qsum(m, 'Aleros')
        return [from_total(m, 'tejas', 'Tejas'), from_total(m, 'vigas-vc', 'Vigas 6×20'), from_total(m, 'piezas-vp', 'Piezas 3×10'), from_total(m, 'correas-cr', 'Correas'),
                L('fascias', 'Fascias / zinguería de borde', qsum(m, 'Zinguería', 'FA'), 'ml', 'FA-01 a FA-04'), L('canaletas', 'Canaletas', qsum(m, 'Zinguería', 'CA'), 'ml', 'CA-01, CA-02; bajadas no modeladas'),
                L('alero-metalico', 'Alero metálico', al, 'm²', 'AL-01, AL-02'), from_total(m, 'madera-total', 'Madera total', informative=True, name='Madera total (= VC + VP + CR)')]
    if k == 'equipamiento':
        g = lambda kind: [c for c in m['codes'] if c['kind'] == kind]
        mu = g('MU'); out = [from_total(m, 'placares', 'Placares')]
        for what in sorted(set(c['label'].split(' · ')[1] for c in mu)):
            out.append(L('muebles-' + what.replace(' ', '-'), 'Muebles fijos · ' + what, len([c for c in mu if c['label'].split(' · ')[1] == what]), 'u', ', '.join(c['code'] for c in mu if c['label'].split(' · ')[1] == what)))
        out += [from_total(m, 'vanitorios', 'Vanitorios'), from_total(m, 'mesadas', 'Mesadas'), from_total(m, 'lavaderos', 'Lavaderos'), from_total(m, 'mamparas', 'Mamparas'),
                from_total(m, 'equipos-cocina', 'Equipos de cocina'), from_total(m, 'equipamiento-total', 'Equipamiento fijo', informative=True, name='Equipamiento fijo (resumen de las anteriores)')]
        return out
    if k == 'exteriores':
        return [from_total(m, 'base-acceso', 'Base de acceso'), from_total(m, 'escalones-acceso', 'Escalones de acceso'),
                L('escalera-exterior', 'Escalera exterior', 1, 'gl', tot(m, 'Escalera exterior')['detail'] + ' · ' + str(tot(m, 'Escalera exterior')['value']) + ' alzadas'),
                from_total(m, 'barandas-exteriores', 'Barandas exteriores'), from_total(m, 'porton', 'Portón'),
                from_total(m, 'calle', 'Calle', informative=True, name='Calle (piso del modelo, referencia)'), from_total(m, 'terreno', 'Terreno', informative=True, name='Terreno (toposólidos, referencia)')]
    if k == 'pileta':
        va = tot(m, 'Muros del vaso')
        return [L('vaso-muros', 'Muros del vaso (hormigón)', float(va['detail'].split('·')[1].strip().split(' ')[0].replace(',', '.')), 'm³', f"{c2(va['value'])} m² · 4 muros"),
                from_total(m, 'vaso-fondo', 'Fondo'), from_total(m, 'borde-solarium', 'Borde'), from_total(m, 'venecitas', 'Revestimiento venecitas'), from_total(m, 'agua-llenado', 'Agua', name='Llenado de agua')]
    if k == 'pisos':
        out = [L('piso-' + t['label'].replace('Piso ', '').lower().replace(' ', '-').replace('ó', 'o'), t['label'], t['value'], t['unit'], t.get('detail', '')) for t in m['totals'] if t['label'].startswith('Piso ')]
        return out + [from_total(m, 'zocalos', 'Zócalo a computar', name='Zócalos'), from_total(m, 'zocalos-modelados', 'Zócalos modelados', informative=True), from_total(m, 'pisos-todos', 'Pisos (todos', informative=True)]
    if k == 'revestimientos':
        return [from_total(m, 'revestimiento-banos', 'Revestimiento baños'), from_total(m, 'revestimiento-franjas', 'Franjas cocina'), from_total(m, 'pintura-muros', 'Pintura de muros'),
                from_total(m, 'revestimiento-total', 'Revestimiento total', informative=True)]
    if k == 'parrilla':
        return [L('parrilla', 'Parrilla (equipo o de obra)', 1, 'u', tot(m, 'Parrilla')['detail']), from_total(m, 'conducto-humos', 'Conductos de humo')]
    if k == 'electrica':
        b = tot(m, 'Bocas')
        return [from_total(m, 'tablero-general', 'Tableros', name='Tablero general'), L('bocas', 'Bocas (propuesta preliminar)', b['value'], 'u', b['detail'])]
    if k == 'gas':
        return [L('artefactos-gas', 'Artefactos posibles a gas', 1, 'u', 'cocina dual fuel; red de gas sin definir', True)]
    if k == 'domotica':
        return [L('locales', 'Locales a cubrir', tot(m, 'Locales')['value'], 'u', 'sin alcance definido', True)]
    if k == 'solar':
        return [L('aguas-candidatas', 'Aguas de techo candidatas', tot(m, 'Aguas')['value'], 'm²', 'orientación a confirmar; sistema sin definir', True)]
    raise KeyError(k)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); a = ap.parse_args()
    for p in sorted((a.public_dir / 'rubros').glob('*/manifest.json')):
        k = p.parent.name; m = json.loads(p.read_text(encoding='utf-8'))
        lines = build(k, m)
        ids = [x['id'] for x in lines]; assert len(ids) == len(set(ids)), k
        m['budget'] = {'revision': 'R27', 'note': 'Partidas a cotizar sin solapes; informative = referencia (no se suma).', 'lines': lines}
        p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
        print(k, [(x['id'], x['value'], x['unit'], 'i' if x['informative'] else '') for x in lines])


if __name__ == '__main__': main()
