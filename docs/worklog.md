# Worklog

Setup, Terminalbefehle, Versionen. Entscheidungen stehen in `PLAN.md`.

## 30.10.2026 – Projektstart

Repo-Gerüst angelegt: `README.md`, `PLAN.md`, `environment.yml`, `.gitignore`, `docs/`, `notebooks/`, `data/`.

### Umgebung anlegen (macOS, Miniforge)

```bash
cd ~/pfad/zu/astro-pipeline
conda env create -f environment.yml
conda activate astro-pipeline
```

### Versionen festhalten

```bash
python -c "import astropy, astroquery, reproject, numpy; \
print('astropy', astropy.__version__); \
print('astroquery', astroquery.__version__); \
print('reproject', reproject.__version__); \
print('numpy', numpy.__version__)"
conda env export --from-history > docs/environment-history.yml
```

Ergebnis (hier eintragen):

| Paket | Version |
|---|---|
| python | 3.12.16 |
| numpy | 2.5.4 |
| matplotlib | 3.11.2 |
| astropy | 8.0.2 |
| astroquery | 0.4.11 |
| reproject | 0.21.0 |

### Kernel registriert

```bash
python -m ipykernel install --user --name astro-pipeline --display-name "astro-pipeline"
```

### Setup-Check (`notebooks/00_setup_check.ipynb`)

- Interpreter: `/Users/inu/miniforge3/envs/astro-pipeline/bin/python` → richtige Umgebung
- MAST-Abfrage Programm 2733: 10 Beobachtungen auf Stufe 3
  - NIRCam: F090W, F187N, F212N, F356W, F444W;F405N, F444W;F470N
  - MIRI: F770W, F1130W, F1280W, F1800W

### Git

Wichtig: vorher **in den Projektordner wechseln** und mit `pwd` prüfen.
(Erster Versuch lief versehentlich in `~` → `~/.git` wieder gelöscht.)

```bash
cd ~/Projects/astro-pipeline
pwd
git init -b main
git status            # nur Projektdateien?
git add .
git commit -m "Initial project skeleton"
```

`.gitignore` fehlte zunächst (Punkt-Dateien sind im Finder unsichtbar) →
nachträglich angelegt, `.DS_Store` und `.ipynb_checkpoints/` mit
`git rm --cached` entfernt, Commit per `git commit --amend` korrigiert.

Autor-E-Mail auf GitHub-Noreply-Adresse umgestellt (wird im öffentlichen Repo sichtbar):

```bash
git config --global user.email "39085398+Tritium13@users.noreply.github.com"
git commit --amend --reset-author --no-edit
```

GitHub-Remote (leeres privates Repo ohne README/.gitignore/License):

```bash
ssh -T git@github.com     # SSH-Zugang testen
git remote add origin git@github.com:Tritium13/astro-pipeline.git
git push -u origin main
```

### SSH-Schlüssel für GitHub (einmalig)

`ssh -T git@github.com` ergab zuerst „Permission denied (publickey)“ → neuen Schlüssel angelegt:

```bash
ssh-keygen -t ed25519 -C "39085398+Tritium13@users.noreply.github.com"
# ~/.ssh/config: Host github.com / AddKeysToAgent yes / UseKeychain yes / IdentityFile ~/.ssh/id_ed25519
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
pbcopy < ~/.ssh/id_ed25519.pub   # dann GitHub → Settings → SSH and GPG keys → New SSH key
ssh -T git@github.com            # „Hi Tritium13! …“
```

Erster Push nach `origin/main` erfolgreich. **Etappe 0 abgeschlossen.**

### Notizen
- `data/` ist in `.gitignore` – FITS-Dateien nie committen.
- zsh: Zeilen mit `#` nicht ins Terminal kopieren.

## 30.10.2026 – Etappe 1: Daten laden

Notebook `notebooks/01_query_download.ipynb`. 1956 Produkte → 6 i2d-Dateien, alle `PUBLIC`, Status `COMPLETE`.
Speicherort: `data/ngc3132_nircam/` (in `.gitignore`).

