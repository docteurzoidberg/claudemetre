# Carte à borniers MRD076A et ESP32-S3 : modèle 3D de référence

Carte d'adaptation à borniers à vis pour la diymore ESP32-S3-DevKitC-1 N16R8 :
l'ESP32 s'enfiche dessus, les fils se vissent, rien à souder sur l'ESP32.
Fiche Amazon : B0FKBLR2KF, variante « 2 pièces ESP32 S3 + carte d'extension ».
La sérigraphie porte `MRD076A FOR ESP32-S3 TERMINAL ADAPTER`.

Source : archive GrabCAD `mdr076a-esp32-s3-1.snapshot.1.zip` (le modèle y est
écrit MDR076A). Les fichiers SolidWorks de l'archive ne sont pas repris. Cotes
contrôlées sur les pièces reçues.

| Fichier | Contenu |
| --- | --- |
| `MDR076A+ESP32-S3.STEP` | carte à borniers avec l'ESP32 enfiché, 626 solides. Envoyé dans Fusion : `claudometre/models/mrd076a_esp32_s3` |
| `MDR076A.STEP` | carte à borniers seule, 211 solides |
| `MDR076A+ESP32-S3.jpg` | aperçu fourni avec le modèle |

## Cotes relevées dans Fusion

Repère du modèle, en mm : origine au milieu d'un petit bord, sur la face
arrière du circuit. X en largeur, Y en longueur, Z vers le dessus. L'USB-C de
l'ESP32 est du côté de y = 0, l'antenne du côté de y = 84,7.

| Élément | X | Y | Z |
| --- | --- | --- | --- |
| Circuit de la carte, 73,6 × 84,7 × 1,5 | ±36,8 | 0 à 84,7 | 0 à 1,5 |
| Borniers, 22 voies au pas de 3,5, entrée des fils vers le bord | ±22,33 à ±29,17 | 3,43 à 81,27 | -2,01 à 9,92 |
| Connecteurs femelles de l'ESP32, entraxe 25,4 | ±11,43 à ±13,97 | 14,37 à 70,29 | -1,72 à 10,02 |
| Connecteurs femelles extérieurs, inutilisés | ±17,83 à ±20,37 | 14,37 à 70,29 | -1,72 à 10,02 |
| Circuit de l'ESP32, 28 × 63,4 | ±14 | 13,76 à 77,18 | 14,2 à 15,2 |
| Sommet (USB-C ; module WROOM à 18,33) | | | 18,48 |
| **Encombrement total** | **73,6** | **84,7** | **-2,01 à 18,48, soit 20,5** |

La carte n'a pas de prise d'alimentation : le 5 V arrive sur le bornier `5V`.
Le jack de 6,5 à 9 V cité par la fiche concerne une autre carte d'extension.
