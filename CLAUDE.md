# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project
Interactive learning webapp that teaches students risk management (risicomanagement). Part of the PXL Hogeschool "Projectmanagement" course series, next to AgileForNigel, TeachBertPERT, TijdVoorKwaliteit and PMTheBasics.

## Source materials (in `source/` folder)
- `source/006 Risicomanagement.md` — the lesson content and structure (copied from `pxl-projectmanagement/docs/`)
- `source/009-risicomanagement.md` — the slides (generated from the PowerPoint, with speaker notes). Slide 4's notes hold the core case: a cyclist at a crossing, "Haal ik het?" (kans), "Wat kan er gebeuren?" (gevolg), "Wat als de auto een trein is?"
- `source/2025_10_huisstijlhandboek.pdf` — PXL corporate identity / huisstijlhandboek
- `source/1314_logo_pxl_bol_witrand.png` — original PXL logo (high-res)

## Requirements
- Single-page scroll layout (all sections on one page, nav links are anchor scrolls)
- Clean, modern design
- Max-width: 1100px (optimized for 1920x1080 student screens)
- Games in **vanilla JavaScript** on a `<canvas>`, no libraries, no image files (all pixel art is drawn in code)

## Hosting — GitHub Pages
The site is published via GitHub Actions to GitHub Pages.

- **Workflow**: `.github/workflows/deploy.yml` — triggers on every push to `main`
- **Source setting**: GitHub Pages → Source must be set to **GitHub Actions** (in repo Settings → Pages)
- No build step — the entire repo root is uploaded as the Pages artifact
- `index.html` only redirects to `risico.html`, so the root URL works too
- **Gotcha:** Pushing workflow files requires the `workflow` OAuth scope. If rejected, add the file via GitHub web UI instead.

## Styling — PXL Hogeschool huisstijl
Same design tokens, typography, nav (hamburger + scroll spy), footer, badges, callouts, progress bar and summary card as the sibling repos (see `../AgileForNigel/CLAUDE.md`).

**Extra tokens on this page:** `--c-kans` (blue) = Kans, `--c-gevolg` (orange-brown) = Gevolg, `--c-risico` (black) = Risico; reused on cards, scales, sliders, matrix axes and formulas. Risk zones (`RISK_ZONES`, score = kans × gevolg on 1-5 scales): laag 1-4 (green), middel 5-9 (gold), hoog 10-16 (orange), kritiek 20-25 (red), each with `--z-<zone>`, `--z-<zone>-bg`, `--z-<zone>-ink`, applied via `[data-zone]`.

**Arcade look:** the game frame is black with a gold border; HUD, overlays and toasts use the Google Font **Press Start 2P** (`--arcade`). Page text stays Raleway/Arial.

## Language
All page content is in **Dutch** (Nederlands).
Do NOT use em dashes (—, `&mdash;`, `—`) in any user-visible text. Use periods, colons, commas, or parentheses instead.
Nico is the recurring character; avoid gendered pronouns for Nico (write "Nico").

## Architecture
Single-file HTML page (`risico.html`) with inline `<style>` and `<script>` — no build step, no framework.

**Game engine (shared):** a Frogger-style engine, `FrogGame(root, opts)`, used by every game on the page. Canvas 416x288 (13x9 tiles of 32px; pixel art in units of 2px, `FP`), scaled with `image-rendering: pixelated`.
- Sprites are drawn in code with `frogPainter` (`r` rect, `line` Bresenham, `mask` text pattern) into offscreen canvases. Nico (`NICO_TOP` + `NICO_LEGS_A/B`, seen from behind on a bike, gold helmet). Road users in `FROG_KINDS` (wandelaar, jogger, kar, fietser, brommer, auto, vrachtwagen, trein), each with random color variants and a flipped copy for leftward lanes.
- A level config has 9 `rows` (row 0 = `goal`, row 8 = `start`), surfaces (`grass`, `path`, `cobble`, `plein`, `road`, `bike`, `rail`, `ballast`, `berm`), plus optional `crossRoad`, `signals`, `barriers` (level crossing) and `tunnel` (L4). Background is pre-rendered by `frogDrawBg`.
- Lanes: `frogLaneInit/Update/Hit`. Spacing via `gap` (tiles) or `period` (seconds). Train lanes use a schedule (`train`, `every`, `warn`, `first`) with warning lights and barriers.
- Rules: 5 hearts, a hit costs `cfg.g` hearts (= gevolg), Frogger reset to start; `need` crossings to win. An attempt starts when Nico leaves the start row. Stats: attempts, hits, damage, time, tunnel. `opts.onEnd(result)` after win or game over.
- Controls: arrows/WASD (only while the game element has focus), swipe on the canvas, D-pad on `pointer: coarse`, M toggles music. The rAF loop only runs while the game is visible.