| Datei | Größe lokal (Byte) |
|---|---|
| jw02733-o001_t001_nircam_clear-f090w_i2d.fits | 674 000 640 |
| jw02733-o001_t001_nircam_clear-f187n_i2d.fits | 674 121 600 |
| jw02733-o001_t001_nircam_clear-f212n_i2d.fits | 674 121 600 |
| jw02733-o001_t001_nircam_clear-f356w_i2d.fits | 155 139 840 |
| jw02733-o001_t001_nircam_f405n-f444w_i2d.fits | 155 139 840 |
| jw02733-o001_t001_nircam_f444w-f470n_i2d.fits | 155 139 840 |

Hinweis: lokale Größen weichen leicht von der `size`-Spalte der Produktliste ab (siehe Fazit im Notebook).

## 30.10.2026 – Etappe 2: FITS verstehen

Notebook `notebooks/02_inspect_fits.ipynb`.

- Fix: `fits.getheader(path, ext="SCI")` → `ValueError`; richtig ist `extname="SCI"` (oder `ext=("SCI", 1)`).
- `FITSFixedWarning` (datfix/obsfix) beim Einlesen des WCS: harmlos, astropy ergänzt Standard-Schlüsselwörter im Speicher.

| Band | FILTER | PUPIL | Kanal | Shape | Pixel (″) | t_exp (s) | NaN % | bkg | noise | p99.9 |
|---|---|---|---|---|---|---|---|---|---|---|
| F090W | F090W | CLEAR | SHORT | 4894×4916 | 0.0307 | 1460 | 2.1 | 0.231 | 0.083 | 16.1 |
| F187N | F187N | CLEAR | SHORT | 4894×4917 | 0.0307 | 2319 | 2.1 | 0.250 | 0.486 | 56.8 |
| F212N | F212N | CLEAR | SHORT | 4895×4916 | 0.0307 | 2319 | 2.2 | 0.375 | 0.857 | 43.3 |
| F356W | F356W | CLEAR | LONG | 2348×2356 | 0.0630 | 1460 | 2.0 | 0.130 | 0.072 | 8.1 |
| F405N | F444W | F405N | LONG | 2348×2356 | 0.0630 | 2319 | 2.0 | 0.153 | 0.192 | 34.0 |
| F470N | F444W | F470N | LONG | 2348×2356 | 0.0630 | 2319 | 2.1 | 0.552 | 0.933 | 54.5 |

Einheit aller SCI-Daten: MJy/sr. bkg/noise = sigma-clipped Median/Std über das ganze Bild (enthält vermutlich schwaches Nebellicht).

## 30.10.2026 – Etappe 3: Registrierung

Notebook `notebooks/03_reproject.ipynb`.

- Zielraster per `find_optimal_celestial_wcs` ((shape, wcs)-Tupel wurden akzeptiert): 3127 × 3121 px, 0,063″/px, Norden oben, TAN. ≈57 % gültige Pixel (gedrehte Originale → leere Ecken).
- `reproject_adaptive(..., conserve_flux=False)`: F090W/F187N/F212N je ≈24 s, F356W/F405N/F470N je ≈9 s.
- Ausgabe: `data/ngc3132_nircam_reproj_lw/ngc3132_<band>_reproj_lw.fits` (Primary = SCI mit WCS + BAND/BUNIT/SRCFILE/REPROJ, Extension FOOTPRINT), ≈39 MB pro Filter.
- Sternkontrolle (9 Sterne, Zentroid vs. F356W, Median): F090W 0,18 px, F187N 0,15, F212N 0,10, F405N 0,24, F470N 0,20 (1 px = 63 mas).
- Vorschaubilder zum Ansehen durch Claude liegen in `data/_previews/` (ignoriert von Git, kann gelöscht werden).

## 30.10.2026 – Etappe 4: Hintergrund und Streckung

