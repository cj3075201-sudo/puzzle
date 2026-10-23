# Audio credits — Once Under a Time, Chapter 1

Compiled 2026-10-22. **Every source below is CC0 1.0 (public domain dedication)**, and its license was checked on the source page at download time. No CC-BY, non-commercial or unclear-license material is used, so attribution is not legally required. It is listed here so the sources can be traced, and as a courtesy to the authors.

- CC0 1.0 legal text: https://creativecommons.org/publicdomain/zero/1.0/
- Freesound: the sounds were fetched as Freesound's high-quality OGG previews. The license applies to the sound itself, and each sound page shows "Creative Commons 0".
- Kenney packs: every pack contains a `License.txt` that reads "License (Creative Commons Zero, CC0)"; the pack page reads "Creative Commons CC0".
- OpenGameArt: the "License(s)" field on each page reads "CC0".

Shared processing for every SFX: mono 44.1 kHz; leading silence trimmed; short fade-in and fade-out; high-pass and low-pass clean-up. A lookahead peak limiter (3–7 dB) was used on sharp transients only. Each file was normalized toward −16 LUFS with a −1 dBFS peak ceiling, whichever is reached first. Very short transients (taps, steps, knocks) therefore stop at the peak ceiling, at roughly −20 to −25 LUFS. The ambient bed is set to −18 LUFS on purpose ("very soft"). Everything is encoded as Ogg Vorbis q6.

## Sound effects

