# Étape 2 : visière de l'afficheur, imprimée à part (debout sur son chant arrière) et collée dans
# une rainure en U de la platine (la platine s'imprime face avant sur le plateau).
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

PARAMS = [
    ('visiere_L', '62 mm', 'Visière : largeur hors tout'),
    ('visiere_ep', '1.8 mm', 'Visière : épaisseur du toit et des joues'),
    ('visiere_P', '12 mm', 'Visière : saillie devant la platine'),
    ('visiere_dz_haut', '15.4 mm', 'Visière : dessus du toit, au-dessus du centre de l afficheur'),
    ('visiere_dz_bas', '11.5 mm', 'Visière : bas des joues, sous le centre de l afficheur'),
    ('rainure_p', '1.5 mm', 'Rainure de la visière dans la platine : profondeur'),
    ('rainure_jeu', '0.2 mm', 'Rainure de la visière : jeu total sur la largeur (collage)'),
]


def u_profile(sk, grow_e):
    """U de la visière (grow_e = surépaisseur de chaque côté, '0 mm' pour la visière) ;
    renvoie le profil en U (aire la plus proche de l'aire attendue)."""
    g = '( %s )' % grow_e
    rect(sk, 'visiere_L + 2 * %s' % g, 'visiere_dz_haut + visiere_dz_bas + 2 * %s' % g,
         'visiere_L / 2 + %s - aff_x' % g, 'visiere_dz_bas + %s - aff_z' % g, sx=-1, sz=-1,
         cx=ev('aff_x'), cz=ev('aff_z') + (ev('visiere_dz_haut') - ev('visiere_dz_bas')) / 2)
    hi = 'visiere_dz_haut + visiere_dz_bas + 1 mm - visiere_ep'
    top_in = ev('aff_z + visiere_dz_haut - visiere_ep') - ev(g)
    h_in = ev(hi)
    rect(sk, 'visiere_L - 2 * visiere_ep - 2 * %s' % g, hi,
         'visiere_L / 2 - visiere_ep - %s - aff_x' % g, 'aff_z + visiere_dz_haut - visiere_ep - %s' % g,
         sx=-1, sz=1, cx=ev('aff_x'), cz=top_in - h_in / 2)
    L, H, e, gg = ev('visiere_L'), ev('visiere_dz_haut + visiere_dz_bas'), ev('visiere_ep'), ev(g)
    want = (L + 2 * gg) * (e + 2 * gg) + 2 * (e + 2 * gg) * (H - e)
    return min(profiles(sk), key=lambda p: abs(prof_area(p) - want))


def run(ctx):
    d = design()
    set_params(PARAMS)
    root = d.rootComponent

    # 1. Perçages de l'afficheur limités à l'insert (la vis M3x6 s'y arrête) : ils ne croisent plus la rainure.
    pocc = [o for o in root.occurrences if o.component.name == 'platine'][0]
    pcomp = pocc.component
    h = pcomp.features.holeFeatures.itemByName('bossages_afficheur_inserts')
    h.extentDefinition.distance.expression = 'insert_p + 0.5 mm'

    # 2. Rainure en U dans la face avant de la platine.
    pocc.activate()
    body = pcomp.bRepBodies.item(0)
    pl = pcomp.constructionPlanes.itemByName('plan_face_platine')
    sk = sketch(pcomp, pl, 'rainure_visiere')
    prof = u_profile(sk, 'rainure_jeu / 2')
    extrude(pcomp, prof, CUT, 'rainure_p', toward_wall(pcomp), 'rainure_visiere', [body])
    d.activateRootComponent()

    # 3. Visière, du fond de la rainure jusqu'à visiere_P devant la platine.
    occ = new_component('visiere')
    comp = occ.component
    occ.activate()
    pl = plane_y(comp, 'rainure_p - platine_ep', 'plan_fond_rainure')
    sk = sketch(comp, pl, 'visiere')
    prof = u_profile(sk, '0 mm')
    vb = extrude(comp, prof, NEW, 'visiere_P + rainure_p', toward_front(comp), 'visiere').bodies.item(0)
    vb.name = 'visiere'
    d.activateRootComponent()
    vb.appearance = d.appearances.itemByName('PLA kaki')

    mn, mx = bbox_mm(vb)
    print('visiere', mn, mx, 'vol', round(vb.volume * 1000, 1), 'mm3')
    # Rainure : faces planes de la platine à y = -platine_ep + rainure_p (fond de rainure).
    yb = ev('rainure_p - platine_ep')
    a = sum(f.area for f in body.faces if isinstance(f.geometry, adsk.core.Plane) and abs(f.pointOnFace.y - yb) < 1e-4)
    print('fond de rainure', round(a * 100, 1), 'mm2', 'unhealthy', unhealthy())
