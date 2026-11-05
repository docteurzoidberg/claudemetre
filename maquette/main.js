// Maquette 3D du Claudemètre : modèle claudometre.glb (voir pack.py), assemblé ou éclaté.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

// Dans l'ordre de la liste, du fond vers la façade.
const GROUPES = {
  coque: ["Coque", "PETG kaki, 200 × 96 × 40 mm, imprimée sur le dos. 12 inserts laiton."],
  clips: ["Clips", "PETG noir : 3 clips collés dans le fond tiennent la carte, sans vis."],
  carte: ["Carte", "Carte à borniers MRD076A et ESP32-S3 N16R8."],
  afficheur: ["Afficheur", "TM1637 0,56″ jaune : heure de réinitialisation de la session. 4 CHC M3×6."],
  temoin: ["Témoin", "Légende éclairée par 4 WS2812B : ambre quand un agent travaille, rouge quand il attend une réponse."],
  platine: ["Platine", "PETG noir, 188 × 90 × 3 mm, 4 FHC M3×12 et 18 inserts laiton."],
  jauges: ["Jauges", "Voltmètres SO-45, 8 CHC M3×12. Aiguilles, vitres et équipage mobile sont ajoutés pour le rendu."],
  cadrans: ["Cadrans", "Imprimés en multi-filament : « % · 5 H » pour la session, « % · 7 J » pour la semaine."],
  plaquettes: ["Plaquettes", "PLA noir, texte PLA blanc, 40 × 8 × 1,8 mm, 6 FHC M3×12."],
  visiere: ["Visière", "PETG kaki, collée dans une rainure."],
  plaques: ["Flancs", ""],
  connecteur: ["Connecteur", ""],
  fusible: ["Fusible", "Porte-fusible 5 × 20 à capuchon, qui protège l'arrivée 12 V. L'écrou se loge dans une empreinte de la plaque."],
};
const VISSERIE = ["Visserie", "36 vis M3 et 34 inserts laiton."];

// Plaque du flanc droit, au choix : chacune vient avec ses connecteurs. `sans` : groupes absents de cette plaque.
const CONNECTEUR = "4 FHC M3×12. Fiche et câble sont ajoutés pour le rendu.";
const PLAQUES = {
  pleine: {
    sans: ["connecteur", "fusible"],
    plaques: "Plaque pleine sur les deux flancs, 86 × 32 × 4 mm, 8 CHC M3×6.",
    visserie: "32 vis M3 et 30 inserts laiton.",
  },
  lp16: {
    sans: ["fusible"],
    plaques: "plaque_bossage à droite, plaque pleine à gauche, 86 × 32 × 4 mm, 8 CHC M3×6.",
    connecteur: `LP-16 2 pôles incliné de 30°, ${CONNECTEUR}`,
    visserie: VISSERIE[1],
  },
  fusible: {
    sans: [],
    plaques: "plaque_bossage_fusible à droite, plaque pleine à gauche, 86 × 32 × 4 mm, 8 CHC M3×6.",
    connecteur: `LP-16 2 pôles incliné de 45°, parallèle au fusible, ${CONNECTEUR}`,
    visserie: VISSERIE[1],
  },
};

const VUES = { iso: [1.2, 0.72, 0.72], face: [0, 0.02, 1], cote: [1, 0.18, 0.02], dos: [0.75, 0.45, -1] };

// Firmware (esphome/temoin.yaml) : respiration de 3,2 s en ambre, clignotement à 1 Hz en rouge.
const COULEURS = {
  ambre: new THREE.Color().setRGB(1, 0.56, 0.12, THREE.SRGBColorSpace),
  rouge: new THREE.Color().setRGB(1, 0.16, 0.08, THREE.SRGBColorSpace),
};
const niveauVoyant = {
  eteint: () => 0,
  ambre: (t) => (calme ? 0.8 : 0.675 + 0.325 * Math.cos((2 * Math.PI * t) / 3.2)),
  rouge: (t) => (calme || t % 1 < 0.5 ? 1 : 0),
};
const ECLAT_VOYANT = { ambre: 2.2, rouge: 1.4 };
const SURBRILLANCE = new THREE.Color(0x3d2f10);
const RETARD = 0.3;      // part de la course pendant laquelle les pièces du fond attendent celles de devant
const FOV = 26;
const MARGE = 0.94;      // part de l'image occupée par l'objet
const BAS_DU_CADRE = -60;

