# Planung: Astro-Pipeline

Stand: 30.10.2026 · Nebenprojekt (PhD-Bewerbungen und Bildanalyse-Projekt haben Vorrang)

## Ziel

Eigene, nachvollziehbare Python-Pipeline: öffentliche JWST-Daten aus MAST → Farbbild.
Am Ende ein öffentliches GitHub-Repo mit dokumentierten Notebooks.

## Abschluss-Checkliste je Etappe

Eine Etappe ist erst fertig, wenn:
1. im Notebook die Zellen **Ergebnis** (oben) und **Fazit** (unten) ausgefüllt sind,
2. `docs/worklog.md` die Befehle/Dateien/Versionen dieser Etappe enthält,
3. Entscheidungen hier in der Tabelle stehen,
4. alles committet und gepusht ist.

## Etappen

### Etappe 0 – Setup
- [x] conda-Umgebung `astro-pipeline` aus `environment.yml` anlegen (nicht `bia`) – 30.10.2026
- [x] Tatsächlich installierte Versionen in `docs/worklog.md` festhalten
- [x] Git-Repo initialisieren, erster Commit, GitHub-Remote (privat: Tritium13/astro-pipeline)
- [x] Kurztest im Notebook `00_setup_check.ipynb`: Importe ok, MAST erreichbar (10 Beobachtungen zu Programm 2733)
- [x] Ergebnis/Fazit in `00_setup_check.ipynb` nachtragen

### Etappe 1 – Daten finden und laden (`notebooks/01_query_download.ipynb`)
- [x] Mit `astroquery.mast.Observations` nach NGC 3132, Programm 2733, NIRCam suchen
- [x] Produktliste auf Stufe 3 (`calib_level=3`) und `_i2d.fits` filtern
- [x] Gesamtgröße aus der Spalte `size` berechnen, **bevor** geladen wird
- [x] Ein Filter zuerst laden, dann den Rest (6 Dateien, ≈2,49 GB, alle `COMPLETE`)
- [x] Ergebnis/Fazit in `01_query_download.ipynb` ausgefüllt
- [x] Commit + Push

### Etappe 2 – FITS verstehen (`02_inspect_fits.ipynb`)
- [x] Aufbau einer i2d-Datei: Extensions (SCI, ERR, WHT …), Header, Einheiten (MJy/sr)
- [x] WCS (Pixel ↔ Himmelskoordinaten) verstehen (SW 0,0307″, LW 0,063″, Bildfeld ≈2,47′)
- [x] Histogramm, NaN-Ränder, Hintergrund, Dynamikumfang ansehen
- [x] Alle 6 Dateien geöffnet (Integritätscheck ok)
- [x] Ergebnis/Fazit in `02_inspect_fits.ipynb` ausgefüllt
- [x] Commit + Push

### Etappe 3 – Ausrichten / Registrierung (`03_reproject.ipynb`)
- [x] Referenzraster wählen (3127 × 3121 px, 0,063″/px, Norden oben)
- [x] Alle Filter mit `reproject_adaptive` auf dieses Raster bringen (≈24 s SW, ≈9 s LW pro Filter)
- [x] Kontrolle: Sterne deckungsgleich (Versatz 0,10–0,24 px; Overlay symmetrisch)
- [x] Ergebnis/Fazit in `03_reproject.ipynb` ausgefüllt
- [x] Commit + Push

### Etappe 4 – Strecken (`04_stretch.ipynb`)
- [x] Hintergrund in 6 verteilten leeren Boxen messen (Mindestabstand 500 px), abziehen; Schwarz-/Weißpunkt festlegen
- [x] Gesättigte Sternkerne (NaN-Lücken im Bild) gefüllt statt schwarz
- [x] F187N/F212N: Detektor-Muster mit negativem k im Schwarzpunkt weitgehend versteckt (bekannte Einschränkung)
- [x] Linear vs. Wurzel vs. log vs. asinh verglichen (F212N)
- [x] Gewählte Parameter pro Filter dokumentiert (`params/ngc3132_stretch.json`)
- [x] Ergebnis/Fazit in `04_stretch.ipynb` ausgefüllt
- [x] Commit + Push