| File | Source(s) | Author | License | Changes |
|---|---|---|---|---|
| `page.ogg` | Kenney *RPG Audio*: `bookFlip2.ogg`, `bookFlip3.ogg` — https://kenney.nl/assets/rpg-audio | Kenney (kenney.nl) | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) | Layered (flip3 tail at +0.30 s), HP 180 Hz / LP 9 kHz, 7 dB peak limit, 0.53 s |
| `piece.ogg` | Kenney *Impact Sounds*: `impactWood_light_000.ogg` — https://kenney.nl/assets/impact-sounds | Kenney | CC0 | Pitched up ×1.25 (smaller piece), cut to 0.11 s, HP 150 Hz |
| `drop.ogg` | Kenney *Impact Sounds* `impactWood_medium_000.ogg` + *RPG Audio* `bookPlace1.ogg` | Kenney | CC0 | Layers aligned at their peaks, LP 5 kHz, pre-transient trimmed, 0.26 s |
| `latch.ogg` | Kenney *RPG Audio*: `metalClick.ogg` (click-clack) + `metalLatch.ogg` | Kenney | CC0 | Layered, HP 300 Hz / LP 7 kHz (warmer, "brass"), 0.30 s |
| `confirm.ogg` | "Kalimba (C-note)" — https://freesound.org/people/foochie_foochie/sounds/331047/ | foochie_foochie | CC0 | One note re-pitched into a rising C5–E5–G5 arpeggio (110 ms apart), LP 6 kHz, 1.46 s |
| `almost.ogg` | same kalimba (331047) | foochie_foochie | CC0 | Two notes E5 → D5 (unresolved), LP 3.5 kHz (softer), 1.0 s |
| `wrong.ogg` | Kenney *Impact Sounds*: `impactWood_heavy_000.ogg`, `impactWood_heavy_001.ogg` | Kenney | CC0 | Two knocks pitched down (×0.82 / ×0.74), LP 900 Hz (muted), 0.55 s |
| `speak.ogg` | "Zanka Note D.wav" (pan flute) — https://freesound.org/people/PanPiper5/sounds/427080/ ; "Glass Bottle 3 - air" — https://freesound.org/people/astriferal/sounds/516169/ | PanPiper5; astriferal | CC0 | Flute note given a wobbling pitch contour (×1.3–1.6), 7 Hz tremolo, two "syllable" envelopes, plus a little bottle breath; no voice material, so it cannot sound like words. 0.62 s |
| `fish.ogg` | "Underwater_rumble_CsG.wav" — https://freesound.org/people/csaszi/sounds/336470/ ; "Big Water Splash" — https://freesound.org/people/qubodup/sounds/442773/ ; "Mud Splash" — https://freesound.org/people/adiantheman/sounds/841538/ | csaszi; qubodup; adiantheman | CC0 | Rumble (LP 400 Hz) with a swell envelope, plus a synthesized 48→34 Hz sub sweep; splashes pitched down (×0.6 / ×0.7) enter at 0.45 s; 3.4 s |
| `step_paper_1..3.ogg` | Kenney *Impact Sounds*: `footstep_concrete_000/001/002.ogg` + a 70 ms slice of *RPG Audio* `bookFlip2.ogg` (paper crinkle) | Kenney | CC0 | Pitched up slightly (×1.12/1.16/1.20, small bird), paper crinkle layered at −13 dB, ~0.1 s each |
| `rope.ogg` | "Rope Knots - Nudos Cuerda.wav" — https://freesound.org/people/Raulitoto/sounds/273530/ ; "ropes" — https://freesound.org/people/ssierra1202/sounds/391946/ ; Kenney *RPG Audio* `handleSmallLeather.ogg` | Raulitoto; ssierra1202; Kenney | CC0 | Knot tug, then a rope-slide pull, then the slack rope drops; 1.24 s |
| `cart.ogg` | "Foley_Elements_Wood_Small-Wooden-Wheeled-Cart-Rolling-On-Wooden-Surface" — https://freesound.org/people/Sonicquinn/sounds/518790/ | Sonicquinn | CC0 | 3.3 s continuous section (13.6–16.9 s), 5 dB limit, 0.3 s equal-power crossfade, so the result is a **seamless 3.00 s loop** |
| `splash.ogg` | qubodup 442773 + adiantheman 841538 (above) | qubodup; adiantheman | CC0 | Both pitched down (×0.78 / ×0.85) for a "thick" ink, LP 5.5 kHz, 1.6 s |
| `crowd_bow.ogg` | Kenney *RPG Audio* `cloth1-4.ogg`, `creak1-3.ogg` ; "Fabric Rustle and Shuffle" — https://freesound.org/people/khenshom/sounds/527698/ | Kenney; khenshom | CC0 | 14 cloth rustles scattered over 0–0.55 s with random pitch (×0.8–1.15), 4 quiet low-passed wooden creaks (puppet joints), a fabric-shuffle swell; 2.0 s |
| `curtain.ogg` | "Vorhang_Open_Close_Fast" (theatre curtain) — https://freesound.org/people/Maestro_Himself/sounds/715901/ | Maestro_Himself | CC0 | First draw only (3.2–7.4 s), HP 80 Hz, 0.15 s fade-in / 0.9 s fade-out, 4.2 s |
| `quill.ogg` | "Ink Quill Writing on Parchment ASMR" — https://freesound.org/people/brktkrgll/sounds/856167/ | brktkrgll | CC0 | 1.1 s section (1.4–2.5 s), HP 400 Hz / LP 11 kHz |

## Ambient

| File | Source(s) | Author | License | Changes |
|---|---|---|---|---|
| `ambient.ogg` | "INT Cave Room tone.wav" — https://freesound.org/people/deleted_user_2104797/sounds/164785/ ; "AMBLM wind interior howling stronger.wav" — https://freesound.org/people/LudwigMueller/sounds/202519/ ; "Water Dripping in Cave.wav" — https://freesound.org/people/Sclolex/sounds/177958/ | deleted Freesound user (account removed; the sound remains published under CC0); LudwigMueller; Sclolex | CC0 | Cave room tone LP 700 Hz (bed), wind LP 1.1 kHz at −12 dB under it, drips band-passed 350 Hz–5 kHz with a short synthetic cave echo at −14 dB; 8 dB limit; 4 s equal-power crossfade, so the result is a **seamless 90.0 s loop**, mono, −18 LUFS |

## Music