const $ = (id) => document.getElementById(id);
const calme = matchMedia("(prefers-reduced-motion: reduce)").matches;
const params = new URLSearchParams(location.search);
const zone = $("scene");
const canvas = $("vue");
const attente = $("attente");

const clamp01 = (v) => Math.min(Math.max(v, 0), 1);
const adoucit = (t) => t * t * (3 - 2 * t);

let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
} catch {
  attente.textContent = "Cette page a besoin de WebGL, qui n'est pas disponible dans ce navigateur.";
  throw new Error("WebGL indisponible");
}
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 0.9;

const scene = new THREE.Scene();
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.6;
scene.add(new THREE.HemisphereLight(0xffffff, 0x3a3d33, 0.8));
const cle = new THREE.DirectionalLight(0xffffff, 1.7);
cle.position.set(200, 240, 190);
const contre = new THREE.DirectionalLight(0xffffff, 0.8);
contre.position.set(-160, 80, -240);
scene.add(cle, contre);

const camera = new THREE.PerspectiveCamera(FOV, 1, 5, 8000);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.09;
controls.minDistance = 60;
controls.maxDistance = 3000;

let sale = true;          // l'image est à refaire
let pieces = [];
let cibles = [];          // maillages que le pointeur peut désigner
let voile = null;         // matériau de la légende, éclairé par le voyant
let halo = null;
let ouverture = 0;
let etatVoyant = "ambre";
let plaque = PLAQUES[params.get("plaque")] ? params.get("plaque") : "fusible";
const visibles = Object.fromEntries(Object.keys(GROUPES).map((g) => [g, true]));
let visserieVisible = true;

// --- animations

const tweens = new Map();
function anime(nom, duree, pas) {
  if (calme) {
    pas(1);
    sale = true;
    return;
  }
  tweens.set(nom, { debut: performance.now(), duree, pas });
}

// --- cadrage

const presentes = () => pieces.filter((p) => !p.option || p.option === plaque);

// Part d'une pièce sur sa course, pour une ouverture k.
const avance = (p, k) => adoucit(clamp01((k - p.retard) / (1 - p.retard)));

// Cible et distance pour que toutes les pièces tiennent dans l'image, pour un axe de vue et une ouverture.
function cadrage(axe, k) {
  const droite = new THREE.Vector3().crossVectors(camera.up, axe);
  if (droite.lengthSq() < 1e-6) droite.set(1, 0, 0);
  droite.normalize();
  const haut = new THREE.Vector3().crossVectors(axe, droite);
  const v = new THREE.Vector3();
  const points = presentes().flatMap((p) => {
    const f = avance(p, k);
    return p.coins.map((c) => {
      v.copy(p.sens).multiplyScalar(f).add(c);
      return [v.dot(droite), v.dot(haut), v.dot(axe)];
    });
  });
  const milieu = (i) => {
    const valeurs = points.map((q) => q[i]);
    return (Math.min(...valeurs) + Math.max(...valeurs)) / 2;
  };
  const [cx, cy, cz] = [milieu(0), milieu(1), milieu(2)];
  const tv = Math.tan(THREE.MathUtils.degToRad(FOV) / 2) * MARGE;
  const th = tv * camera.aspect;
  const recul = Math.max(...points.map(([x, y, z]) => z + Math.max(Math.abs(x - cx) / th, Math.abs(y - cy) / tv)));
  const cible = droite.multiplyScalar(cx).addScaledVector(haut, cy).addScaledVector(axe, cz);
  return { cible, distance: recul - cz };
}

// Suit un changement d'ouverture ou de format sans perdre le point de vue ni le zoom choisis.
function recadre(faitChanger) {
  const axe = camera.position.clone().sub(controls.target).normalize();
  const avant = cadrage(axe, faitChanger.avant);
  faitChanger.applique?.();
  const apres = cadrage(axe, ouverture);
  const distance = camera.position.distanceTo(controls.target) * (apres.distance / avant.distance);
  controls.target.add(apres.cible.sub(avant.cible));
  camera.position.copy(controls.target).addScaledVector(axe, distance);
}

