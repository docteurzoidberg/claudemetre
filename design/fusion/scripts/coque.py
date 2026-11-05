# Étape 1a : paramètres utilisateur + coque (imprimée sur le dos, façade ouverte vers -Y).
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

PARAMS = [
    # Coque
    ('coque_L', '200 mm', 'Coque : largeur'),
    ('coque_H', '96 mm', 'Coque : hauteur'),
    ('coque_P', '40 mm', 'Coque : profondeur, du mur à la façade'),
    ('coque_ep', '2.5 mm', 'Coque : épaisseur des parois'),
    ('coque_fond', '3 mm', 'Coque : épaisseur du fond (côté mur)'),
    ('coque_R', '3 mm', 'Coque : rayon des arêtes de coin'),
    ('coque_Rf', '2.5 mm', 'Coque : arrondi du pourtour de la façade'),
    ('rebord_ep', '3 mm', 'Coque : épaisseur du rebord avant qui porte la platine'),
    ('ouv_L', '168 mm', 'Coque : largeur de l ouverture avant'),
    ('ouv_H', '76 mm', 'Coque : hauteur de l ouverture avant'),
    ('chanfrein_p', 'max(( coque_L - 2 * coque_ep - ouv_L ) / 2; ( coque_H - 2 * coque_ep - ouv_H ) / 2)',
     'Coque : profondeur du chanfrein à 45° sous le rebord (impression sans support)'),
    # Visserie M3 + inserts laiton
    ('vis_x', '88 mm', 'Vis de platine : demi-entraxe horizontal'),
    ('vis_z', '39 mm', 'Vis de platine : demi-entraxe vertical'),
    ('vis_d', '3.4 mm', 'M3 : perçage de passage'),
    ('fraise_d', '6.4 mm', 'M3 tête fraisée (FHC) : diamètre de la fraisure'),
    ('insert_d', '4.2 mm', 'Insert M3 (Ø5 x 4) : diamètre du logement'),
    ('insert_p', '4.5 mm', 'Insert M3 (Ø5 x 4) : profondeur du logement'),
    ('vis_coque_p', '8 mm', 'Coque : profondeur du perçage des inserts de platine (vis FHC M3x8)'),
]


def is_corner_edge(e, L, H):
    g = e.geometry
    if not isinstance(g, adsk.core.Line3D):
        return False
    a, b = e.startVertex.geometry, e.endVertex.geometry
    if abs(a.x - b.x) > 1e-4 or abs(a.z - b.z) > 1e-4:
        return False
    return abs(abs(a.x) - L / 2) < 1e-3 and abs(abs(a.z) - H / 2) < 1e-3


def run(ctx):
    d = design()
    set_params(PARAMS)
    occ = new_component('coque')
    comp = occ.component
    occ.activate()
    wall = toward_wall(comp)
    xz = comp.xZConstructionPlane

    sk = sketch(comp, xz, 'coque_contour')
    centered_rect(sk, 'coque_L', 'coque_H')
    body = extrude(comp, sk.profiles.item(0), NEW, 'coque_P', wall, 'coque_bloc').bodies.item(0)
    body.name = 'coque'
    L, H = ev('coque_L'), ev('coque_H')
    fillet(comp, [e for e in body.edges if is_corner_edge(e, L, H)], 'coque_R', 'coque_coins')

    sk = sketch(comp, xz, 'coque_ouverture')
    centered_rect(sk, 'ouv_L', 'ouv_H')
    extrude(comp, sk.profiles.item(0), CUT, 'rebord_ep', wall, 'coque_ouverture', [body])

    pl1 = plane_y(comp, 'rebord_ep', 'plan_rebord')
    pl2 = plane_y(comp, 'rebord_ep + chanfrein_p', 'plan_chanfrein')
    s_haut = sketch(comp, pl1, 'chanfrein_haut')
    centered_rect(s_haut, 'ouv_L', 'ouv_H')
    s_cav = sketch(comp, pl2, 'cavite')
    centered_rect(s_cav, 'coque_L - 2 * coque_ep', 'coque_H - 2 * coque_ep')
    lf = comp.features.loftFeatures
    li = lf.createInput(CUT)
    li.loftSections.add(s_haut.profiles.item(0))
    li.loftSections.add(s_cav.profiles.item(0))
    li.isSolid = True
    li.participantBodies = [body]
    lf.add(li).name = 'coque_chanfrein'
    extrude(comp, s_cav.profiles.item(0), CUT, 'coque_P - coque_fond - rebord_ep - chanfrein_p', wall,
            'coque_cavite', [body])

    # Pilier d'angle (+X, +Z), du rebord au fond, ancré à mi-épaisseur des parois ; puis miroirs.
    sk = sketch(comp, pl1, 'pilier')
    w = '( coque_L - coque_ep - ouv_L ) / 2'
    h = '( coque_H - coque_ep - ouv_H ) / 2'
    rect(sk, w, h, 'ouv_L / 2', 'ouv_H / 2', sx=-1, sz=-1,
         cx=ev('ouv_L / 2') + ev(w) / 2, cz=ev('ouv_H / 2') + ev(h) / 2)
    pil = extrude(comp, sk.profiles.item(0), JOIN, 'coque_P - coque_fond - rebord_ep', wall, 'pilier', [body])
    m1 = mirror(comp, [pil], comp.yZConstructionPlane, 'pilier_miroir_x')
    mirror(comp, [pil, m1], comp.xYConstructionPlane, 'pilier_miroir_z')

    # Logements d'inserts M3 dans les piliers, depuis la façade.
    sk = sketch(comp, xz, 'inserts_platine')
    pts = four_points(sk, sk.originPoint, 0, 0, 'vis_x', 'vis_z')
    hole(comp, pts, 'lamage', 'vis_d', 'vis_coque_p', True, 'inserts_platine', [body],
         cb_d='insert_d', cb_p='insert_p')

    # Arrondi du pourtour de la façade.
    front = None
    for f in body.faces:
        g = f.geometry
        if isinstance(g, adsk.core.Plane) and abs(f.pointOnFace.y) < 1e-4:
            if front is None or f.area > front.area:
                front = f
    outer = [lp for lp in front.loops if lp.isOuter][0]
    fillet(comp, list(outer.edges), 'coque_Rf', 'coque_arrondi_facade')

    d.activateRootComponent()
    mn, mx = bbox_mm(body)
    print('bodies', comp.bRepBodies.count, 'bbox', mn, mx, 'vol cm3', round(body.volume, 1))
    print('chanfrein_p', round(ev('chanfrein_p') * 10, 2), 'unhealthy', unhealthy())