Notebook `notebooks/04_stretch.ipynb`, Parameter in `params/ngc3132_stretch.json` (im Git), gestreckte Bilder in `data/ngc3132_nircam_stretched/` (nicht im Git).

- Himmelsboxen: 150 × 150 px, ≥150 px vom Rand, Mindestabstand 500 px (erste Version ohne Mindestabstand: alle 6 Boxen in einer Ecke → Ungleichmäßigkeit unterschätzt).
- Gesättigte Kerne: zuerst schwarz (gemeinsame Gültigkeitsmaske) → Lücken mit `binary_fill_holes` gefunden und mit Maximalwert gefüllt (F090W 396, F187N 257, F212N 209, F356W 509, F405N 245, F470N 162 px).
- Korrektur einer falschen Begründung: größeres k senkt den Schwarzpunkt → Hintergrund heller, nicht ruhiger. Für verrauschte Filter daher negatives k.

| Band | bkg | noise | spread/noise | k | black | white |
|---|---|---|---|---|---|---|
| F090W | 0.2067 | 0.0184 | 1.49 | 0.5 | −0.009 | 18.42 |
| F187N | 0.0301 | 0.1099 | 3.69 | −1.0 | 0.110 | 57.33 |
| F212N | −0.0126 | 0.1057 | 2.62 | −1.5 | 0.159 | 43.29 |
| F356W | 0.1123 | 0.0041 | 3.49 | 1.0 | −0.004 | 8.54 |
| F405N | 0.1166 | 0.0360 | 0.98 | 1.0 | −0.036 | 34.01 |
| F470N | 0.4152 | 0.0573 | 2.25 | −0.5 | 0.029 | 54.18 |

(black/white relativ zum abgezogenen Hintergrund, MJy/sr; asinh a = 0,05 für alle.)

## 30.10.2026 – Etappe 5: Farbe

Notebook `notebooks/05_color.ipynb`, Zuordnungen in `params/ngc3132_color.json` (im Git), Vorschauen in `output/previews/` (≈1040 px, im Git), volle Auflösung als `.npy` in `data/ngc3132_nircam_color/` (nicht im Git).

- Mischung: RGB = Σ(w·img·Farbe) / Σ(w·Farbe) pro Kanal, auf 0–1 begrenzt.
- Varianten: A chromatisch (240° → 0° nach Wellenlänge), B NASA-Schlüssel, C physikalisch gruppiert.
- Beobachtung: A/B wirken blass (gelb/oliv außen, weißlich/lavendel innen), weil jede Komponente in zwei weit auseinanderliegenden Filtern leuchtet und sich aus Gegenfarben mischt. C trennt Innen (blau) und Außen (rot-orange) kontrastreich.
- Entscheidung: C. Sterne in C gelbstichig (beide Breitbandfilter gelb); Variante D (Breitband fast weiß) besprochen, nicht umgesetzt.

## 30.10.2026 – Etappe 6: Export

Notebook `notebooks/06_export.ipynb`.

- Ausschnitt: Mitte (y, x) = (1570, 1575), 1578 × 1578 px ≈ 1,66′ × 1,66′; gut belichteter Bereich = gültig in allen Filtern + 120 px Randabstand (44,5 % des Rasters).
- WCS-Check: Norden oben, Osten links.
- Fehler: `tifffile` → „TIFF strings must be 7-bit ASCII“ (Umlaute in der Beschreibung). Lösung: Beschreibung transliteriert (`str.maketrans`), volle UTF-8-Fassung in PNG und `.md`. Bildunterschrift anschließend auf Englisch umgestellt.
- Dateien: `output/full_res/ngc3132_nircam_C_physical_16bit.tif` (14,9 MB), `…_full.png` (2,4 MB) – nicht im Git; `output/ngc3132_nircam_C_physical_web.jpg` (0,33 MB), `…_caption.md` – im Git.

## 31.10.2026 – Etappe 7a: Paket + Regressionstest

