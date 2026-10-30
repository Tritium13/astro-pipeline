# Planung: Astro-Pipeline

Stand: 30.10.2026 · Nebenprojekt (PhD-Bewerbungen und Bildanalyse-Projekt haben Vorrang)

## Ziel

Eigene, nachvollziehbare Python-Pipeline: öffentliche JWST-Daten aus MAST → Farbbild.
Am Ende ein öffentliches GitHub-Repo mit dokumentierten Notebooks.

## Etappen

### Etappe 0 – Setup
- [ ] conda-Umgebung `astro-pipeline` aus `environment.yml` anlegen (nicht `bia`)
- [ ] Tatsächlich installierte Versionen in `docs/worklog.md` festhalten
- [ ] Git-Repo initialisieren, erster Commit, GitHub-Remote
- [ ] Kurztest: `import astropy, astroquery, reproject` im Notebook

### Etappe 1 – Daten finden und laden (`notebooks/01_query_download.ipynb`)
- [ ] Mit `astroquery.mast.Observations` nach NGC 3132, Programm 2733, NIRCam suchen
- [ ] Produktliste auf Stufe 3 (`calib_level=3`) und `_i2d.fits` filtern
- [ ] Gesamtgröße aus der Spalte `size` berechnen, **bevor** geladen wird
- [ ] Ein Filter zuerst laden, dann den Rest

### Etappe 2 – FITS verstehen (`02_inspect_fits.ipynb`)
- [ ] Aufbau einer i2d-Datei: Extensions (SCI, ERR, WHT …), Header, Einheiten
- [ ] WCS (Pixel ↔ Himmelskoordinaten) verstehen
- [ ] Histogramm, NaN-Ränder, Hintergrund, Dynamikumfang ansehen

### Etappe 3 – Ausrichten / Registrierung (`03_reproject.ipynb`)
- [ ] Referenzraster wählen
- [ ] Alle Filter mit `reproject` auf dieses Raster bringen
- [ ] Kontrolle: Sterne in Overlays deckungsgleich?

### Etappe 4 – Strecken (`04_stretch.ipynb`)
- [ ] Hintergrund abziehen, Schwarz-/Weißpunkt per Perzentil
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
| 30.10.2026 | Erstes Objekt: NGC 3132 (Südlicher Ringnebel), nur NIRCam | Planetarischer Nebel, ein Bildfeld statt großem Mosaik; Early-Release-Daten (Programm 2733) seit 2022 öffentlich; offizielle Farbzuordnung als Vergleich veröffentlicht | vorgeschlagen |
| 30.10.2026 | Einstieg mit Stufe-3-Produkten (`_i2d.fits`) | Schon kalibriert, kombiniert und auf ein Himmelsraster gebracht; die eigene JWST-Kalibrier-Pipeline ist für den Einstieg nicht nötig | vorgeschlagen |
| 30.10.2026 | Werkzeuge: astropy, astroquery, reproject, matplotlib | Etablierte, gepflegte Pakete aus dem Astropy-Umfeld; über conda-forge verfügbar | vorgeschlagen |
| 30.10.2026 | Versionen nicht in `environment.yml` pinnen, sondern nach Installation im Worklog festhalten | Neueste kompatible Versionen ziehen, trotzdem reproduzierbar | vorgeschlagen |
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
