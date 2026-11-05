# Étape 1b : platine (impression face avant sur le plateau), perçages et bossages d'inserts au dos.
import adsk.core, adsk.fusion, os

LIB = os.path.join(os.path.dirname(__file__), 'lib.py')
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'))

PARAMS = [
    ('platine_L', '188 mm', 'Platine : largeur'),
    ('platine_H', '90 mm', 'Platine : hauteur'),
    ('platine_ep', '3 mm', 'Platine : épaisseur'),
    ('platine_R', '3 mm', 'Platine : rayon des coins'),
    # Voltmètres SO-45
    ('jauge_x', '58 mm', 'SO-45 : demi-entraxe horizontal des deux jauges'),
    ('jauge_z', '8 mm', 'SO-45 : hauteur de l axe des jauges'),
    ('jauge_trou_d', '46 mm', 'SO-45 : passage du corps Ø45'),
    ('jauge_vis_e', '37 mm', 'SO-45 : entraxe des trous de collerette'),
    ('jauge_bossage_d', '8 mm', 'SO-45 : bossages d inserts au dos de la platine'),
    ('jauge_bossage_h', '5 mm', 'SO-45 : hauteur des bossages (vis CHC M3x12)'),
    # Afficheur TM1637 0,56"
    ('aff_x', '0 mm', 'Afficheur : position horizontale du centre'),
    ('aff_z', '11 mm', 'Afficheur : hauteur du centre'),
    ('aff_fen_L', '50.8 mm', 'Afficheur : fenêtre dans la platine (afficheur 50,2)'),
    ('aff_fen_H', '19.6 mm', 'Afficheur : fenêtre dans la platine (afficheur 19,0)'),
    ('aff_saillie', '0.3 mm', 'Afficheur : saillie de la face devant la platine'),
    ('aff_prof', '8 mm', 'Afficheur : de la face au circuit imprimé'),
    ('aff_pcb_dx', '1.6 mm', 'Afficheur : décalage du circuit vers la droite'),
    ('aff_trou_ex', '60 mm', 'Afficheur : entraxe horizontal des trous du circuit'),
    ('aff_trou_ez', '21.5 mm', 'Afficheur : entraxe vertical des trous du circuit'),
    ('aff_bossage_d', '6.4 mm', 'Afficheur : bossages d inserts (limités par le corps de l afficheur)'),
    ('aff_bossage_h', 'aff_prof - platine_ep - aff_saillie', 'Afficheur : hauteur des bossages'),
    # Plaquettes vissées
    ('plaq_L', '40 mm', 'Plaquette : largeur'),
    ('plaq_H', '10 mm', 'Plaquette : hauteur'),
    ('plaq_ep', '2.5 mm', 'Plaquette : épaisseur'),
    ('plaq_R', '1.5 mm', 'Plaquette : rayon des coins'),
    ('plaq_vis_e', '32 mm', 'Plaquette : entraxe des deux vis FHC M3x8'),
    ('plaq_jauge_dz', '30.5 mm', 'Plaquettes SESSION / SEMAINE : sous l axe de la jauge'),
    ('plaq_aff_dz', '17 mm', 'Plaquette RÉINIT. : sous le centre de l afficheur'),
    ('plaq_bossage_d', '8 mm', 'Plaquette : bossages d inserts au dos de la platine'),
    ('plaq_bossage_h', '3 mm', 'Plaquette : hauteur des bossages'),
]


def is_corner_edge(e, L, H):
    g = e.geometry
    if not isinstance(g, adsk.core.Line3D):
        return False
    a, b = e.startVertex.geometry, e.endVertex.geometry
    if abs(a.x - b.x) > 1e-4 or abs(a.z - b.z) > 1e-4:
        return False
    return abs(abs(a.x) - L / 2) < 1e-3 and abs(abs(a.z) - H / 2) < 1e-3


def bosses(comp, body, name, plane, pts_fn, d_e, h_e, depth_e):
    """Bossages d'inserts : cercles sur le plan du sommet, extrudés vers la
    platine (1 mm de recouvrement), puis logement d'insert + passage."""
    sk = sketch(comp, plane, name)
    pts = pts_fn(sk)
    circles_at(sk, pts, d_e)
    coll = adsk.core.ObjectCollection.create()
    for p in profiles(sk):
        coll.add(p)
    extrude(comp, coll, JOIN, h_e + ' + 1 mm', toward_front(comp), name, [body])
    hole(comp, pts, 'lamage', 'vis_d', depth_e, False, name + '_inserts', [body],
         cb_d='insert_d', cb_p='insert_p')