```bash
pip install -e . --no-deps    # in env astro-pipeline, im Projektordner
```

- `src/astropipe/` (bands, mast, registration, stretch, color, export), `pyproject.toml`; `.gitignore` um `*.egg-info/`, `build/` ergänzt.
- `notebooks/07_regression_ngc3132.ipynb`: Zielraster, F356W-Reprojektion, Lücken, Boxen, Hintergrund, Streckung bitgenau; Farbe C max. 1,46e-5 (RGB in JSON auf 4 Stellen gerundet).

## 31.10.2026 – Etappe 7b: NGC 6720 (Ring-Nebel)

Notebooks `08_ngc6720.ipynb`, `08a_destripe_ngc6720.ipynb`, `08b_destripe_local_ngc6720.ipynb`; Parameter `params/ngc6720_stretch.json`, `params/ngc6720_color.json`.

- MAST: Programm 1558, 4 i2d (F150W2;F162M, F212N, F300M, F335M), alle `o005`, 483 s, 1,79 GB.
- Registrierung: Raster 3311 × 3312 px (≈45° gedreht, 46,6 % gültig); Versatz 0,02–0,16 px.
- Himmelsboxen: Box 0 (Score −0,074, dunkles Detektorband) und Box 1 (−0,004) verworfen → Regel „Score > 0“. Zwischendurch Zustandsfehler im Notebook (`boxes` überschrieben → erst 3, dann 1 Box) → Lösung: neue Variable `boxes_used` + „Restart Kernel and Run All“.
- Streifen: in i2d entlang der Zeilen (Zeilen/Spalten 2,1–3,5). 08a: leerer Himmel, ganze Zeile → kaum Wirkung; 512-px-Abschnitte → −30 % (pro 128-px-Block), aber Abschnitte im Nebel unkorrigiert → blaue F162M-Streifen im Innenraum. 08b: lokales Modell (16-px-Medianzellen; Testbild: Fehler 0,14 vs. 0,44 alt) → flächige Korrektur auch im Nebel; Kennzahl (lokaler Rest) F162M 0,088 → 0,072 (alt) → 0,065 (neu), F212N 0,770 → 0,630 → 0,578.
- Download-Schutz: `mast.download` lädt nur fehlende Dateien (Größenvergleich, 1 % Toleranz).
- Export: Variante C, Querformat 4:3, Mitte (1671, 1608), 1562 × 1172 px ≈ 1,64′ × 1,23′; `output/ngc6720_nircam_C_physical_web.jpg` + `_caption.md`.

## 31.10.2026 – NIRCam + MIRI (NGC 6720)

Notebooks `09_miri_ngc6720.ipynb` (Bestandsaufnahme), `09a_combine_nircam_miri_ngc6720.ipynb` (Kombination); Parameter `params/ngc6720_nircam_miri.json`.

- MAST MIRI/IMAGE Programm 1558: 18 i2d. o001 = Hauptmosaik, 9 Filter (F560W–F2550W), 444 s, je 48 MB, alle auf einem Raster (1043 × 1644 px, 0,111″/px). o002/o004 = Simultanaufnahmen während MRS (3 Filter, Teilbereiche), o003 = MRS-OFF (Hintergrundposition ≈ 5,5′ abseits). Geladen nur o001 (0,43 GB).
- Überlappung NIRCam ∩ MIRI enthält den ganzen Ring; gültig in allen 7 Filtern: 35,9 % des Rasters. Abgesetztes Rechteck oben links in MIRI vermutlich Koronografenfeld (fällt weg).
- MIRI auf NIRCam-Raster hochgerechnet (`reproject_adaptive`). Versatz gegen F335M: F560W −1,06/+0,67 px, F770W −1,03/+0,65 px (dy/dx), F1500W unsicher (Streuung ≈ 2 px). Gemeinsame Verschiebung aus F560W+F770W → danach 0,17/0,26 px.
- MIRI-Hintergrund hoch (F1500W ≈ 38 MJy/sr) und ungleichmäßig (spread/noise ≈ 9,8 bei F1500W); 6 Boxen, alle Score > 0.
- Package: `color.luminance`, `color.apply_luminance` (LRGB), `registration.star_shifts`, `registration.apply_shift`.
- Export: `output/ngc6720_nircam_miri_W2_ionisation_web.jpg` + caption, `output/ngc6720_nircam_miri_W2s_psf_matched_web.jpg` + caption (Ausschnitt 1338 × 1004 px ≈ 1,40′ × 1,05′).