| File | Source | Author | License | Changes |
|---|---|---|---|---|
| `music_village.ogg` | "4 Music Box Tracks" → `musicbox3_sad_tune.ogg` — https://opengameart.org/content/4-music-box-tracks | Aureolus_Omicron | CC0 ("CC0. No credit required.") | Gain −0.7 dB only (−16 LUFS), re-encoded. The author ships it as a looping ogg (F minor, 80 bpm, music box); 2:36, stereo. No fades, so the loop stays intact |
| `music_title.ogg` | "First Light Particles – CC0 Atmospheric Piano/Ambient Track" — https://opengameart.org/content/first-light-particles-%E2%80%93-cc0-atmospheric-pianoambient-track | yoiyami | CC0 ("CC0 1.0 Universal (Public Domain)") | Gain +4.6 dB (−16 LUFS), 0.5 s fade-in; 2:12, stereo. The piece has a natural soft ending, so a loop gives a short breath |
| `music_ending.ogg` | "Awestruck" — https://opengameart.org/content/awestruck | isaiah658 | CC0 ("Credit … not required, but is appreciated") | Gain −0.7 dB only; 55 s, stereo. The author built it as a seamless loop, so no fades were added |

Suggested courtesy credit line for the game's credits screen: *Sound: Kenney (kenney.nl), Freesound users foochie_foochie, PanPiper5, astriferal, csaszi, qubodup, adiantheman, Raulitoto, ssierra1202, Sonicquinn, khenshom, Maestro_Himself, brktkrgll, LudwigMueller, Sclolex. Music: Aureolus_Omicron, yoiyami, isaiah658 (OpenGameArt). All CC0.*

---

# Pass 2 — new chapter-1 script 「내 자리 대신 가 줄래」 (2026-10-23)

29 new files, every one built from **CC0 1.0** sources (license re-checked on each Freesound page at download, the "Creative Commons 0" field), from Kenney packs (CC0), and from material synthesized in Python (numpy/scipy). No existing file was changed or overwritten. Processing and targets are the same as pass 1: mono 44.1 kHz for SFX; −16 LUFS with a −1 dBFS peak ceiling, whichever comes first (short taps stop at the ceiling, at −19 to −25 LUFS); ambience and crowd beds −18 LUFS, stereo; music −16 LUFS, stereo. Everything is Ogg Vorbis q6. Loops were rendered "circularly": events and reverb tails that run past the end are folded back onto the start, and filters and limiters run as if already looping, so the seam has no click or gap. The ambience beds also get a 4 s equal-power crossfade.

**Synthesized parts** (my own, no third-party material, also CC0): the sub-bass sweeps in `fish_rise`, `fish_gulp`, `fish_sink`; the resonant bubble "bloops" in `fish_sink`; the mouth-air noise in `fish_open` and the air puff in `fish_spit`; the low music-box tines, the mechanism hiss and the ticks in `musicbox*`; the warm pad in `music_hideout`; the low "tree hollow" body noise in `amb_hideout`; and the convolution reverb on every file (decaying filtered noise impulse responses).

**Music is original.** `music_village2`, `music_hideout`, `music_truth`, `music_procession` and the `musicbox` tune were composed for this game (2026-10-23) and rendered note by note from the single-note CC0 samples listed below, with a small Python sampler. The hideout tune (`musicbox`) is the shared motif. `music_hideout` is an arrangement of it, and `music_truth` quotes its first three notes and then breaks off on a wrong note.

## New Freesound sources (all CC0)