function placeVue(nom, immediat) {
  const fin = new THREE.Vector3(...VUES[nom]).normalize();
  const axe = camera.position.clone().sub(controls.target);
  const d0 = axe.length();
  const debut = axe.normalize();
  const t0 = controls.target.clone();
  const pas = (u) => {
    const e = adoucit(u);
    const { cible, distance } = cadrage(fin, ouverture);
    controls.target.lerpVectors(t0, cible, e);
    const dir = debut.clone().lerp(fin, e).normalize();
    camera.position.copy(controls.target).addScaledVector(dir, THREE.MathUtils.lerp(d0, distance, e));
  };
  if (immediat) pas(1);
  else anime("vue", 700, pas);
  for (const b of $("vues").children) b.setAttribute("aria-pressed", String(b.dataset.vue === nom));
  sale = true;
}

// --- ouverture

function ouvre(k) {
  const avant = ouverture;
  ouverture = k;
  for (const p of pieces) p.objet.position.copy(p.offset).multiplyScalar(avance(p, k));
  recadre({ avant });
  $("ouverture").value = Math.round(k * 100);
  $("assemble").setAttribute("aria-pressed", String(k === 0));
  $("eclate").setAttribute("aria-pressed", String(k === 1));
  sale = true;
}

function ouvreVers(k, duree = 1400) {
  const depart = ouverture;
  anime("ouverture", duree * Math.max(Math.abs(k - depart), 0.25), (u) => ouvre(THREE.MathUtils.lerp(depart, k, u)));
}

// --- pièces

function appliqueVisibilite() {
  for (const p of pieces) p.objet.visible = (!p.option || p.option === plaque) && visibles[p.groupe] && (!p.vis || visserieVisible);
  cibles = pieces.filter((p) => p.objet.visible).flatMap((p) => p.maillages).filter((m) => m.material.name !== "verre");
  sale = true;
}

function choisisPlaque(nom) {
  const applique = () => {
    plaque = nom;
    appliqueVisibilite();
    for (const b of $("plaques").children) b.setAttribute("aria-pressed", String(b.dataset.plaque === nom));
    for (const l of $("liste").children) l.hidden = PLAQUES[nom].sans.includes(l.dataset.groupe);
  };
  if (pieces.length) recadre({ avant: ouverture, applique });
  else applique();
  if (PLAQUES[nom].sans.includes(epingle)) epingle = null;
  montreFiche();
}

let survole = null;       // groupe sous le pointeur ou dans la liste
let epingle = null;       // groupe choisi au toucher ou au clic

function montreFiche() {
  const g = survole ?? epingle;
  const [nom, detail] = g === "visserie" ? VISSERIE : (GROUPES[g] ?? ["Maquette", ficheParDefaut]);
  $("fiche-nom").textContent = nom;
  $("fiche-detail").textContent = PLAQUES[plaque][g] ?? detail;
  for (const l of $("liste").children) l.classList.toggle("marque", l.dataset.groupe === g);
  for (const p of pieces) {
    const allume = p.groupe === g || (g === "visserie" && p.vis);
    for (const m of p.materiaux) {
      if (m === voile) continue;
      m.emissive.copy(m.userData.emissive);
      if (allume) m.emissive.add(SURBRILLANCE);
    }
  }
  sale = true;
}
const ficheParDefaut = matchMedia("(hover: none)").matches
  ? "Glisser pour tourner, pincer pour zoomer. Toucher une pièce pour la nommer."
  : $("fiche-detail").textContent;

function designe(groupe) {
  if (groupe === survole) return;
  survole = groupe;
  montreFiche();
}

function ligne(groupe, nom, coche) {
  const l = document.createElement("label");
  l.className = "piece";
  l.dataset.groupe = groupe;
  const c = document.createElement("input");
  c.type = "checkbox";
  c.checked = true;
  c.addEventListener("change", () => coche(c.checked));
  const n = document.createElement("span");
  n.textContent = nom;
  l.append(c, n);
  l.addEventListener("pointerenter", () => designe(groupe));
  l.addEventListener("pointerleave", () => designe(null));
  c.addEventListener("focus", () => designe(groupe));
  c.addEventListener("blur", () => designe(null));
  return l;
}