### Etappe 5 – Farbe zuordnen (`05_color.ipynb`)
- [x] Chromatische Zuordnung (A) als Basis
- [x] Mehr als 3 Filter: Farbton pro Filter, additiv gemischt (normiert, Weiß bei allen = 1)
- [x] Physikalisch gruppierte Variante (C) ergänzt; Idee D (Breitband fast weiß, „LRGB“) besprochen, nicht umgesetzt
- [x] Mit der offiziellen Zuordnung verglichen (B)
- [x] Ergebnis/Fazit in `05_color.ipynb` ausgefüllt
- [x] Commit + Push

### Etappe 6 – Export und Feinschliff (`06_export.ipynb`)
- [x] Ausschnitt: größtes Quadrat im gut belichteten Bereich (120 px Randabstand), 1578 × 1578 px ≈ 1,66′, Mitte = Schwerpunkt F405N
- [x] Orientierung per WCS geprüft: Norden oben, Osten links
- [x] 16-bit TIFF + PNG (voll, `output/full_res/`, nicht im Git) + JPEG (Web, `output/`)
- [x] Bildunterschrift (englisch) aus Parameterdateien erzeugt: Programm, Filter, Farbzuordnung, Bearbeitung, Credits
- [ ] Credits-Hinweise von STScI/MAST und Linienzuordnung der Filter vor Veröffentlichung prüfen
- [ ] Ergebnis/Fazit in `06_export.ipynb` ausgefüllt
- [ ] Commit + Push

### Etappe 7 – Zweites Objekt / Generalisierung
- [ ] Ring-Nebel NGC 6720 (Programm 1558) mit derselben Pipeline
- [ ] Wiederverwendbare Funktionen in `src/` auslagern (Farbvarianten A/B/C per Parameter wählbar)
- [ ] Optional: NIRCam + MIRI kombinieren
- [ ] Ideen NGC 3132: Variante D (Breitband fast weiß → weiße Sterne), größerer/anderer Ausschnitt für die äußeren Schalen, Maßstab + Kompass

### Etappe 8 – Veröffentlichung
- [ ] Entscheiden: Repo vollständig auf Englisch (README, Markdown-Zellen, Fazits)?
- [ ] README mit Beispielbildern, Lizenz, Datennachweis
- [ ] Repo öffentlich schalten

## Entscheidungen