| Short name | Sound | Author | Page |
|---|---|---|---|
| bubbles | Bubbles In Water | calebrankin | https://freesound.org/people/calebrankin/sounds/529383/ |
| mudbubble | Hot Bubbling Mud | Breviceps | https://freesound.org/people/Breviceps/sounds/456806/ |
| gulp | Gulp - Hard Swallow | magnuswaker | https://freesound.org/people/magnuswaker/sounds/531755/ |
| monsterspit | gross monster spitting / belching effect 01 | rubberduck9999 | https://freesound.org/people/rubberduck9999/sounds/676316/ |
| slowcreaks | Slow wooden creaks x5 | peridactyloptrix | https://freesound.org/people/peridactyloptrix/sounds/218163/ |
| woodcreaking | Wood Creaking.wav | laft2k | https://freesound.org/people/laft2k/sounds/397620/ |
| tollbell | TollBell.wav | daytripper | https://freesound.org/people/daytripper/sounds/73678/ |
| bagrustle | Bag rustle.wav | Eyewer | https://freesound.org/people/Eyewer/sounds/435769/ |
| invopen | Inventory Open | Fission9 | https://freesound.org/people/Fission9/sounds/568992/ |
| plankscrape | Wood Plank Scraping Close-Mic Long.aif | RutgerMuller | https://freesound.org/people/RutgerMuller/sounds/104013/ |
| woodstonescrape | SFX_wood_stone_floor_scraping_pile_01.wav | EricsSoundschmiede | https://freesound.org/people/EricsSoundschmiede/sounds/669466/ |
| largewagon | R23-67-Large Wagon.wav | craigsmith | https://freesound.org/people/craigsmith/sounds/480039/ |
| buckboard | G52-16-Buckboard Creaking.wav | craigsmith | https://freesound.org/people/craigsmith/sounds/437085/ |
| filing | filing.wav | aerror | https://freesound.org/people/aerror/sounds/328763/ |
| woodsqueak | Wood-squeak.m4a | jmarcosfer | https://freesound.org/people/jmarcosfer/sounds/520914/ |
| spintop | SpinningTop.wav | gazbooth | https://freesound.org/people/gazbooth/sounds/634288/ |
| woodblock | Woodblock-soft.wav | hollandm | https://freesound.org/people/hollandm/sounds/692828/ |
| framedrum | Frame drum_oneshot_RAW_13.wav | cabled_mess | https://freesound.org/people/cabled_mess/sounds/345636/ |
| alfaia | Alfaia Hit | Sassaby | https://freesound.org/people/Sassaby/sounds/509528/ |
| bigkick | Big Kick Drum | TheEndOfACycle | https://freesound.org/people/TheEndOfACycle/sounds/673508/ |
| duduk | duduk C3 (sounds C4) | blood_of_a_pomegranate | https://freesound.org/people/blood_of_a_pomegranate/sounds/479213/ |
| wineglass | Wine Glass Sustained Note F#6 | spectral9 | https://freesound.org/people/spectral9/sounds/256251/ |
| marimba | Marimba - F#5 (VSCO 2 CE) | sgossner | https://freesound.org/people/sgossner/sounds/373586/ |
| bassoon | Bassoon - sustain - F#3 (VSCO 2 CE) | sgossner | https://freesound.org/people/sgossner/sounds/372688/ |
| cellopizz | Cello Section - tight pizzicato - F#2 (VSCO 2 CE) | sgossner | https://freesound.org/people/sgossner/sounds/372760/ |
| cellotrem | Cello Section - tremolo - F#4 (VSCO 2 CE) | sgossner | https://freesound.org/people/sgossner/sounds/372865/ |
| cbassvib | Solo Contrabass - vibrato sustain - F#1 (VSCO 2 CE) | sgossner | https://freesound.org/people/sgossner/sounds/373153/ |
| timpani | Timpani - F3 (VSCO 2 CE) | sgossner | https://freesound.org/people/sgossner/sounds/373936/ |
| windwindow | wind blowing through window with little traffic noise | MeanRaccoon | https://freesound.org/people/MeanRaccoon/sounds/844779/ |
| windwhistle | Wind whistle 3 | Sadiquecat | https://freesound.org/people/Sadiquecat/sounds/770282/ |
| hammerdistant | hammering distant metal wood mono.wav | cognito perceptum | https://freesound.org/people/cognito%20perceptu/sounds/85239/ |
| mbnote | Music box note | thomasjaunism | https://freesound.org/people/thomasjaunism/sounds/218459/ |
| flutetrem | flute_note_tremolo.wav | hellska | https://freesound.org/people/hellska/sounds/328727/ |