function construitListe() {
  const liste = $("liste");
  for (const [g, [nom]] of Object.entries(GROUPES)) {
    liste.append(ligne(g, nom, (v) => {
      visibles[g] = v;
      appliqueVisibilite();
    }));
  }
  const l = ligne("visserie", VISSERIE[0], (v) => {
    visserieVisible = v;
    appliqueVisibilite();
  });
  l.classList.add("visserie");
  liste.append(l);
}

// --- pointeur

const rayon = new THREE.Raycaster();
const pointeur = new THREE.Vector2();
let aTester = false;
let appui = null;

function placePointeur(e) {
  const r = canvas.getBoundingClientRect();
  pointeur.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
}

function groupeSousPointeur() {
  rayon.setFromCamera(pointeur, camera);
  const hit = rayon.intersectObjects(cibles, false)[0];
  return hit ? hit.object.userData.groupe : null;
}

canvas.addEventListener("pointermove", (e) => {
  if (e.pointerType === "mouse" && !e.buttons) {
    placePointeur(e);
    aTester = true;
  }
});
canvas.addEventListener("pointerleave", () => {
  aTester = false;
  designe(null);
});
canvas.addEventListener("pointerdown", (e) => {
  appui = [e.clientX, e.clientY];
});
canvas.addEventListener("pointerup", (e) => {
  if (!appui || Math.hypot(e.clientX - appui[0], e.clientY - appui[1]) > 6) return;
  placePointeur(e);
  const g = groupeSousPointeur();
  epingle = g === epingle ? null : g;
  montreFiche();
});

// --- voyant

function majVoyant(temps) {
  if (!voile) return;
  const niveau = niveauVoyant[etatVoyant](temps);
  const couleur = COULEURS[etatVoyant] ?? COULEURS.ambre;
  voile.emissive.copy(couleur).multiplyScalar(niveau * (ECLAT_VOYANT[etatVoyant] ?? 0));
  halo.material.color.copy(couleur);
  halo.material.opacity = 0.34 * niveau;
  halo.visible = niveau > 0.01;
}

function creeHalo() {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  const d = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  d.addColorStop(0, "rgba(255,255,255,.75)");
  d.addColorStop(0.45, "rgba(255,255,255,.22)");
  d.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = d;
  g.fillRect(0, 0, 128, 128);
  const texture = new THREE.CanvasTexture(c);
  texture.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Sprite(new THREE.SpriteMaterial({
    map: texture, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
}

// --- chargement

function prepare(gltf) {
  const racine = gltf.scene;
  racine.rotation.x = -Math.PI / 2;    // repère de Fusion : Z en haut, façade vers -Y
  scene.add(racine);

  racine.traverse((o) => {
    if (!o.userData.offset) return;
    const p = {
      objet: o, nom: o.name, groupe: o.userData.groupe, vis: o.userData.vis,
      option: o.userData.option, offset: new THREE.Vector3(...o.userData.offset), maillages: [], materiaux: [],
    };
    o.traverse((m) => {
      if (!m.isMesh) return;
      m.material = m.material.clone();
      m.material.userData.emissive = m.material.emissive.clone();
      m.userData.groupe = p.groupe;
      p.materiaux.push(m.material);
      p.maillages.push(m);
    });
    pieces.push(p);
  });

  const loin = Math.max(...pieces.map((p) => p.offset.length()));
  for (const p of pieces) p.retard = RETARD * (1 - p.offset.length() / loin);

  // Coins des pièces pour le cadrage, dans le repère de la scène. Le câble sort du cadre par le bas.
  racine.updateMatrixWorld(true);
  for (const p of pieces) {
    const b = new THREE.Box3().setFromObject(p.objet);
    b.min.y = Math.max(b.min.y, BAS_DU_CADRE);
    b.max.y = Math.max(b.max.y, BAS_DU_CADRE);
    p.coins = [0, 1, 2, 3, 4, 5, 6, 7].map((i) => new THREE.Vector3(
      (i & 1 ? b.max : b.min).x, (i & 2 ? b.max : b.min).y, (i & 4 ? b.max : b.min).z,
    ));
    p.sens = new THREE.Vector3(p.offset.x, p.offset.z, -p.offset.y);
  }
  camera.position.set(0, 0, 1);

  const clair = new THREE.LineBasicMaterial({ color: 0x8d8877, transparent: true, opacity: 0.32 });
  const fonce = new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.4 });
  for (const p of pieces) {
    if (!p.objet.userData.aretes) continue;
    for (const m of p.maillages) {
      const c = m.material.color;
      const sombre = c.r + c.g + c.b < 0.2 || m.material.name === "verre";
      m.add(new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry, 28), sombre ? clair : fonce));
    }
  }

  const legende = pieces.find((p) => p.nom === "temoin_voile");
  voile = legende.materiaux[0];
  const boite = new THREE.Box3().setFromObject(legende.objet);
  const centre = legende.objet.worldToLocal(boite.getCenter(new THREE.Vector3()));
  halo = creeHalo();
  halo.position.copy(centre).add(new THREE.Vector3(0, -14, 0));
  halo.scale.set(92, 46, 1);
  legende.objet.add(halo);

  const version = gltf.asset.extras?.version;
  if (version) $("version").textContent = `claudometre, version ${version}`;

  choisisPlaque(plaque);
  majVoyant(0);
  placeVue(params.has("vue") && VUES[params.get("vue")] ? params.get("vue") : "iso", true);
  attente.hidden = true;

  // ?ouverture=40 ouvre directement à 40 % ; sinon l'objet s'ouvre tout seul au chargement.
  const demande = Number(params.get("ouverture"));
  if (params.has("ouverture")) ouvre(clamp01(demande / 100));
  else if (calme) ouvre(1);
  else {
    ouvre(0);
    setTimeout(() => ouvreVers(1, 2200), 500);
  }
}

