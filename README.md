# Nerv : Crisis

Un jeu d’arcade spatial en Python/Pygame. Défendez Tokyo-3 et survivez aux
vagues, dans une seule fenêtre du menu jusqu’à la fin de partie. L’illustration
Evangelion, le logo, la police pixel et la bande-son d’origine sont conservés.

## Installer et jouer

Python 3.12 recommandé.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Sous Windows, activez avec `.venv\Scripts\activate`.
Une session graphique est nécessaire pour jouer. Le jeu fonctionne sans
périphérique audio. Les ressources sont localisées par rapport au code :
le lancement fonctionne depuis un autre dossier.

## Menu et fenêtre

- **New Game** : choisir Cadet, Normal ou Expert, puis lancer la mission.
- **Load** : reprendre la dernière partie sauvegardée, en pause.
- **Lab** : volume, pause de la musique et particules activables avec **V**.
- **B** ou clic sur les records : consulter les records par difficulté et les cinq succès.
- Navigation : souris, flèches et Entrée. Échap ferme les panneaux.
- **M** : mettre la musique en pause/reprise, dans le menu comme en jeu.
- **F11** : plein écran. La fenêtre se redimensionne en gardant les proportions
  et les zones cliquables correctes.

L’introduction de trois secondes se passe avec Entrée, Espace ou un clic.
`python main.py --skip-intro` ouvre directement le terminal.
Le combat utilise la même fenêtre, le même affichage et la même piste musicale :
aucun sous-processus ni deuxième lecteur audio n’est lancé.

## Commandes en mission

| Action | Commande |
| --- | --- |
| Déplacer | Flèches, ZQSD ou WASD |
| Tir continu | Maintenir Espace |
| Tir automatique | F |
| Esquive rapide et courte protection | Maj / Shift (recharge 2,2 s) |
| Impulsion AT Field | C, quand l’énergie atteint 100 % |
| Pause / reprise | P ou Échap |
| Musique / plein écran | M / F11 |

Le jeu se met en pause à la perte de focus. Le menu pause permet de reprendre,
de changer les réglages, de **sauvegarder et revenir au menu**, ou de revenir au
menu sans sauvegarder la partie. La fin de partie propose de rejouer ou de
revenir au menu. Ces écrans se pilotent aussi à la souris.

## Combat et progression

- **Éclaireurs** : rapides, fragiles ; **zigzags** : trajectoires sinusoïdales ;
  **canonniers** : résistants, tirs dirigés vers le joueur.
- Un **boss Ange toutes les cinq vagues**, avec barre de vie, tirs en éventail
  et une seconde phase plus agressive à mi-vie.
- Détruisez tous les ennemis d’une vague pour progresser. Chaque nouvelle vague
  répare 5 % de la base et recharge 10 % d’énergie. Un boss détruit répare 20 %.
- Les ennemis qui franchissent la base lui retirent 10 %. Les impacts du joueur
  coûtent une vie, sauf protection temporaire ou bouclier. Une base détruite ou
  zéro vie termine la mission. Cadet commence avec cinq vies, les autres modes
  avec trois ; les soins peuvent monter à cinq.
- Les éliminations rapprochées montent un **combo jusqu’à x5**. Les points de
  base sont 100 / 180 / 250 / 2 500 selon le type d’ennemi.
- Une capsule tombe toutes les cinq éliminations ; les boss lâchent un soin.
  **+** : vie, **S** : bouclier (maximum deux), **R** : tir rapide pendant 10 s,
  **T** : triple tir pendant 10 s, **E** : +40 % d’énergie.
- L’impulsion AT Field efface les projectiles adverses et inflige des dégâts
  aux ennemis. Les éliminations rechargent aussi son énergie.

## Sauvegardes et progression locale

Un emplacement de sauvegarde conserve le combat : position, vague, ennemis,
projectiles, bonus, score et temporisations. Les effets décoratifs et la suite
aléatoire des futures apparitions ne sont pas conservés. **Load** restaure la
partie en pause. Une nouvelle sauvegarde remplace la précédente ; une nouvelle
partie ne l’efface pas. Fermer la fenêtre ne sauvegarde pas automatiquement
la mission : utilisez **Pause → Sauvegarder et menu**.

Les records par difficulté, succès et réglages sont stockés dans `profile.json` :

- Linux : `$XDG_DATA_HOME/Nerv-Crisis`, sinon `~/.local/share/Nerv-Crisis`.
- Windows : `%LOCALAPPDATA%\Nerv-Crisis`.
- Pour choisir un autre dossier : variable `NERV_DATA_DIR`.

Les écritures sont atomiques. Les données invalides sont refusées et les erreurs
d’écriture sont signalées dans le jeu. Aucune donnée personnelle n’est envoyée
à un service externe. Les fichiers du jeu et les anciennes versions restent
séparés des données du joueur.

## Vérifications

```sh
python -m unittest discover -s tests -v
```

Les tests utilisent les pilotes SDL sans écran et des profils temporaires.
Ils couvrent le combat, les bonus, les boss, la pause, le retour au menu, les
réglages, les zones cliquables après redimensionnement, les sauvegardes et leur
restauration. Ils vérifient aussi qu’une mission ne crée ni fenêtre ni processus
supplémentaire. L’affichage physique et le son réel restent à tester sur une
machine avec écran et haut-parleurs.

## Anciennes versions et licence

Les sept versions historiques sont conservées dans [versions/](versions/README.md),
avec leurs ressources et leur commit d’origine. Les améliorations suivantes
restent également accessibles dans l’historique Git.

Tous droits réservés. Projet de CYZ. Voir LICENSE.