## 31.10.2026 – Etappe 9, Stufe 2: Skript + Konfiguration

```bash
python -m astropipe.run configs/ngc3132.toml          # im Projektordner, env astro-pipeline
python -m astropipe.run configs/ngc3132.toml --no-export
```

- Neu: `src/astropipe/run.py`, `configs/ngc3132.toml`, `configs/ngc6720.toml`, `notebooks/10_run_configs.ipynb`.
- Regressionstest: NGC 3132 Streckung (6 Filter) und Farbe C max. |diff| = 0; Ausschnitt (1570, 1575), 1578 px wie Notebook 06. NGC 6720 Streckung (4 Filter) = 0; Ausschnitt (1671, 1608), 1562 × 1172 px wie Notebook 08; gleiche 4 Himmelsboxen.
- Laufzeit: NGC 3132 8 s (Reprojektion aus dem Terminal-Lauf wiederverwendet), NGC 6720 89 s inkl. lokaler Streifenkorrektur und Reprojektion.
- Fix: `mast.total_size_gb` gibt bei leerer Liste 0 statt NaN (Warnung „converting a masked element to nan“).

## 31.10.2026 – Etappe 9, Stufe 3: Entdecker-Modus + Lückenfehler

```bash
python -m astropipe.explore              # zufälliger Kandidat, Lauf + Bericht
python -m astropipe.explore --seed 42    # reproduzierbar
python -m astropipe.explore --no-run     # nur suchen + Konfiguration schreiben
```

- Neu: `src/astropipe/explore.py`, `notebooks/11_explore.ipynb`, `configs/explore/`.
- Erster Lauf: Fenster 2025-08-10 + 30 d, 224 Beobachtungen, 32 Kandidaten; 2 zu groß (> 3 GB), gewählt `jw08277-o004_t003` (NGC1527, Programm 8277, F115W/F200W/F277W, 2,89 GB). Raster 5385 × 3366 px (zwei Module).
- Fehler 1: kein Ausschnitt um den Helligkeitsschwerpunkt möglich → `export.interior_center`, Option `export.center = "auto"`.
- Fehler 2: bunte Einzelpixel = NaN-Lücken aus defekten Pixeln, die als „gesättigt“ weiß gefüllt wurden. Erste Korrektur (globales 99-%-Perzentil) → im Regressionstest NGC 3132 alles CHECK. Diagnose (`stretch.classify_holes`, Ausschnitte): die als „bad“ eingestuften Lücken liegen auf Himmel/Nebelrauschen (innerer ≈ äußerer Ring) → die **alte** Füllung war falsch. Klarstellung: F405N/F470N haben am Zentralstern keine Lücken (das schwarze Zentrum in Etappe 4 kam aus den anderen Filtern).
- Endgültiges Kriterium: lokaler Kontrast (Ring 1–2 px vs. 6–10 px). Prüfung gegen alte Ergebnisse: innerhalb der defekten Pixel max. |diff| 1,0, außerhalb max. 1,5·10⁻² (F090W), meist ~10⁻³ (verschobener Weißpunkt); F300M/F335M ohne defekte Pixel identisch.
- Explorer-Bericht mit Warnhinweisen: `output/runs/<prefix>_report.md`.

## 31.10.2026 (Nachmittag) – Explorer: Übersicht, Cache-Fehler, leere Felder