Reused from pass 1 (already credited above): kalimba (foochie_foochie), Zanka pan flute (PanPiper5), underwater rumble (csaszi), big splash (qubodup), mud splash (adiantheman), cave drips (Sclolex), cave room tone (deleted user), interior wind (LudwigMueller), curtain (Maestro_Himself), cart (Sonicquinn). Kenney packs used: *Impact Sounds* (`impactWood_light_000-004`, `impactWood_heavy_000/001`, `impactPlank_medium_001/002`, `impactSoft_heavy_000`, `impactMetal_light_000`, `footstep_wood_000-004`) and *RPG Audio* (`creak1-3`, `cloth1-4`, `doorOpen_2`, `dropLeather`, `bookPlace1`, `drawKnife1`).

VSCO 2 Community Edition (Versilian Studios) is a CC0 sample library; sgossner uploaded its one-shots to Freesound under CC0. The pitch in its Freesound titles is one semitone below the true pitch. Every sample was re-measured before use, for example the bassoon "F#3" sounds G3.

## Files

| File | Built from | Changes |
|---|---|---|
| `fish_rise.ogg` | csaszi rumble, Breviceps mud bubbling, calebrankin bubbles, qubodup splash (forward + reversed), adiantheman mud splash, Sclolex drips + synth sub | 4.6 s. Rumble and bubbling grow for 2.6 s (sub sweep 30→52 Hz). A reversed splash sucks the water up, then the head breaks the surface **at 2.6 s** (splashes pitched ×0.55/×0.65), then water runs off. Cave reverb 2.2 s |
| `fish_open.ogg` | peridactyloptrix slow creak (8.3–9.4 s), Kenney `doorOpen_2`, adiantheman mud splash + synth air | Creak pitched ×0.55 (huge jaw hinge), door creak ×0.5 under it, wet lips parting at the start, hollow mouth air (band 140–520 Hz) swelling; 2.3 s |
| `fish_gulp.ogg` | Kenney `impactPlank_medium_001`, `impactSoft_heavy_000`; magnuswaker gulp; adiantheman mud splash + synth sub | Jaw shuts (plank ×0.55 + soft thud), slosh, then the swallow pitched ×0.45 at 0.16 s with a 70→30 Hz sub drop; 1.8 s |
| `fish_spit.ogg` | rubberduck9999 monster spit; adiantheman mud splash; Kenney `dropLeather`, `bookPlace1` + synth air puff | Spit pitched ×0.7, then at 0.52 s the lump lands (splat + leather thud) and at 0.78 s the paper roll lands; 1.6 s |
| `fish_sink.ogg` | qubodup splash, calebrankin bubbles, csaszi rumble + synth bubbles + synth sub | Water closes (splash ×0.5), eight large bubbles that get lower and further apart, rumble and sub 52→26 Hz fade; 4.8 s |
| `bell_near.ogg` | daytripper TollBell | HP 70 Hz, light reverb, 7.5 s |
| `bell_far.ogg` | daytripper TollBell | LP 1.5 kHz / HP 150 Hz, strike softened, 60 % wet reverb 3.6 s with 70 ms pre-delay; 8.0 s |
| `crowd_murmur.ogg` | PanPiper5 Zanka flute, hellska flute (pitch-warped into 260 short "syllables", no voice material); Kenney `creak1-3`, `cloth1-4`, `impactWood_light_*`, `footstep_wood_*` | Seamless **20.0 s loop**, stereo, −18 LUFS. Murmur of wooden creatures, joint creaks, clacks, cloth, shuffling feet |
| `clack_1..3.ogg` | Kenney `impactWood_light_000-004` + `creak3` slice | Two quick wooden ticks (22–36 ms apart, pitched ×1.25–1.6) + a tiny creak tail; 0.1–0.2 s |
| `sack.ogg` | Fission9 inventory open, Eyewer bag rustle (2.88–3.58 s), Kenney `dropLeather` | Open, stuff, contents settle; 1.26 s |
| `hook_scrape.ogg` | RutgerMuller plank scrape, EricsSoundschmiede wood-on-stone scrape, Kenney `drawKnife1`, `impactMetal_light_000` | Hook tink, then a wooden pole dragged on stone with a faint metal edge; 1.6 s |
| `cart_heavy.ogg` | craigsmith Large Wagon (×0.85), Sonicquinn cart (×0.7), craigsmith buckboard creaks (×0.8), Kenney `impactWood_heavy_*` (cargo shifting) | Seamless **4.8 s loop** (0.5 s crossfade) |
| `file_nose.ogg` | aerror filing (two strokes, ×1.12, HP 700 Hz) + Kenney wood ticks pitched ×2.6–3.2 (crumbs) | 0.64 s |
| `kid_giggle.ogg` | jmarcosfer wood squeak: five 65–110 ms tonal slices pitched ×1.85–1.95, descending | "hee-hee-hee" rhythm made of wood squeaks, two tiny jaw clacks; no voice; 0.86 s |
| `kid_run.ogg` | Kenney `footstep_wood_000-004` pitched ×1.75–1.93, light clacks | 8 quick steps, seamless **1.12 s loop** (also fine as a one-shot) |
| `top_spin.ogg` | gazbooth spinning top (launch rattle 1.05–1.75 s, steady hum 5.6–8 s, slowed 8–11 s), Kenney wood ticks | Launch, spin, slows down with growing wobble, falls over and clatters; 6.0 s |
| `musicbox.ogg` | thomasjaunism music box note (melody and middle tines, re-pitched) + synthesized low tines + synth mechanism | Original tune (D minor, 3/4, 84 bpm, 16 bars); the spring runs down in the last two bars (slower, pitch sags 15 cents); 39 s |
| `musicbox_short.ogg` | same | Second half of the tune only, ends on the tonic, runs down; 18.5 s |
| `musicbox_plink.ogg` | same + Kenney `impactWood_light_002` | Stick taps the box, two stray tines; 2.2 s |
| `drum_stage.ogg` | Sassaby alfaia, cabled_mess frame drum, TheEndOfACycle kick (LP 140 Hz) | One ceremonial stroke, reverb 2.4 s; 3.0 s |
| `amb_hideout.ogg` | deleted-user cave room tone (LP 420 Hz), Sclolex drips (single drips cut out, small-room echo), peridactyloptrix creaks, `crowd_murmur` LP 380 Hz (the village heard through the bark door) + synth low body | **60 s loop**, stereo, −18 LUFS |
| `amb_alley.ogg` | MeanRaccoon wind through window (own 49 s loop, LP 1.6 kHz), LudwigMueller interior wind, Sadiquecat wind whistle, laft2k wood creaking, Kenney `creak1-3`, cognito perceptum distant hammering, Kenney `impactPlank_medium_002` (loose board) | **60 s loop**, stereo, −18 LUFS |
| `amb_plaza.ogg` | `crowd_murmur` (near + far layers), cave room tone, Maestro_Himself curtain, cabled_mess frame drum + Sassaby alfaia (a stage cue rehearsed far away), hollandm woodblock, Kenney planks | **60 s loop**, stereo, −18 LUFS |
| `music_village2.ogg` | foochie_foochie kalimba (melody), sgossner marimba (ostinato, B-section tune), sgossner cello pizzicato (bass), spectral9 wine glass (bowed-glass pad), hollandm woodblock, Kenney wood ticks, cabled_mess frame drum | Original. D dorian, 100 bpm, 24 bars A-B-A; **57.6 s seamless loop** |
| `music_hideout.ogg` | thomasjaunism music box, foochie_foochie kalimba, sgossner bassoon + synth pad | Original. D minor, 3/4, 76 bpm; music box sings the tune, then the kalimba sings it an octave lower; **75.8 s seamless loop** |
| `music_truth.ogg` | sgossner contrabass (drone D2), sgossner bassoon, sgossner cello tremolo (D/E♭ rub), spectral9 glass, cabled_mess frame drum (uneven heartbeat), foochie_foochie kalimba (broken hideout motif), sgossner timpani | Original. Sparse and tense; **64.0 s seamless loop** |
| `music_procession.ogg` | Sassaby alfaia + cabled_mess frame drum + TheEndOfACycle kick (march), hollandm woodblock + Kenney ticks (wooden feet), blood_of_a_pomegranate duduk (reed melody), sgossner bassoon and contrabass (drone), daytripper bell (tuned to D), sgossner cello tremolo | Original. D phrygian, 66 bpm, 16 bars (4 bars drums only, then the reed); **58.2 s seamless loop** |

