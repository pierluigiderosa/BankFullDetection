# BankFullDetection – porting a QGIS 3 (3.34 – 3.44)

## Contesto
Plugin QGIS per l'individuazione automatica del livello di bankfull da sezioni trasversali su DTM
(metodo della massima profondità idraulica A/W, De Rosa et al. 2019, IJGI 8(11):480).
Il codice originale (branch `master`) è Python 2.7 / QGIS 2.18 / PyQt4 e usa R via rpy2
(`tools/spline_withR.py`) per lo smoothing spline con CV 10-fold e regola 1-SE.

Il branch di lavoro parte da `jeremyk6/stage` (porting QGIS 3 incompleto + migliorie UI di jeremyk6).

Il repository è clonato direttamente nella cartella plugin del profilo QGIS 3: QGIS lo carica da qui.
Non creare MAI altre cartelle di plugin accanto a questa.

Riferimenti esterni (SOLO lettura, non modificarli, non copiarli alla cieca):
- `C:\dev\bankfull-ref\original-master` – il mio codice originale (Python 2.7 / QGIS 2.18), per confronto.
- `C:\dev\bankfull-ref\jeremyk6-stage` – fork di jeremyk6, branch `stage`, così com'era prima delle mie modifiche.
- `C:\dev\bankfull-ref\HydXS` – Garber & Thompson 2023 (Water Resources Research 2024, doi 10.1029/2023WR035269):
  versione Python 3 standalone del core con migliorie (multipoligoni, trimming con asse fiume,
  ricalcolo se il bankfull tocca il bordo, run multipli con moda/binning). Usa ANCORA R/rpy2.
  Licenza Apache-2.0: reimplementare le idee, citare la fonte, non incollare blocchi di codice.

## Obiettivo
1. Libreria core in Python puro, SENZA dipendenze da QGIS e SENZA R: `bankfull_core/`.
2. Plugin QGIS sottile che usa il core: dialogo + (in seguito) algoritmo Processing.
3. Target: QGIS 3.34 (minimo, è la versione di sviluppo) fino a 3.44 (Qt5, Python 3.12). QGIS 4 non è un obiettivo per ora.

## Vincoli tassativi
- Nessun `rpy2`, nessuna chiamata a R/Rscript. Lo smoothing va fatto con numpy/scipy.
- Qt solo tramite `qgis.PyQt` (mai `PyQt5` importato direttamente).
- Shapely 2: usare `.geoms` per le multi-geometrie, `geom_type ==` (mai `.type is`).
- Niente `descartes`: disegnare i poligoni con `matplotlib.patches.Polygon`.
- Niente `unicode()`, `cmp()`, `print` statement, `iteritems`; solo import relativi nel plugin.
- Il core non importa mai `qgis.*`. Il plugin non contiene logica di calcolo.
- Non scrivere file in percorsi fissi (`/tmp/...`): usare `tempfile` o output scelti dall'utente.
- Niente `import pdb` o codice di debug lasciato nel sorgente.

## Struttura attesa
```
bankfull_core/
  hydraulics.py      # profondità idraulica, poligoni bagnati, gestione multipoligoni
  smoothing.py       # spline + CV k-fold + regola 1-SE + ricerca massimi (sostituisce spline_withR)
  detection.py       # mainFun riscritta: input pointList [(dist, z)], output dataclass risultato
  options.py         # parametri (min hyd depth, nVsteps, opzioni stile HydXS on/off)
tests/
  data/              # sezioni di test + output di riferimento ("golden") generati con la versione R
  test_*.py
plugin/  (o radice del plugin)
  __init__.py, bankfulldetection.py, dialog, ui, resources, metadata.txt
```

## Modo di lavorare
- Prima di ogni fase: proponi un piano e attendi conferma. Una fase = un branch o una serie di commit piccoli.
- Test prima del codice per il core (`pytest`). Ogni modifica al core deve lasciare i test verdi.
- Il confronto con la versione R si fa sui file in `tests/data/golden/`: non rigenerarli, non modificarli.
- Tolleranza di accettazione iniziale sul livello di bankfull: |Δz| ≤ 0.05 m sulla maggior parte
  delle sezioni; segnala sempre le sezioni fuori tolleranza invece di forzare i parametri.
- Non puoi avviare QGIS: per il plugin limita la verifica a import e lint;
  il test in QGIS lo faccio io e ti riporto gli errori del log.
- Commenti e docstring in inglese, messaggi a me in italiano.

## Ambiente
- Interprete: il Python incluso in QGIS 3 (percorso esatto e versioni delle librerie in `docs/ambiente.md`).
  Stesse librerie che userà il plugin: numpy, scipy, shapely, matplotlib, PyQGIS.
- Non installare pacchetti nel Python di QGIS senza chiedermelo.
- Il core deve funzionare con le versioni di libreria presenti in QGIS: non usare funzioni più recenti
  di quelle disponibili (controlla `docs/ambiente.md`).
- Il core e i suoi test non importano `qgis`: devono girare con il solo interprete, senza avviare QGIS.

## Comandi
- Usa sempre l'interprete di QGIS indicato in `docs/ambiente.md` (non il `python` di sistema).
- Test core: `<python di QGIS> -m pytest -q`
- Lint: `<python di QGIS> -m ruff check .`
