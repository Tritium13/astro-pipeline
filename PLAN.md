# Planung: Astro-Pipeline

Stand: 31.10.2026 · Nebenprojekt (PhD-Bewerbungen und Bildanalyse-Projekt haben Vorrang)

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
- [x] Ergebnis/Fazit in `06_export.ipynb` ausgefüllt
- [x] Commit + Push

### Etappe 7 – Zweites Objekt / Generalisierung
- [x] Ring-Nebel NGC 6720 (Programm 1558, NIRCam F162M/F212N/F300M/F335M) mit dem Paket (`08_ngc6720.ipynb`), exportiert (Variante C, Querformat 4:3, 1,64′ × 1,23′)
- [x] Streifenkorrektur: `08a` (leerer Himmel, 512-px-Abschnitte) → `08b` (lokales Hintergrundmodell, 16-px-Zellen) – im Nebel deutlich wirksamer; Reststreifen und Detektor-Blöcke bleiben
- [x] Paket erweitert: `clean` (destripe, destripe_local), `mast.download` überspringt vorhandene Dateien, `export.largest_rect`
- [x] Ergebnis/Fazit in `08`, `08a`, `08b` ausgefüllt
- [x] Commit + Push
- [x] Wiederverwendbare Funktionen in `src/astropipe/` ausgelagert (bands, mast, registration, stretch, color, export), `pip install -e .`
- [x] Regressionstest NGC 3132 (`07_regression_ngc3132.ipynb`): alles bitgenau, Farbe 1,5e-5 (gerundete RGB in JSON)
- [x] Farben künftig als Farbwinkel + Sättigung speichern (exakt reproduzierbar) – ab NGC 6720 umgesetzt
- [x] Optional: NIRCam + MIRI kombinieren (NGC 6720): Bestandsaufnahme `09_miri_ngc6720.ipynb` (Hauptmosaik o001, 9 Filter, 0,43 GB), Kombination `09a_combine_nircam_miri_ngc6720.ipynb`
- [x] MIRI ↔ NIRCam: Versatz ≈ 1,25 px (≈ 78 mas) an Sternen gemessen (F560W/F770W) und korrigiert → 0,17–0,26 px (`registration.star_shifts`, `apply_shift`)
- [x] Drei Versionen verglichen: W1 (wie Wesson et al. Abb. 3), W2 Ionisationsschichten + LRGB (F335M), W2s gleiche Schärfe (Referenz); W2 + W2s exportiert
- [x] MIRI-Verschiebung in `params/ngc6720_nircam_miri.json` aufnehmen (dy +1,04, dx −0,67 px angewendet)
- [x] Ergebnis/Fazit in `09` und `09a` ausgefüllt
- [x] Commit + Push
- [ ] Ideen NGC 3132: Variante D (Breitband fast weiß → weiße Sterne), größerer/anderer Ausschnitt für die äußeren Schalen, Maßstab + Kompass

### Etappe 8 – Veröffentlichung
- [ ] Entscheiden: Repo vollständig auf Englisch (README, Markdown-Zellen, Fazits)?
- [ ] README mit Beispielbildern, Lizenz, Datennachweis
- [ ] Repo öffentlich schalten

### Etappe 11 (Idee) – Planeten
- MAST-Bestand NIRCam, Stufe 3, öffentlich (31.10.2026): Jupiter (1022, 1373, 9022), Mars (1415, 2787), Neptun (2739, 1 Beob., F140M/F210M/F300M/F460M), Uranus (2739, 2768, 6379, 8975, 9482); Saturn unter diesem Namen nicht gefunden (andere Bezeichnung oder nur andere Instrumente? prüfen)
- Erster Kandidat: **Neptun, Programm 2739** (eine Beobachtung, 4 Filter, überschaubar); danach Uranus 6379 (8 Breitbandfilter)
- Besonderheiten: bewegtes Ziel (Registrierung am Planeten statt an Sternen), extrem hell vs. schwache Ringe/Monde, Subarrays (`sub160/320/640`), Mosaike bei Jupiter