Suggested credits line addition: *Freesound users calebrankin, Breviceps, magnuswaker, rubberduck9999, peridactyloptrix, laft2k, daytripper, Eyewer, Fission9, RutgerMuller, EricsSoundschmiede, craigsmith, aerror, jmarcosfer, gazbooth, hollandm, cabled_mess, Sassaby, TheEndOfACycle, blood_of_a_pomegranate, spectral9, sgossner (Versilian Studios VSCO 2 CE), MeanRaccoon, Sadiquecat, cognito perceptum, thomasjaunism, hellska. All CC0.*

---

# Pass 3 — creature voices, notebook UI, footsteps by ground (2026-10-23)

38 new files, all from CC0 sources (Freesound "Creative Commons 0" checked on each page; Kenney packs with a CC0 `License.txt`). Same processing as before: mono 44.1 kHz, Ogg Vorbis q6. Voices are at −16 LUFS (same as `speak`). Footsteps are matched to the `step_paper` set at about −25 LUFS with a −1 dBFS peak, using a fast-release limiter on the transient. UI sounds are at their peak ceiling, which puts them at −21 to −27 LUFS, the same range as `page` and `piece`.

## New sources

| Short name | Sound | Author | Page / pack | License |
|---|---|---|---|---|
| pencilwide | writing - pencil - wide 03.wav | Anthousai | https://freesound.org/people/Anthousai/sounds/337091/ | CC0 |
| stamptrad | traditional stamp.wav | I.fekry | https://freesound.org/people/I.fekry/sounds/470710/ | CC0 |
| stamp1 | Stamp | kermite607 | https://freesound.org/people/kermite607/sounds/362624/ | CC0 |
| sloprip | Slow Paper Rip | sgrowe | https://freesound.org/people/sgrowe/sounds/342540/ | CC0 |
| nbclose | Notebook close | Kukensius | https://freesound.org/people/Kukensius/sounds/320456/ | CC0 |
| bookopen | Libro abierto.wav | Sol5 | https://freesound.org/people/Sol5/sounds/450327/ | CC0 |
| stonestep | Footstep on Stone 3 | sgossner | https://freesound.org/people/sgossner/sounds/197780/ | CC0 |
| dirtshoe | Footsteps_6_Dirt_shoe.wav | monte32 | https://freesound.org/people/monte32/sounds/353799/ | CC0 |
| dirtgravel | dirt/gravel footstep 4 | Yoyodaman234 | https://freesound.org/people/Yoyodaman234/sounds/223153/ | CC0 |
| leaves | steps on dry leaves | buojira | https://freesound.org/people/buojira/sounds/540949/ | CC0 |
| bottle | Blowing in a bottle | SamsterBirdies | https://freesound.org/people/SamsterBirdies/sounds/489429/ | CC0 |
| Kenney *Casino Audio* | `card-place-1..3` | Kenney | https://kenney.nl/assets/casino-audio | CC0 |
| Kenney *RPG Audio* | `bookFlip1-3`, `bookOpen`, `bookClose`, `footstep00/02/07`, `cloth1-4`, `creak1-3` | Kenney | https://kenney.nl/assets/rpg-audio | CC0 |
| Kenney *Impact Sounds* | `footstep_concrete_001/003/004`, `footstep_wood_000-004`, `footstep_grass_001-003`, `impactWood_light_*`, `impactSoft_heavy_000` | Kenney | https://kenney.nl/assets/impact-sounds | CC0 |