def run(ctx):
    d = design()
    set_params(PARAMS)
    occ = new_component('platine')
    comp = occ.component
    occ.activate()
    xz = comp.xZConstructionPlane

    sk = sketch(comp, xz, 'platine_contour')
    centered_rect(sk, 'platine_L', 'platine_H')
    body = extrude(comp, sk.profiles.item(0), NEW, 'platine_ep', toward_front(comp), 'platine').bodies.item(0)
    body.name = 'platine'
    fillet(comp, [e for e in body.edges if is_corner_edge(e, ev('platine_L'), ev('platine_H'))],
           'platine_R', 'platine_coins')

    # Bossages des jauges (un jeu par jauge, une esquisse chacun).
    pl_j = plane_y(comp, 'jauge_bossage_h', 'plan_bossages_jauges')
    for side, sx in (('droite', 1), ('gauche', -1)):
        def pts_fn(sk, sx=sx):
            c, cx, cz = point(sk, 'jauge_x', 'jauge_z', sx=sx)
            return four_points(sk, c, cx, cz, 'jauge_vis_e / 2', 'jauge_vis_e / 2')
        bosses(comp, body, 'bossages_jauge_' + side, pl_j, pts_fn, 'jauge_bossage_d', 'jauge_bossage_h',
               'jauge_bossage_h + platine_ep')

    # Bossages de l'afficheur.
    pl_a = plane_y(comp, 'aff_bossage_h', 'plan_bossages_afficheur')
    def pts_aff(sk):
        c, cx, cz = point(sk, 'aff_x + aff_pcb_dx', 'aff_z')
        return four_points(sk, c, cx, cz, 'aff_trou_ex / 2', 'aff_trou_ez / 2')
    bosses(comp, body, 'bossages_afficheur', pl_a, pts_aff, 'aff_bossage_d', 'aff_bossage_h',
           'aff_bossage_h + platine_ep - 0.8 mm')

    # Bossages des plaquettes.
    pl_p = plane_y(comp, 'plaq_bossage_h', 'plan_bossages_plaquettes')
    jx, pz = ev('jauge_x'), ev('plaq_jauge_dz - jauge_z')
    ax, az = ev('aff_x'), ev('plaq_aff_dz - aff_z')
    e2 = ev('plaq_vis_e / 2')
    plaq = {
        'session': (-jx + e2, -jx - e2, -pz, 'jauge_x - plaq_vis_e / 2', 'jauge_x + plaq_vis_e / 2',
                    'plaq_jauge_dz - jauge_z'),
        'semaine': (jx + e2, jx - e2, -pz, 'jauge_x + plaq_vis_e / 2', 'jauge_x - plaq_vis_e / 2',
                    'plaq_jauge_dz - jauge_z'),
        'reinit': (ax + e2, ax - e2, -az, 'aff_x + plaq_vis_e / 2', 'plaq_vis_e / 2 - aff_x',
                   'plaq_aff_dz - aff_z'),
    }
    for name, a in plaq.items():
        bosses(comp, body, 'bossages_plaquette_' + name, pl_p, lambda sk, a=a: pair_points(sk, *a),
               'plaq_bossage_d', 'plaq_bossage_h', 'plaq_bossage_h + platine_ep')

    # Passages des corps de jauges et fenêtre de l'afficheur, depuis la face avant
    # (recoupe aussi les bossages des jauges).
    pl_f = plane_y(comp, '-platine_ep', 'plan_face_platine')
    sk = sketch(comp, pl_f, 'passages')
    cr, xr, zr = point(sk, 'jauge_x', 'jauge_z')
    cl = sk.sketchPoints.add(spt(sk, -xr, zr))
    sk.sketchDimensions.addDistanceDimension(sk.originPoint, cl, HOR, spt(sk, -xr / 2, zr + 0.3)).parameter.expression = 'jauge_x'
    sk.geometricConstraints.addHorizontalPoints(cr, cl)
    circles_at(sk, [cr, cl], 'jauge_trou_d')
    fw, fh = ev('aff_fen_L'), ev('aff_fen_H')
    rect(sk, 'aff_fen_L', 'aff_fen_H', 'aff_fen_L / 2 - aff_x', 'aff_z - aff_fen_H / 2', sx=-1, sz=-1,
         cx=ev('aff_x'), cz=ev('aff_z'))
    coll = adsk.core.ObjectCollection.create()
    for p in profiles(sk):
        coll.add(p)
    extrude(comp, coll, CUT, 'platine_ep + jauge_bossage_h + 2 mm', toward_wall(comp), 'passages', [body])

    # Vis de platine FHC M3 fraisées, dans les inserts de la coque.
    sk = sketch(comp, pl_f, 'vis_platine')
    pts = four_points(sk, sk.originPoint, 0, 0, 'vis_x', 'vis_z')
    hole(comp, pts, 'fraise', 'vis_d', 'platine_ep', True, 'vis_platine', [body], csk_d='fraise_d')

    d.activateRootComponent()
    mn, mx = bbox_mm(body)
    print('bodies', comp.bRepBodies.count, 'bbox', mn, mx, 'vol cm3', round(body.volume, 1))
    print('aff_bossage_h', round(ev('aff_bossage_h') * 10, 2), 'unhealthy', unhealthy())
