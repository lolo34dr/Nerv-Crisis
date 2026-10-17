# Nerv : Crisis

An English-language arcade shooter built with Python and Pygame. Defend Tokyo-3
against enemy waves and Angels. The original Evangelion artwork, NERV logo,
pixel font, music and sound effects are retained.

## Install and launch

Python 3.12 is recommended.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

On Windows, activate with `.venv\Scripts\activate`.
A graphical session is required. Audio hardware is optional. Resources are
resolved relative to the source files, so launching from another directory works.

The game starts **fullscreen by default**, using the current display resolution.
**F11** switches between fullscreen and a resizable window. To start windowed:

```sh
python main.py --windowed
```

## Startup: logo splash and real loading

The original logo fades in and out on a black background. Enter, Space, Esc or a
click skips this animation. `--skip-intro` also skips the splash.

The subsequent loading screen prepares seven resource groups: profile, UI fonts,
original artwork, cached combat graphics, soundtrack, sound effects and terminal
background. Progress advances only after each operation finishes. There is no
artificial loading countdown; a fast machine may finish quickly. Even when the
splash is skipped, required resources must load before the menu can open.

A required resource failure leaves the loading bar incomplete. Press **R** to
retry or **Esc** to quit. Missing audio hardware is handled without blocking the
other resources. Combat reuses the loaded images and fonts instead of decoding
them again when a mission starts.

## Terminal and controls

- **New Game**: select Cadet, Normal or Expert, then launch the mission.
- **Load**: continue the saved mission, initially paused.
- **Lab**: music volume, playback and visual effects (**V**).
- **B**, or click the records area: view high scores and six achievements.
- **H**: open the pilot field guide, including movement, weapons and power-ups.
- Navigate with the mouse, arrow keys and Enter. Esc closes a panel.
- **M** pauses/resumes the music in both the terminal and combat.

The terminal, gameplay, pause screens and settings share one window and one
music player. Starting a mission never launches a second process or window.
The image keeps its aspect ratio; letterboxing and click coordinates adapt to
window size and fullscreen changes.

| Action | Keys |
| --- | --- |
| Move | Arrows, WASD or ZQSD |
| Continuous fire | Hold Space |
| Toggle auto-fire | F |
| Dash with brief protection | Shift (2.2 second cooldown) |
| AT Field pulse | C, when energy is full |
| Pause/resume | P or Esc |
| Help | H (pauses an active mission) |
| Music / fullscreen | M / F11 |

Losing window focus pauses combat. Closing help/settings keeps the mission
paused until you resume. The pause menu offers Resume, Settings, Save and menu,
and Back to menu. The mission-over screen shows kills, pickups, defeated Angels,
completed objectives, survival time, base health and your personal best.

## Waves, enemies and objectives

- **Scouts** are fast and fragile. **Zigzags** move in a sinusoidal pattern.
  **Gunners** have armor and aimed shots.
- An **Angel boss appears every five waves**, with a health bar, spread shots,
  and a faster second phase below half health.
- Clear the wave to advance. Each new wave repairs 5% of the base and restores
  10% energy; defeating an Angel repairs another 20%.
- A base breach costs 10% base health. Player impacts cost one life unless a
  shield or brief invulnerability absorbs them. Zero lives or base health ends
  the mission. Cadet starts with five lives; other difficulties start with three.
- Consecutive kills build a **combo up to x5**. Base kill scores are 100 / 180 /
  250 / 2,500 depending on the enemy type.
- Each wave has an additional objective: eliminate five targets, collect a
  power-up, clear without a base breach, or defeat the Angel. Completing it
  awards 300–1,000 points and 20% energy, once per wave. Objectives are optional:
  failing one does not stop wave progression. Complete three to unlock a badge.
- A capsule drops every five kills; Angels drop a heal. **+** restores one life
  (up to five), **S** adds a shield (up to two), **R** grants ten seconds of rapid
  fire, **T** grants ten seconds of triple shots, and **E** restores 40% energy.
- The AT Field pulse clears hostile projectiles and damages enemies. Kills also
  recharge its energy.

## Local saves and profile

Use **Pause > Save and menu**, then **Load** to resume. The save preserves the
player, wave, enemies, projectiles, power-ups, score, timers and objectives.
Decorative particles and the random sequence of future spawns are not saved.
Saves from the preceding release still load; their new objective counters start
at zero. There is one save slot. Saving replaces it; starting a fresh mission
keeps the existing slot. Closing the application records scores but does not
automatically save the current mission.

High scores by difficulty, achievements and settings live in `profile.json`:

- Linux: `$XDG_DATA_HOME/Nerv-Crisis`, or `~/.local/share/Nerv-Crisis`.
- Windows: `%LOCALAPPDATA%\Nerv-Crisis`.
- Override the folder with the `NERV_DATA_DIR` environment variable.

Writes are atomic. Invalid save data is rejected and write errors are displayed.
No player data is sent to an external service or written into the repository.

## Validation

```sh
python -m unittest discover -s tests -v
```

Tests use dummy SDL drivers and temporary profiles. They cover combat, bosses,
power-ups, objectives, pause/help, saves, previous-save compatibility, resizing,
fullscreen switching, asset caching, failed-loading retry and real loading
progress. They also verify that a mission creates no additional window, process
or music player. Physical fullscreen rendering and audible output should also
be checked on a desktop machine.

## Historical versions and license

The seven original snapshots, including their assets and commit references, are
in [versions/](versions/README.md). Later changes remain in the Git history.

All rights reserved. Project by CYZ. See LICENSE.