- `09a` neu gelaufen (neue Lückenfüllung); W2/W2s minimal verändert.
- Explorer `--seed 7` → NGC 5643 (Programm 1685, F090W/F150W/F277W, 2,71 GB). Kern liegt im Lückenkreuz der SW-Detektoren → Ausschnitt nur 0,74′ in einem Detektor. Neu: `export.save_overview` (`*_overview.jpg`), Bericht mit Anteil defekter Pixel und Hinweis „Helligkeitsschwerpunkt an Lücke“.
- Seed war nicht reproduzierbar (Zeitfenster hing an der Uhrzeit, MAST-Reihenfolge) → behoben; zweiter Lauf lieferte J0217-0208 (Programm 1657, F150W/F200W/F300M/F410M).
- J0217-0208: starke Streifen + farbige Blöcke. `clean.method = "local"` ohne Wirkung, weil (1) `reproject_all` alte Dateien nur nach Namen wiederverwendete (behoben: `SRCFILE` + Zeitstempel), (2) `cleaned/` ebenso (behoben: Header `ASTCLEAN` = Hash der Einstellungen), (3) breite Bänder vom 16-px-Modell bzw. Hochpass `smooth = 51` nicht erfasst werden. Lösung: `sky`, `smooth = 0`, `segment = 512`, `clean.subtract_background_2d` (128 px). Streifenrichtung gemessen: Zeilen ≈ 2× stärker als Spalten.
- Ergebnis: Blöcke fast weg, Reststreifen in F150W/F200W → bekannte Einschränkung (Einzelaufnahmen im i2d gegeneinander versetzt), mögliche Etappe 10.
- Neu: `clean.method = "auto"` (`run.assess_field`), Explorer schreibt es als Standard. Test: `configs/explore/jw01657-o006_t002_auto.toml`.

## 31.10.2026 (später Nachmittag) – NGC 5643 aus zwei Beobachtungen, Planeten-Bestand

- `clean.method = "auto"`: erstes Kriterium (Himmelsanteil > 50 %) scheiterte (leeres Feld 0,43–0,51) → großräumige Struktur / Rauschen (< 3 σ = leer). J0217: 0,6–1,0 σ → `sky` + 2-D-Hintergrund, wie von Hand. NGC 5643: 16–39 σ → gefüllt; Streifenmaß am Himmelsprofil lieferte 1–6 (Galaxie selbst) → bei gefüllten Feldern am lokalen Rest: 0,12–0,28.
- MAST, Programm 1685: alle sechs Galaxien je zwei Beobachtungen; N5643 o011 (07.07.2023) und o012 (22.07.2023), Umrisse (`s_region`) zeigen vertauschte Module, leichte Drehung → kombinieren.
- `run.py`: `data.obs` als Liste, Schlüssel `<band>_<oNNN>`, `combine_observations` (Median-Offset im Überlapp, Mittelwert). `configs/ngc5643.toml`: Raster 7724 × 2882, Offsets −0,013/+0,008/+0,014, Sternversatz 0,1 px, Laufzeit 643 s inkl. 2,7 GB Download. Ausschnitt von Hand `[3860, 1597]`, 2100 px.
- Planeten in MAST (NIRCam, Stufe 3): Jupiter 1022/1373/9022, Mars 1415/2787, Neptun 2739, Uranus 2739/2768/6379/8975/9482; Saturn nicht gefunden → Etappe 11 (Idee).

## 31.10.2026 (Abend) – Etappe 8: Übersetzung und Veröffentlichung vorbereitet

