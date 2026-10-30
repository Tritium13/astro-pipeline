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
