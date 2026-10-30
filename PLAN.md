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
- [ ] Ergebnis/Fazit in `03_reproject.ipynb` ausgefüllt
- [ ] Commit + Push

### Etappe 4 – Strecken (`04_stretch.ipynb`)
- [ ] Hintergrund abziehen, Schwarz-/Weißpunkt per Perzentil (Hintergrund in leerer Region messen, nicht übers ganze Bild)
- [ ] F212N: Hintergrund-Artefakte (Streifen, Detektor-Sprünge) beachten
- [ ] Linear vs. asinh vs. log vergleichen
- [ ] Gewählte Parameter pro Filter dokumentieren

### Etappe 5 – Farbe zuordnen (`05_color.ipynb`)
- [ ] Chromatische Zuordnung (kurz = blau, lang = rot) als Basis
- [ ] Mehr als 3 Filter: jedem Filter einen Farbton geben und additiv mischen
- [ ] Mit der offiziellen Zuordnung vergleichen (Referenz unten)

### Etappe 6 – Export und Feinschliff (`06_export.ipynb`)
- [ ] 16-bit TIFF (Archiv) + PNG/JPEG (Web)
- [ ] Bildunterschrift: Programm, Filter, Farbzuordnung, Credits

### Etappe 7 – Zweites Objekt / Generalisierung
- [ ] Ring-Nebel NGC 6720 (Programm 1558) mit derselben Pipeline
- [ ] Wiederverwendbare Funktionen in `src/` auslagern
- [ ] Optional: NIRCam + MIRI kombinieren

### Etappe 8 – Veröffentlichung
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
| – | Streckfunktion | offen (Etappe 4) | offen |
| – | Farbzuordnung | offen (Etappe 5) | offen |

## Referenz: offizielle Zuordnung NGC 3132 (NIRCam)

Laut NASA-Seite zum Bild: Rot F470N, Rot F405N, Gelb F356W, Grün F212N, Cyan F187N, Blau F090W.
Quelle: https://science.nasa.gov/asset/webb/southern-ring-nebula-nircam-compass-image

## Wissenschaftlich vs. ästhetisch – wie ich es dokumentiere

- Jedes Bild bekommt eine Tabelle: Filter → Farbe, Streckfunktion + Parameter, sonstige Eingriffe.
- „Chromatisch“ (Reihenfolge nach Wellenlänge) und „frei gewählt“ werden explizit so benannt.
- Lokale Eingriffe (z. B. Sterne verkleinern, selektive Sättigung) werden aufgelistet,
  weil sie Helligkeitsverhältnisse verändern.
- Kein Bild wird als „echte Farben“ bezeichnet: Das Licht ist infrarot, jede Farbe ist eine Zuordnung.