### Etappe 10 (Idee, optional) – Korrektur an den Einzelaufnahmen
- [ ] 1/f-Streifen pro Einzelaufnahme (Stufe 2, `_cal.fits`) korrigieren und das Mosaik selbst mit der `jwst`-Pipeline neu zusammensetzen; vorhandene Werkzeuge (Pipeline-Schritt, Community-Skripte) erst recherchieren und prüfen
- Grund: im i2d liegen die Streifenmuster der versetzten Aufnahmen verschoben übereinander → mit Zeilenprofilen nicht vollständig entfernbar (wie Festmuster-Rauschen nach dem Stitchen eines Tile-Scans)
- Aufwand: viele Einzeldateien, Pipeline + Referenzdateien, deutlich mehr Rechenzeit (RAM 16 GB beachten)

### Etappe 9 – Automatisierung / „Entdecker-Modus“ (Idee, nach Etappe 7/8)
Ziel: beliebige passende JWST-Bilddaten mit derselben Pipeline per Skript verarbeiten.
- [x] Stufe 1: Generalisierung aus Etappe 7 (Funktionen in `src/`, am Ring-Nebel getestet)
- [x] Stufe 2: Skript + Konfigurationsdatei pro Objekt (Programm, Filter, Farbvariante A/B/C, Parameter) → jedes Bild per Befehl reproduzierbar: `python -m astropipe.run configs/<name>.toml`; `configs/ngc3132.toml`, `configs/ngc6720.toml`; Regressionstest `10_run_configs.ipynb`: Streckung und Farbe **bitgenau** wie in den Notebooks, Ausschnitte identisch
- [ ] Stufe 2b (optional): NIRCam + MIRI in der Konfiguration (Instrumentenversatz, LRGB, Schärfe angleichen)
- [x] Stufe 3: Entdecker-Modus (`python -m astropipe.explore`, `11_explore.ipynb`): zufälliges 30-Tage-Fenster, Gruppierung nach Beobachtung, ≥ 3 Filter, ≤ 3 GB, Standard-Konfiguration in `configs/explore/`, Lauf + Kurzbericht mit Warnhinweisen. Erster Fund: Feld im Programm 8277 (NGC 1527, Halo-Survey), tiefes Feld mit vielen Hintergrundgalaxien
- [x] Dabei gefunden und behoben: (1) Ausschnitt scheitert bei Feldern ohne zentrales Objekt → `center = "auto"` mit Rückfall auf die innerste Stelle; (2) **Fehler seit Etappe 4:** NaN-Lücken aus defekten Pixeln wurden wie gesättigte Kerne weiß gefüllt → `stretch.classify_holes` (lokaler Kontrast innerer Ring vs. äußerer Ring); defekte Pixel bekommen den Umgebungsmedian
- [ ] Notebook-Ergebnisse von gestern enthalten die weißen Kleckse → als Referenz gelten ab jetzt die Skript-Ergebnisse (`output/runs/`); `09a` (NIRCam + MIRI) bei Gelegenheit neu laufen lassen
- [ ] Explorer: einzelner blauer Pixel im NGC-1527-Feld prüfen (Artefakt oder Objekt?)
- [x] Übersichtsbild pro Lauf (`*_overview.jpg`: ganzes Feld, Rahmen = Ausschnitt, rotes Kreuz = Helligkeitsschwerpunkt); Bericht verlinkt es
- [x] Cache-Fehler behoben: Registrierung und Streifenkorrektur nutzten Zwischenergebnisse nur nach Dateinamen wieder → jetzt Prüfung von Quelle (`SRCFILE`), Zeitstempel und Einstellungen (`ASTCLEAN`)
- [x] Seed reproduzierbar (Zeitfenster bis Monatsanfang, Kandidaten vor dem Mischen sortiert)
- [x] Tiefes leeres Feld (J0217-0208, Programm 1657): breite Bänder + Stufen zwischen Aufnahmen → `clean.method = "sky"`, `smooth = 0`, `background2d_cell = 128`; deutlich besser, Reste in F150W/F200W bleiben (**bekannte Einschränkung**, s. Entscheidungen)
- [x] `clean.method = "auto"` an zwei Feldern geprüft: leer (J0217, Struktur 0,6–1,0 σ) vs. gefüllt (NGC 5643, 16–39 σ); Streifen bei gefüllten Feldern am lokalen Rest gemessen
- [ ] Schwellen (Struktur 3 σ, Streifen 0,15) an weiteren Feldern beobachten
- [x] NGC 5643 (Programm 1685): zwei Beobachtungen (o011 + o012, 15 Tage Abstand, Module vertauscht) kombiniert → Lückenkreuz bis auf einen schmalen Keil rechts vom Kern gefüllt; Ausschnitt von Hand 2100 px ≈ 2,2′ um den Kern (`configs/ngc5643.toml`)
- [ ] NGC 5643: schwarzer Keil und kleine Rechtecke am Kern – so lassen (ehrlich) oder Ausschnitt anpassen? Ergebnis/Bildunterschrift prüfen
- Vorab-Filter: nur Bildgebung, ≥ 3 Filter, öffentlich, Stufe 3, überlappende Bildfelder, Größengrenze (RAM 16 GB)
- Erkenntnisse aus NGC 6720: Box-Suche soll Boxen mit negativem Score automatisch verwerfen (Detektor-Artefakte); wenn das Objekt das Feld füllt, gibt es keinen leeren Himmel → Hintergrund relativ, Streifenkorrektur mit lokalem Modell; Detektor-Blöcke (2D-Helligkeitsstufen) wären der nächste Schritt; Notebooks vor dem Ergebnis immer per „Restart & Run All“ prüfen (Zustandsfehler bei `boxes`)
- Bekannte Fallstricke: Mosaike mit Detektorlücken (`binary_fill_holes` würde sie weiß füllen → Lückengröße begrenzen), Spektroskopie/Koronografie/Zeitreihen/bewegte Ziele ausschließen, große Datenmengen
- Analogie: wie bei der Mikroskopie braucht jede Aufnahmeart ihre eigene Verarbeitung (ein Z-Stapel ist kein 2D-Bild) → Pipeline erkennt und überspringt Ungeeignetes, statt alles gleich zu behandeln

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
| 31.10.2026 | Pipeline als Paket `src/astropipe/` (editable install); Notebooks rufen Funktionen auf | Wiederverwendbar für neue Objekte (Etappe 7/9); per Regressionstest gegen NGC 3132 validiert. Sättigungslücken nur bis 2000 px füllen (Detektorlücken in Mosaiken nicht weiß) | angenommen |
| 31.10.2026 | NGC 6720: Streifenkorrektur aller 4 Filter vor der Registrierung mit `clean.destripe_local` (16-px-Medianzellen, 512-px-Abschnitte) | Kurze Belichtung (483 s) → deutliche Ausleser-Streifen; Nebel füllt das Feld, kein leerer Himmel → lokales Hintergrundmodell statt Himmelspixel. Differenzbilder zeigen nur Streifen. Näherung; saubere Korrektur wäre in den Einzelaufnahmen | angenommen |
| 31.10.2026 | NGC 6720: Himmelsboxen mit negativem Score verwerfen (4 von 6 genutzt); Hintergrund ist relativ (Halo füllt das Feld) | Negative Scores = Detektorbänder, kein leerer Himmel | angenommen |
| 31.10.2026 | NGC 6720 Farbe: C – physikalisch gruppiert (F162M 210° blau = ionisiertes Gas; F212N 15° orange-rot = H₂; F300M 60° gelb, F335M 40° gold = gemischt, F335M mit PAH), Gewichte 1 | Filterinhalte nach Wesson et al. 2024, Tab. 1 (arXiv:2308.09027); A und B (beide chromatisch) fast identisch und blasser | angenommen |
| 31.10.2026 | NGC 6720 Ausschnitt: Querformat 4:3 (`largest_rect`) | Gültiger Bereich ist eine Raute (≈45° gedreht); Ring liegt quer → Querformat zeigt mehr vom Ring als ein Quadrat (1,64′ × 1,23′ statt 1,31′ × 1,31′) | angenommen |
| 31.10.2026 | NIRCam + MIRI: MIRI auf das NIRCam-Raster (0,063″) **hochgerechnet**, Versatz zwischen den Instrumenten an Sternen korrigiert | Feine Struktur von NIRCam bleibt erhalten; hochrechnen erzeugt keine neuen Details – ästhetische Entscheidung, offen dokumentiert. Versatz bei F560W/F770W gleich gerichtet (dy −1,05, dx +0,66 px) → echter Instrumentenversatz; F1500W-Messung zu unsicher, gemeinsames Raster → gleiche Verschiebung | angenommen |
| 31.10.2026 | NIRCam + MIRI Farbe: **W2 – Ionisationsschichten** (F1500W [Ne III] 230° blau, F162M 190° hellblau, F212N H₂ 25° orange, F770W 0° rot), 50 % Helligkeit aus F335M (LRGB); dazu **W2s** als Referenz mit gleicher Schärfe (Gauß auf FWHM von F1500W ≈ 0,49″) | W2 zeigt die Schichtung von hoch ionisiert (innen) bis molekular (außen) am deutlichsten; W2s belegt, dass die Farbverteilung auch bei ehrlicher Auflösung gleich ist und die Schärfe aus NIRCam stammt. Filterinhalte nach Wesson et al. 2024; NIRCam-FWHM Näherungen | angenommen |
| 31.10.2026 | Konfiguration als TOML (`configs/*.toml`), Ausführung `python -m astropipe.run`; Zwischenergebnisse in `data/<name>_run/`, Bilder in `output/runs/`, Protokoll `params/<name>_run.json` | TOML ist ab Python 3.11 eingebaut (`tomllib`), gut lesbar, kommentierbar; getrennte Ordner lassen Notebook-Ergebnisse unangetastet und vergleichbar | angenommen |
| 31.10.2026 | Lücken im Bild nach **lokalem Kontrast** einstufen: gesättigt ⇔ innerer Ring − äußerer Ring > 20 σ und innerer Ring > 1,5 × äußerer Ring; sonst defekter Pixel → Umgebungsmedian | Alte Füllung (alles weiß) erzeugte helle Kleckse aus defekten Pixeln (NGC 3132: 6–11 pro Filter, 158–245 px). Ein globales Helligkeitskriterium scheitert in hellen Nebeln. Prüfung: Unterschiede zur alten Version nur an den defekten Pixeln (max. 1,0), sonst ≤ 1,5·10⁻² (verschobener Weißpunkt) | angenommen |
| 31.10.2026 | Referenz für Regressionstests ab jetzt: Skript-Ergebnisse nach der Lückenkorrektur | Die Notebook-Ergebnisse vom 30./31.10. enthalten den Lückenfehler | angenommen |
| 31.10.2026 | Leere, tiefe Felder: Zeilenkorrektur am leeren Himmel **ohne Hochpass** (`smooth = 0`) + 2-D-Hintergrund (128-px-Zellen, Quellen ausgeblendet); Explorer wählt per `clean.method = "auto"` (großräumige Struktur < 3 σ → leeres Feld; Streifen/Rauschen > 0,15 → korrigieren; erstes Kriterium „Himmelsanteil > 50 %“ scheiterte am Testfeld mit 0,43–0,51) | `local` (16-px-Modell) und `smooth = 51` behalten Bänder breiter als ~16–25 Zeilen. 2-D-Hintergrund entfernt auch echte Strukturen > ~8″ → nur für Felder mit kompakten Quellen, nicht für Nebel. Schwelle vorläufig | angenommen |
| 31.10.2026 | Reststreifen in F150W/F200W bei J0217-0208 als bekannte Einschränkung akzeptieren, nicht kosmetisch verstecken | Saubere Lösung nur an den Einzelaufnahmen (Etappe 10). Negatives `black_k` würde schwache Galaxien mit verstecken | angenommen |
| 31.10.2026 | Mehrere Beobachtungen pro Filter (`data.obs` als Liste): einzeln korrigieren und reprojizieren, Hintergrund der weiteren Beobachtung per Median-Differenz im Überlapp angleichen, dann mitteln | Füllt Detektorlücken (NGC 5643); Hintergrundunterschiede zwischen den Tagen klein (≈ 0,01 MJy/sr), Sternversatz 0,1 px. Cepheiden-Helligkeitsänderung zwischen den Tagen für ein Farbbild vernachlässigt | angenommen |
| 31.10.2026 | Ausschnitt von Hand möglich (`export.center = [y, x]`, `size_px`); verbleibende Lücken bleiben schwarz | Automatik weicht Lücken aus und verfehlt dann das Motiv; Lücken nicht künstlich füllen | angenommen |
| – | Repo-Sprache: komplett Englisch? | am Ende (Etappe 8) entscheiden | offen |
| 30.10.2026 | Gesättigte Sternkerne: NaN-Lücken innerhalb des Bildes (`binary_fill_holes`) mit dem Maximalwert des Filters füllen | Pipeline setzt gesättigte Pixel auf NaN; ohne Füllung würden Sterne über die gemeinsame Gültigkeitsmaske in allen Filtern schwarz. Kosmetischer Eingriff (≈160–510 px pro Filter) | ersetzt am 31.10.2026 (Einstufung nach lokalem Kontrast, s. o.) |
| 30.10.2026 | Farbzuordnung: **C – physikalisch gruppiert** (F187N 200°, F405N 225° → Blau/Cyan, ionisiertes Gas; F212N 20°, F470N 0° → Orange/Rot, molekularer Wasserstoff; F090W 55°, F356W 40° → Gelb, Breitband/Sterne), alle Gewichte 1 | Größter Kontrast zwischen innerer Blase und äußeren Schalen: jede physikalische Komponente bleibt in einer Farbfamilie, statt sich wie bei A/B aus Gegenfarben zu blassen Tönen zu mischen. Sieht dem veröffentlichten NASA-Bild am ähnlichsten. **Frei gewählt, nicht chromatisch**; bekannte Folge: Sterne gelbstichig. A und B bleiben in `params/ngc3132_color.json` dokumentiert | angenommen |