// --- boucle : rien n'est dessiné tant que rien ne change

let image = 0;
function boucle(now) {
  requestAnimationFrame(boucle);
  if (!pieces.length) return;
  for (const [nom, t] of tweens) {
    const u = clamp01((now - t.debut) / t.duree);
    t.pas(u);
    if (u === 1) tweens.delete(nom);
    sale = true;
  }
  if (controls.update()) sale = true;
  if (aTester) {
    aTester = false;
    designe(groupeSousPointeur());
  }
  if (etatVoyant !== "eteint" && !calme && now - image > 33) {
    image = now;
    majVoyant(now / 1000);
    sale = true;
  }
  if (sale) {
    sale = false;
    renderer.render(scene, camera);
  }
}

new ResizeObserver(() => {
  const w = zone.clientWidth;
  const h = zone.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  const applique = () => {
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  if (pieces.length) recadre({ avant: ouverture, applique });
  else applique();
  sale = true;
}).observe(zone);

$("assemble").addEventListener("click", () => ouvreVers(0));
$("eclate").addEventListener("click", () => ouvreVers(1));
$("ouverture").addEventListener("input", (e) => {
  tweens.delete("ouverture");
  ouvre(e.target.valueAsNumber / 100);
});
for (const b of $("vues").children) b.addEventListener("click", () => placeVue(b.dataset.vue));
for (const b of $("plaques").children) b.addEventListener("click", () => choisisPlaque(b.dataset.plaque));
for (const b of $("voyants").children) {
  b.addEventListener("click", () => {
    etatVoyant = b.dataset.voyant;
    for (const o of $("voyants").children) o.setAttribute("aria-pressed", String(o === b));
    majVoyant(performance.now() / 1000);
    sale = true;
  });
}

construitListe();
requestAnimationFrame(boucle);

new GLTFLoader().load(
  "claudometre.glb",
  prepare,
  (e) => {
    attente.textContent = e.lengthComputable
      ? `Chargement du modèle… ${Math.round((e.loaded / e.total) * 100)} %`
      : `Chargement du modèle… ${(e.loaded / 1e6).toFixed(1).replace(".", ",")} Mo`;
  },
  (erreur) => {
    console.error(erreur);
    attente.textContent = "Le modèle n'a pas pu être chargé.";
  },
);