| Datum | Entscheidung | Begründung | Status |
|---|---|---|---|
| 30.10.2026 | Erstes Objekt: NGC 3132 (Südlicher Ringnebel), nur NIRCam | Planetarischer Nebel, ein Bildfeld statt großem Mosaik; Early-Release-Daten (Programm 2733) seit 2022 öffentlich; offizielle Farbzuordnung als Vergleich veröffentlicht | angenommen |
| 30.10.2026 | Einstieg mit Stufe-3-Produkten (`_i2d.fits`) | Schon kalibriert, kombiniert und auf ein Himmelsraster gebracht; die eigene JWST-Kalibrier-Pipeline ist für den Einstieg nicht nötig | angenommen |
| 30.10.2026 | Werkzeuge: astropy, astroquery, reproject, matplotlib | Etablierte, gepflegte Pakete aus dem Astropy-Umfeld; über conda-forge verfügbar | angenommen |
| 30.10.2026 | Versionen nicht in `environment.yml` pinnen, sondern nach Installation im Worklog festhalten | Neueste kompatible Versionen ziehen, trotzdem reproduzierbar | angenommen |
| 30.10.2026 | Referenzraster: neues gemeinsames Raster mit 0,063″/px (LW-Auflösung), Norden oben, TAN, via `find_optimal_celestial_wcs` | Alle 6 Filter haben leicht unterschiedliche Raster und sind gedreht → alle reprojizieren; LW-Auflösung schont RAM (≈4× weniger Pixel) und verliert bei LW nichts; Norden oben = Konvention, Ausschnitt/Drehung fürs Endbild in Etappe 6. SW-Auflösung später als Option fürs finale Bild | angenommen |
| 30.10.2026 | Reprojektionsmethode: `reproject_adaptive`, `conserve_flux=False` | SW wird um Faktor 2 verkleinert: adaptive Methode mittelt (wie Binning „Average“) statt nur zu interpolieren; Einheit MJy/sr ist Flächenhelligkeit → mitteln, nicht summieren | angenommen |
| 30.10.2026 | Streckung: asinh (a = 0,05) nach Hintergrundabzug; Schwarzpunkt `bkg − k·noise` (k pro Filter: F090W 0,5; F187N −1; F212N −1,5; F356W 1; F405N 1; F470N −0,5), Weißpunkt 99,9-%-Perzentil pro Filter | asinh: nahe 0 linear (Rauschen ruhig), hell logarithmisch (Stern gebändigt); log hob Detektor-Streifen stark an. Negatives k versteckt die Detektor-Muster in F187N/F212N auf Kosten der schwächsten Struktur. **Ästhetisch:** jeder Filter auf eigenen Weißpunkt normiert → relative Helligkeiten zwischen Filtern gehen verloren | angenommen |
| 30.10.2026 | Ausschnitt/Export: quadratisch, nur gut belichteter Bereich; keine lokalen Eingriffe; Bildunterschrift englisch, TIFF-Beschreibung ASCII-transliteriert | Bild ohne leere Ecken/verrauschte Ränder; Bearbeitung vollständig durch Notebooks + Parameterdateien beschrieben; Englisch für öffentliches Publikum; TIFF erlaubt nur 7-bit-ASCII | angenommen |
| – | Repo-Sprache: komplett Englisch? | am Ende (Etappe 8) entscheiden | offen |
| 30.10.2026 | Gesättigte Sternkerne: NaN-Lücken innerhalb des Bildes (`binary_fill_holes`) mit dem Maximalwert des Filters füllen | Pipeline setzt gesättigte Pixel auf NaN; ohne Füllung würden Sterne über die gemeinsame Gültigkeitsmaske in allen Filtern schwarz. Kosmetischer Eingriff (≈160–510 px pro Filter) | angenommen |
| 30.10.2026 | Farbzuordnung: **C – physikalisch gruppiert** (F187N 200°, F405N 225° → Blau/Cyan, ionisiertes Gas; F212N 20°, F470N 0° → Orange/Rot, molekularer Wasserstoff; F090W 55°, F356W 40° → Gelb, Breitband/Sterne), alle Gewichte 1 | Größter Kontrast zwischen innerer Blase und äußeren Schalen: jede physikalische Komponente bleibt in einer Farbfamilie, statt sich wie bei A/B aus Gegenfarben zu blassen Tönen zu mischen. Sieht dem veröffentlichten NASA-Bild am ähnlichsten. **Frei gewählt, nicht chromatisch**; bekannte Folge: Sterne gelbstichig. A und B bleiben in `params/ngc3132_color.json` dokumentiert | angenommen |

## Referenz: offizielle Zuordnung NGC 3132 (NIRCam)

Laut NASA-Seite zum Bild: Rot F470N, Rot F405N, Gelb F356W, Grün F212N, Cyan F187N, Blau F090W.
Quelle: https://science.nasa.gov/asset/webb/southern-ring-nebula-nircam-compass-image

## Wissenschaftlich vs. ästhetisch – wie ich es dokumentiere

- Jedes Bild bekommt eine Tabelle: Filter → Farbe, Streckfunktion + Parameter, sonstige Eingriffe.
- „Chromatisch“ (Reihenfolge nach Wellenlänge) und „frei gewählt“ werden explizit so benannt.
- Lokale Eingriffe (z. B. Sterne verkleinern, selektive Sättigung) werden aufgelistet,
  weil sie Helligkeitsverhältnisse verändern.
- Kein Bild wird als „echte Farben“ bezeichnet: Das Licht ist infrarot, jede Farbe ist eine Zuordnung.
