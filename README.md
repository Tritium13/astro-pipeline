# astro-pipeline

Eine nachvollziehbare Python-Pipeline, die öffentliche JWST-Daten aus dem
[MAST-Archiv](https://mast.stsci.edu) in Farbbilder verwandelt:
Daten finden und laden → Filter auf ein gemeinsames Raster bringen →
Helligkeit strecken → Farben zuordnen → exportieren.

Hobbyprojekt, angelehnt an Amateur-Bearbeitungen veröffentlichter JWST-Daten.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `PLAN.md` | Etappen, Fortschritt, Entscheidungen (mit Begründung) |
| `docs/worklog.md` | Setup, Terminalbefehle, Versionen |
| `notebooks/` | Ein Notebook pro Pipeline-Schritt, mit Markdown-Zellen (was / warum / Ergebnis) |
| `environment.yml` | conda-Umgebung `astro-pipeline` |
| `data/` | lokale FITS-Dateien (nicht im Repo) |

## Setup

```bash
conda env create -f environment.yml
conda activate astro-pipeline
jupyter lab
```

## Datennachweis

Die Bilder basieren auf Beobachtungen des NASA/ESA/CSA James Webb Space Telescope,
abgerufen über MAST. Programm-IDs und Filter stehen jeweils im Notebook und in `PLAN.md`.
Die Farbgebung ist eine eigene Bearbeitung und kein offizielles Produkt.
