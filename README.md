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

## Commandes

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
les controles, les transitions, la progression et le rendu des quatre ecrans.
Ils ne valident pas l'affichage physique ni la sortie sonore.

## Licence

Tous droits reserves. Projet de CYZ. Voir LICENSE.

## Anciennes versions

Les sept versions historiques sont conservées dans [versions/](versions/README.md),
avec leurs ressources et la référence de leur commit original.