**Sound (`FrogAudio`):** everything is synthesized with the Web Audio API, no audio files. The AudioContext is created on the first user gesture (`start()` or a sound button), because of browser autoplay rules.
- Music: an original 8-bar chiptune loop (`FROG_TUNE`: 25% pulse-wave lead, triangle bass, noise hi-hat, sine kick), scheduled with a 25 ms lookahead timer. Tempo per level (`tempo`: park 112, markt 150, overweg 124, steenweg 160; sandbox 116 + 8 × kans). Only one game owns the music (`FrogAudio.owner`). It plays only while that game is active and visible, and stops on game over, win, level change or a hidden tab.
- Effects (`FrogAudio.play`): hop, start, cross, hit (heavier and lower for a higher gevolg), win, over, bell (every 0.42 s while the level-crossing lights blink), horn (when a scheduled train arrives), tunnel.
- Two HUD buttons per game (`[data-snd="music"|"sfx"]`, `aria-pressed`) switch music and effects for all games. The choice is saved in `localStorage` (`nico-risico-audio-v1`, try/catch). Do not reproduce existing game music; keep the tune original.

**Current sections in `risico.html`:**
- `#kans-gevolg` — Risico = Kans × Gevolg. Intro with Nico's portrait (drawn from the sprite), three formula cards (Kans "Haal ik het?", Gevolg "Wat kan er gebeuren?", Risico) and the zone legend, then:
  1. `#frog-levels` (prefix `frog-`): four levels in `FROG_LEVELS`, one per quadrant: Het park (K1 G1), Marktdag (K5 G1), De overweg (K1 G5, trains with lights and barriers), De steenweg (K5 G5, with a fietstunnel = vermijden). Tabs, the game `#frog-main`, and an analysis panel `#frog-analysis` that appears after a level ends: stats, then the student rates kans and gevolg (1-5, `RISK_K`/`RISK_G`). Within ±1 of the level's values = good; otherwise level hints (`hintK`/`hintG`), revealed after the second try. Reveal shows the formula, zone, explanation and an IT-project example (`it`). Markers are added to the risk matrix (`riskMatrixHtml`). Summary when all four are analysed (same score 5 for markt and overweg, measures: preventie/repressie/vermijden/aanvaarden).
  2. `#frog-wat-als` (prefix `sb-`, `sim-`): "Wat als de auto een trein is?" Sliders for kans and gevolg drive a playable sandbox (`frogSandboxCfg`): gevolg picks the road user (wandelaar, fietser, brommer, auto, trein), kans sets how busy it is: number of lanes (`SB_LAYOUT`, 2 to 7 lanes; kans 5 = 7 lanes with no safe strip), speed (`SB_SPEED`, 0.8x to 1.5x, varied per lane with `SB_VARY` so gaps never line up) and density (`SB_OCC`, gaps between 0.6x and 1.25x of the mean so there are no long holes). Slow road users are easier to dodge, so at high kans their stream is denser (`SB_GF`, weighted per kans by `SB_GW`); that keeps the difficulty about the same for every gevolg. Nico's hitbox is `FROG_HIT_L/R` (5..27 px of the tile, shared with the levels).
     **Tuning targets (keep these when retuning):** the user found the earlier versions too easy at kans 5 twice. Measure with an attentive bot that has perfect information (looks 0.4 s ahead, may step sideways or back, decides every 0.15 s): it must still be hit in roughly 50-75% of crossings at kans 5 for every gevolg (current: 54-76%), and close to 0% at kans 1-3. Real players do worse than that bot.
     "Laat Nico 100 keer onvoorzichtig oversteken" runs `frogSimulate` headless: a careless Nico glances 0.1 s ahead at the next lane (`SIM_LOOK`), goes anyway after 1 s of waiting (`SIM_PATIENCE`), no sidesteps. Measured hit rates ≈ 2/15/35/73/98% for kans 1-5, about the same for every gevolg. It shows 100 dots, measured kans × gevolg = average hearts lost per crossing, plus a history table of the last runs.

## Development
No build commands. Open `risico.html` directly in a browser, or start the `risico` preview from `.claude/launch.json` (`python -m http.server 8765`). The deploy workflow uploads the entire repo root as a static site.