- Branch `english`. Markdown-Zellen aller Notebooks per Skript ersetzt (JSON-Format wie Jupyter: `indent=1`, `sort_keys`, `ensure_ascii=False`), Code/Ausgaben unverändert; einzige Code-Änderung: Orientierungstext in `06_export` (Zelle 7).
- `explore.write_report` auf Englisch; README neu (englisch), `LICENSE` (MIT), `scipy` explizit in `environment.yml`.
- Quellen: MAST Data Use Policy (https://archive.stsci.edu/data_use.html), MAST Mission Acknowledgements (https://archive.stsci.edu/acknowledgments.html), NIRCam-Filter (https://jwst-docs.stsci.edu/jwst-near-infrared-camera/nircam-instrumentation/nircam-filters), Pontoppidan et al. 2022 (arXiv:2207.13067).

## 31.10.2026 (Abend) – Etappe 11: Neptun

- Bestand: Planeten in MAST (NIRCam, Stufe 3) per `target_name`-Liste; Neptun = Programm 2739, o004, 4 Filter, 1,65 GB (`data/neptune_2739_nircam/`).
- Header: `TARGTYPE = MOVING`; `MT_AVRA/MT_AVDEC` im SCI-Header (nicht im Hauptheader – erster Fehler in `run.py`). Filterpaare F140M+F300M (06:28–07:52 UTC) und F210M+F460M (06:52–08:33 UTC), Bewegung dazwischen 0,62″.
- Erst per Skript (`configs/neptune.toml`, ganzes Feld) versucht → zu dunkel, Triton-Artefakt; dann auf Wunsch Notebook `12_neptune.ipynb` Schritt für Schritt (wie bei den Nebeln).
- Streifen: `sky`, `smooth = 0`, 2-D-Hintergrund 128 px – schadet den Ringen nicht, hilft um Neptun aber wenig.
- Ausrichtung: WCS-Verschiebung um MT-Differenz; Scheibenmitte zuerst helligkeitsgewichtet (1–5 px, Wolken), dann mit halbierter Schwelle (24 px, Ringe verschmelzen), schließlich Schwelle aus F460M-Scheibe → 0,5–0,9 px.
- Nahaufnahme 14″ bei 0,031″/px (455 px). Gesättigte Wolkenkerne in F210M (47 px) → `fill_holes(sat_fill="local")` + in allen Filtern weiß.
- Farbe: 7 Varianten (A–E, G, G2) verglichen; Export A_chromatic + G_white_clouds (`output/neptune_*`), Parameter `params/neptune.json`.
- Nächster Schritt: weitere Planeten mit dem Notebook testen, Skript erst danach angleichen.

## 31.10.2026 (Abend) – Etappe 11: Uranus

- `13_uranus.ipynb`: Kopie des Neptun-Ablaufs mit Parameterzelle (TARGET, PROGRAM, OBS, FIELD_ARCSEC, SHARP, EXCLUDE). Programm 6379, o002, 6 Breitbandfilter, 0,72 GB (`data/uranus_6379_nircam/`). Kurzwellen-i2d nur 119 MB (kleineres Feld als bei Neptun).
- Drei Zeitgruppen (F150W+F356W 07:49, F115W+F444W 08:32, F070W+F277W 09:12 UTC); Bewegung 0,24″ pro Gruppe.
- Fehler 1: F070W-Scheibe vollständig gesättigt (alle 7161 Scheibenpixel NaN) → `EXCLUDE = ["F070W"]`. Fehler 2: `SHARP` nach Neuausführen der Parameterzelle wieder `None` → fest „F150W“.
- Scheibenmitte: F444W/F277W/F150W zeigen vor allem die helle Polregion (vermutet) → Referenz F115W (ganze Scheibe). F115W↔F356W 1,7 px; Abweichungen der anderen = Kappe, nicht Versatz (gleichzeitige Paare).
- 2-D-Hintergrund zog den äußeren Lichthof ungleichmäßig ab → `USE_BG2D = False`. Streckung a = 0,02; F356W-Weißpunkt aus dem Feld (99,95 %).
- Farbe: A (goldene Ringe), A_lrgb, B_ice (F356W grau → Ringe rosa: einziger Rotbeitrag), C_gold_rings (rot), D_silver_rings (F356W als weißes Licht überlagert) → Export A + D (`output/uranus_*`), Parameter `params/uranus.json`.

## 01.11.2026 – Etappe 11: Jupiter

- Bestand per `Abfragen.ipynb` (zuletzt freigegebene Daten + Jupiter-Liste). Gewählt: Programm 1373, o008, F212N + F335M gleichzeitig (27.07.2022, 10:51–11:00 UTC) → keine Rotation zwischen den Filtern. Entdrehung mehrerer Paare bewusst auf später verschoben.
- `14_jupiter.ipynb` nach dem Uranus-Muster: Nahaufnahme 50″, Raster 1626² bei 0,0307″/px, Planet ≈ 40″.
- Fehler 1: `disk_mask` erfasste nur 12″ → `planet_mask` (5 % des 99-%-Perzentils, größte Fläche, Löcher gefüllt).
- Fehler 2: gesättigte Randsicheln und Bogen um den Großen Roten Fleck in F335M wurden schwarz → NaN auf dem Planeten (Maske + 15 px Dilatation) = gesättigt → weiß, in `sat_union`. F212N: 5008 px defekt/verworfen, 2888 px gesättigt; F335M: 2213 bzw. 28 880 px.
- Fehler 3: Weißpunkt aus den aufgefüllten Pixeln → `disk = planet & ~sat_union`. Weißpunkte F212N 20 612, F335M 1741.
- Diagnose-Zelle: verworfene (NaN-)Pixel liegen gehäuft an scharfen, bewegten Strukturen (GRS-Rand, kleine Wolken) – vermutlich Ausreißererkennung der Pipeline wegen Jupiters Drehung zwischen den Dithern (nicht geprüft). Nach dem Füllen nicht mehr sichtbar.
- a = 0,1 vs. 0,2 verglichen → 0,2 (mehr Banddetail).
- Export A_bicolour + B_warm_bands (`output/jupiter_*`), Parameter `params/jupiter.json`.
- Nachtrag: dunkelblaue Punkte im Farbbild A = **nicht markierte dunkle Flecken nur in F335M** (55 auf der Scheibe, 15–50 % unter der Umgebung, Median ≈ −34 %); schon im MAST-i2d (133 lokale Minima, volles Gewicht, meist alle 3 Dither beteiligt), nicht deckungsgleich mit den NaN-Pixeln. Vermutung: ein schlechter Wert in einer von drei Aufnahmen (nicht geprüft). Neuer Schritt 5b: < 0,85 × 15-px-Median, ≤ 40 px, Scheibe ohne Rand → lokaler Median; bei 0,9 fände die Suche in F212N schon 80 echte Strukturen. Vorher/Nachher in Schritt 7b, `output/jupiter_dark_spots_comparison.jpg`.

## 01.11.2026 (Mittag) – neue MAST-Daten per Skript: Säule (Programm 12591)

- Explorer erweitert: `--program N` (optional `--obs <prefix>`) wählt eine Beobachtung aus einem bestimmten Programm statt eines Zufallsfensters; `write_config` übernimmt `--max-gb` (vorher fest 3,0 → Download hätte abgebrochen).
- `python -m astropipe.explore --program 12591 --max-gb 7 --no-run` → `jw12591-o003_t001` („Star-Forming-Pillar“, beobachtet 27.05.2026, freigegeben 29.10.2026), 6 Filter F090W/F187N/F212N/F277W/F335M/F470N, 6,28 GB.
- Lauf `python -m astropipe.run configs/explore/jw12591-o003_t001.toml`: 967 s inkl. Download; Raster 5691 × 2399 px (0,063″); Feldtyp „ausgedehntes Objekt“, Streifen ≤ 0,07 → keine Korrektur; Sternversatz 0,09–0,23 px; RAM reichte (16 GB).
- Automatischer Ausschnitt (Helligkeitsschwerpunkt, 1610² px) schnitt den Säulenkopf mit dem jungen Stern ab → von Hand Hochformat `center = [2810, 1290]`, `size_px = [3400, 1900]` (2,0′ × 3,6′); zweiter Lauf 133 s (Cache).
- Standardparameter ohne weitere Anpassung; Farbe A_chromatic.