Also reused: PanPiper5 Zanka pan flute, hellska flute tremolo, astriferal bottle air (credited above).

## Files

| File | Built from | Changes |
|---|---|---|
| `kinopio_speak_1..4.ogg` | Zanka flute warped ×2.9–4.2 into 2–4 quick syllables + Kenney wood ticks ×1.9 | Small, quick, bright wooden-flute chirps. 1 rising (asking), 2 falling (telling), 3 chattering, 4 excited. LP 4.5 kHz; 0.29–0.42 s |
| `chief_speak_1..3.ogg` | Zanka flute ×0.7–0.9 + SamsterBirdies blown bottle + Kenney creak (×0.55, start only) | Slow syllables through a "hollow trunk" resonance (bands 150–260 Hz and 380–520 Hz, short body reverb), LP 2.4 kHz; 0.67–0.74 s |
| `villager_speak_1..4.ogg` | Zanka flute ×1.6–2.2 / hellska flute ×0.85–1.1 + soft wood tick | 2–3 middle syllables, LP 3.2 kHz; 0.32–0.45 s |
| `collector_speak_1..3.ogg` | Zanka flute ×1.0–1.3, astriferal bottle breath, Kenney cloth | Muffled under a hood: LP 700 Hz, breath and cloth brushing; 0.56–0.65 s |
| `pencil_scribble.ogg` | Anthousai pencil (2.76–3.40 s) | HP 300 Hz, limited so the scratch carries; 0.64 s |
| `pencil_tick.ogg` | Anthousai pencil, two strokes (tap + flick ×1.15) | A small check mark; 0.16 s |
| `piece_snap_1..3.ogg` | Kenney `card-place-1..3` + an 80 ms grain of the pencil take + a tiny wood click ×2.2 | Paper piece snapping into place; 0.29–0.35 s |
| `page_flip_1..3.ogg` | Kenney `bookFlip1..3` (×1.0 / 1.04 / 0.96) | Cleaned, HP 200 Hz; 0.22–0.35 s |
| `stamp.ogg` | I.fekry stamp strike + Kenney `impactSoft_heavy_000` (weight) + kermite607 stamp lift (rubber leaving the paper) | 0.52 s |
| `peel.ogg` | sgrowe Slow Paper Rip (0.10–1.42 s), pitched ×0.86 | Slow, slightly lower tear of an aged paper band; 0.15 s fade in; 1.53 s |
| `notebook_open.ogg` | Kenney `bookOpen` + Sol5 book opening (0.26–1.02 s) | 0.79 s |
| `notebook_close.ogg` | Kenney `bookClose` + Kukensius notebook close | 0.65 s |
| `step_stone_1..3.ogg` | Kenney `footstep_concrete_003/004/001` (×1.12–1.2) + sgossner stone step + Yoyodaman234 grit | ≈ −25.5 LUFS; 0.09–0.10 s |
| `step_wood_1..3.ogg` | Kenney `footstep_wood_000/002/004` + RPG `footstep00/02/07` (×1.1–1.25); `_3` adds a small board creak | −25 LUFS; 0.22 s |
| `step_dirt_1..3.ogg` | monte32 dirt-shoe steps (×1.12–1.2) + Kenney `footstep_grass_001-003` thud | −25 LUFS; 0.22 s |
| `step_root_1..3.ogg` | Kenney `footstep_wood_*` (dull, ×1.1) + buojira dry-leaf crunch (×1.2–1.3); `_2` adds a twig tick | −25 LUFS; 0.20 s |

Credits line addition: *Anthousai, I.fekry, kermite607, sgrowe, Kukensius, Sol5, monte32, Yoyodaman234, buojira, SamsterBirdies (Freesound). All CC0.*
