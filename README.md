# Nerv : Crisis

Un jeu d'arcade spatial en Python/Pygame : protegez la base, detruisez les
ennemis et survivez aux vagues de difficulte croissante.

## Installation et lancement

Python 3.12 recommande.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Sous Windows, activez avec `.venv\Scripts\activate`.
Les ressources sont localisees par rapport au code : le lancement fonctionne
meme depuis un autre dossier. Une session graphique est necessaire pour jouer.
L'absence de peripherique audio n'empeche pas de jouer.

## Menu original

`main.py` conserve les images et la bande-son historiques, avec une interface
revue : titres pixel, textes lisibles avec accents, illustration sans deformation,
boutons New Game / Load / Lab / Quit et panneaux harmonises.
L’introduction dure trois secondes et se passe avec Entree, Espace ou un clic.
Cliquez sur **New Game**, puis choisissez **Shooter** pour ouvrir le jeu ameliore.
Le menu se pilote avec la souris ou les fleches et Entree.
Lab propose le volume musical (curseur a la souris ou fleches gauche/droite)
et les commandes.
M met la musique en pause. Load indique que les sauvegardes sont indisponibles.
Le menu se redimensionne en conservant ses proportions, avec bandes noires
si necessaire. Les zones cliquables suivent la taille de la fenetre.
La musique du menu est mise en pause pendant le shooter, puis reprend a sa
fermeture sauf si vous l’aviez deja mise en pause.
F11 bascule le menu en plein ecran. Pour passer les animations de demarrage :
`python main.py --skip-intro`.

## Commandes du shooter

- Entree : commencer ou rejouer.
- Fleches, ZQSD ou WASD : deplacement.
- Espace maintenu : tir continu.
- P ou Echap : pause/reprise. La perte de focus met aussi le jeu en pause.
- M : couper/reactiver la musique.
- Echap depuis le menu ou la fin de partie : quitter.

Chaque ennemi detruit rapporte 100 points. Une collision ou un ennemi qui
franchit la base coute une vie, avec une courte protection apres les degats.
La difficulte augmente toutes les 20 secondes. Le record est conserve pendant
la session uniquement.

## Verification sans ecran

```sh
python -m unittest discover -s tests -v
```

Ces tests utilisent les pilotes SDL fictifs et verifient les collisions,
les controles, les transitions, la progression, les panneaux du menu, le volume
et les zones cliquables apres redimensionnement.
Ils ne valident pas l'affichage physique ni la sortie sonore.

## Licence

Tous droits reserves. Projet de CYZ. Voir LICENSE.

## Anciennes versions

Les sept versions historiques sont conservées dans [versions/](versions/README.md),
avec leurs ressources et la référence de leur commit original.
