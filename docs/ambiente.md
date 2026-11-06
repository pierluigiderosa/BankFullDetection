# Ambiente di sviluppo

Verificato il 06/11/2026 dalla Python Console di PyCharm.

## Interprete
`C:\Program Files\QGIS 3.34.7\apps\Python312\python.exe` (Python 3.12.3, incluso in QGIS 3.34.7)

Nessun virtualenv. Strumenti di sviluppo (pytest, ruff) installati con `pip install --user`.

## Librerie disponibili in QGIS 3.34.7
| Libreria | Versione | Note per il porting |
|---|---|---|
| numpy | 1.26.4 | |
| scipy | 1.13.0 | `scipy.interpolate.make_smoothing_spline` disponibile (da 1.10) |
| shapely | 2.0.3 | Usare `.geoms` e `geom_type`; niente iterazione diretta sui Multi |
| matplotlib | 3.8.4 | Backend Qt5 (`backend_qt5agg`) |
| descartes | assente | Non usarlo: disegnare con `matplotlib.patches.Polygon` |
| rpy2 | assente | Non usarlo: R va eliminato |

## Note
- `qgis.core` non è importabile dalla console di PyCharm: è previsto. Il core e i suoi test
  non devono importare `qgis`. Il plugin si prova dentro QGIS con Plugin Reloader.
- Comando per i test: `& "C:\Program Files\QGIS 3.34.7\apps\Python312\python.exe" -m pytest -q`
