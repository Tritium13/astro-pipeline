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
| python | |
| astropy | |
| astroquery | |
| reproject | |
| numpy | |

### Git

```bash
git init
git add .
git commit -m "Initial project skeleton"
# GitHub-Repo anlegen, dann:
git remote add origin git@github.com:<user>/astro-pipeline.git
git push -u origin main
```

### Notizen
- `data/` ist in `.gitignore` – FITS-Dateien nie committen.