## Referenz: offizielle Zuordnung NGC 3132 (NIRCam)

Laut NASA-Seite zum Bild: Rot F470N, Rot F405N, Gelb F356W, Grün F212N, Cyan F187N, Blau F090W.
Quelle: https://science.nasa.gov/asset/webb/southern-ring-nebula-nircam-compass-image

## Referenz: offizielle Zuordnung NGC 6720 (NIRCam)

Laut NASA-Seite zum Bild: Blau F162M, Cyan F212N, Grün F300M, Rot F335M (chromatisch), Programm 1558 (M. Barlow).
Quelle: https://science.nasa.gov/asset/webb/ring-nebula-nircam-image/

## Wissenschaftlich vs. ästhetisch – wie ich es dokumentiere

- Jedes Bild bekommt eine Tabelle: Filter → Farbe, Streckfunktion + Parameter, sonstige Eingriffe.
- „Chromatisch“ (Reihenfolge nach Wellenlänge) und „frei gewählt“ werden explizit so benannt.
- Lokale Eingriffe (z. B. Sterne verkleinern, selektive Sättigung) werden aufgelistet,
  weil sie Helligkeitsverhältnisse verändern.
- Kein Bild wird als „echte Farben“ bezeichnet: Das Licht ist infrarot, jede Farbe ist eine Zuordnung.
