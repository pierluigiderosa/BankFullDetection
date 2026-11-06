# Rapporto esplorativo – BankFullDetection, branch `port-qgis3`

Solo lettura: non ho modificato nulla. Il branch attuale coincide **file per file** con
`C:\dev\bankfull-ref\jeremyk6-stage` (a parte `CLAUDE.md`, `.gitignore` e `.idea/`, che è ignorata da git).
Quindi tutto quello che segue vale anche per il fork di jeremyk6 così com'è.

---

## 1. File del plugin e funzione di ciascuno

| File | Ruolo |
|---|---|
| `__init__.py` | `classFactory(iface)`: punto d'ingresso QGIS, importa `BankFullDetection`. |
| `metadata.txt` | Metadati del plugin (`qgisMinimumVersion=3.0`, `version=0.1`, `experimental=True`). |
| `bankfulldetection.py` | Classe plugin: traduttore, azione su toolbar e menu, `run()` controlla che `shapely` ci sia e apre il dialogo (non modale). |
| `bankfulldetectiondialog.py` | Tutta la logica dell'interfaccia, su 3 tab. **Main tool**: `genXS` (genera le sezioni dall'asse), `genLine` (ricava la linea di thalweg dai minimi delle sezioni), `runProfile` (esegue `mainFun` su ogni sezione, costruisce il poligono di bankfull e salva lo shapefile), `writeLayer` (sceglie il file di output). **Graph**: `runProfileXS` (grafico di una sola sezione). **Validation** (aggiunto da jeremyk6): `runValidation` (N run della stessa sezione, tabella, statistiche min/max/media/dev.std, `saveCSV`). Contiene anche `mobileMean`, codice morto. |
| `ui_bankfulldetection.ui` / `ui_bankfulldetection.py` | Form Qt Designer e la sua versione compilata con pyuic5 5.11. Parametri: `nVsteps` (predefinito 100), `minVdep` (0.5), `maxMPdep` (0), `chbSlopeLim`, `nbExSbox`, step e larghezza delle sezioni (50 e 500). |
| `resources.qrc` / `resources_rc.py` | Icona compilata con pyrcc5. |
| `tools/BankElevationDetection.py` | Il core: `WTable`, `hdepth`, `mainFun` (curva della profondità idraulica A/W per `nVsteps` livelli, massimi locali, primo massimo ≥ `minVdep`), `plot_line`. |
| `tools/spline_withR.py` | `runAlg`: codice R (Scrucca 2014) eseguito via rpy2, con `smooth.spline`, CV 10-fold, regola 1-SE, Newton-Raphson sulla derivata prima e massimi dove f'' < 0. Ripete fino a 50 volte se non trova massimi. |
| `tools/XSGenerator.py` | `create_points_secs` (sezioni perpendicolari all'asse, ogni `step` m, larga `width`), `get_profile_seg`, `pointsAlongLine`/`createPointsAt` (non usate). |
| `tools/profiler.py` | `ProfilerTool`: densifica la linea alla risoluzione del raster (OGR `Segmentize`) e campiona il DEM con `provider.identify`, restituendo `[(dist, z)]`. |
| `utils/__init__.py` | `log`, `message`, `get_loaded_layers` (non usate) e `MemoryLayer`, un wrapper per i layer in memoria usato da XSGenerator. |
| `utils/geometry.py` | Funzioni vettoriali sui `QgsPoint` (`diff`, `dist`, `cosdir`, `paires`…). |
| `i18n/bankfulldetection_it.ts` | Traduzioni sorgente; nessun `.qm` compilato. |
| `bankfulldetection.pro`, `Makefile`, `help/` | Build (pyuic5/pyrcc5/lrelease, deploy in stile Unix) e documentazione Sphinx dal template. |

---

## 2. Incompatibilità con Python 3 / QGIS 3.40–3.44 (e violazioni dei vincoli di CLAUDE.md)

Legenda: 🔴 si blocca o va in errore · 🟠 risultato sbagliato o comportamento silenziosamente errato · 🟡 deprecato, fragile o viola i vincoli.

### Bloccanti per il caricamento del plugin
- 🔴 `tools/spline_withR.py:12`: `import rpy2.robjects` è a livello di modulo. La catena `__init__` → `bankfulldetection.py:30` → `bankfulldetectiondialog.py:31` → `BankElevationDetection.py:32` lo importa al caricamento: **senza rpy2 il plugin non si carica affatto**.
- 🔴 `bankfulldetectiondialog.py:75, 77`: `unicode()` in `setup_gui`. Va in `NameError` appena nel progetto c'è un layer, quindi **il dialogo non si apre**.

### Shapely 2 (QGIS 3.40/3.44 su OSGeo4W usa Shapely 2.x)
- 🔴 Iterazione diretta su un MultiPolygon (`TypeError` in Shapely 2): `BankElevationDetection.py:69, 145, 166`; `bankfulldetectiondialog.py:193`.
- 🔴 `len(MultiPolygon)`: `BankElevationDetection.py:140`.
- 🔴/🟠 `.type is 'MultiPolygon'`: `BankElevationDetection.py:66, 139, 165`; `bankfulldetectiondialog.py:191`. `.type` è deprecato in Shapely 2.0 e rimosso in 2.1. Inoltre `is` su una stringa è un `SyntaxWarning` e l'esito non è garantito: se dà False, il ramo multipoligono viene saltato in silenzio.

### API QGIS 3 / Qt5
- 🔴 `bankfulldetectiondialog.py:229-231`: in Qt5 `getSaveFileName` restituisce una tupla. `str(tupla)` produce un percorso del tipo `"('C:/x.shp', 'Shapefile (*.shp)').shp"`.
- 🔴 `utils/__init__.py:47`: `QgsGeometry.fromPolygon` è stato rimosso (al suo posto c'è `fromPolygonXY`). Il codice è morto (`add_poly` non viene mai chiamato).
- 🔴 `utils/__init__.py:5`: `QgsMessageLog.instance()` è stato rimosso. `:13`: `iface.legendInterface()` è stato rimosso. Entrambe le funzioni sono codice morto.
- 🔴 `tools/XSGenerator.py:82`: `line.asPolyline()` su un MultiLineString va in errore. In QGIS 3 gli assi caricati da shapefile o GPKG sono quasi sempre Multi, quindi `genXS` fallisce sugli input reali.
- 🟠 `tools/profiler.py:32`: accetta solo `wkbLineString`. Una sezione Multi o Z (per esempio le sezioni salvate e ricaricate) restituisce un profilo vuoto con un errore che nessuno legge (`e` viene ignorata ovunque).
- 🟠 `tools/profiler.py:27-28`: `asWkb()` restituisce un `QByteArray` passato a `ogr.CreateGeometryFromWkb`. Va verificato in QGIS; meglio `bytes(...)` o, ancora meglio, `QgsGeometry.densifyByDistance` senza passare da OGR.
- 🟠 `tools/profiler.py:50`: se il pixel è NoData, `results[1]` è `None`, il profilo contiene `None` e `Polygon` fallisce dopo. `:2`: importa `_ogr`, un modulo privato. `:15-17`: `log` senza `self` e `QgsMessageLog` non importato.
- 🟠 `utils/__init__.py:27-28`: `self.geomtype+'?crs='+...` non viene assegnato, quindi **i layer delle sezioni non hanno CRS**. Lo stesso accade con i layer creati senza CRS in `bankfulldetectiondialog.py:103` ("River line") e `:208` (poligono di bankfull); di conseguenza `:221` `vl.sourceCrs()` non è valido e lo shapefile viene salvato senza `.prj`.
- 🟠 `utils/__init__.py:35` (chiamato da `XSGenerator.py:93`): `setGeometry(QgsPoint)` funziona solo tramite l'overload `QgsAbstractGeometry`. È fragile.
- 🟠 `bankfulldetectiondialog.py:221-222`: `QgsVectorFileWriter.writeAsVectorFormat` è deprecato (si usa V3). In PyQGIS 3 restituisce una tupla, quindi `error == NoError` dà sempre False e il messaggio di successo non compare mai (da confermare sul log). `:217`: `text() == None` non è mai vero, quindi il controllo sul file di output non funziona.
- 🟡 `ui_bankfulldetection.py:9` e `resources_rc.py:9`: `from PyQt5 import …` viola il vincolo "solo `qgis.PyQt`" (sono file generati: meglio `uic.loadUiType` su `.ui`).
- 🟡 `tools/XSGenerator.py:28-29`: import assoluti `from BankFullDetection.utils import *` (violano il vincolo degli import relativi e dipendono dal nome della cartella). Inoltre `utils/geometry.py:13` definisce `sum`, che col `*` oscura il builtin.
- 🟡 `tools/XSGenerator.py:53`: `QgsField(..., QVariant.Int)` è deprecato da QGIS 3.38 (si usa `QMetaType`). `:119-120`: `float(array 1-elemento)` dà un `DeprecationWarning` con NumPy ≥ 1.25.
- 🟡 `tools/profiler.py:12`: `QgsRaster.IdentifyFormatValue` è un enum legacy (oggi `Qgis.RasterIdentifyFormat.Value`).
- 🟡 `bankfulldetection.py:42`: `QSettings().value("locale/userLocale")[0:2]` va in errore se il valore è `None` (meglio `QgsApplication.locale()`). `:49`: `qVersion() > '4.3.3'` è un confronto tra stringhe, residuo Qt4.
- 🟡 `metadata.txt:14`: `qgisMinimumVersion=3.0` (il target è 3.40). Mancano `about`, `repository` e `tracker` (obbligatori per la pubblicazione).
- 🟡 `Makefile:23` (`QGISDIR=.qgis3`) e il target di deploy usano percorsi Unix e QGIS 3.0 superati.

### Violazioni dei vincoli di CLAUDE.md (oltre a quelle già elencate)
- `descartes`: `BankElevationDetection.py:154, 167, 170`; `bankfulldetectiondialog.py:269` (importato e mai usato, ma senza descartes la tab Validation va in errore).
- File in un percorso fisso: `BankElevationDetection.py:189` apre in append `<tempdir>/test.csv` a ogni chiamata con `Graph=0` (anche in Validation) e **non lo chiude mai**.
- Logica di calcolo nel plugin: `bankfulldetectiondialog.py:186-206` seleziona il poligono bagnato e calcola i bordi; `:95-99` cerca il minimo del profilo.
- `print` di debug: `bankfulldetectiondialog.py:168, 339`; R `cat(...)` in `spline_withR.py:105, 108, 111`.

### Bug funzionali ereditati (non legati al porting, ma emergeranno nei test)
- `bankfulldetectiondialog.py:163-166`: un `except:` nudo trasforma qualunque eccezione (rpy2 mancante, Shapely 2…) in "sezione scartata". Se tutte le sezioni falliscono si ottiene un poligono vuoto senza alcun errore.
- `BankElevationDetection.py:52-53`: `mainFun` **modifica la lista del chiamante** (aggiunge i punti a maxY+1). Il dialogo, a `:171`, costruisce poi `Polygon(profileList)` sulla lista già modificata.
- `BankElevationDetection.py:177`: nel ramo d'errore `bankfullIndex` non è definito, quindi `Graph=1` va in `NameError`.
- `bankfulldetectiondialog.py:318-325`: con un valore `None` in `depts`, `round`, `mean` e `stdev` vanno in errore; `stdev` va in errore anche con un solo run.
- `bankfulldetectiondialog.py:90, 138`: il layer delle sezioni viene cercato per nome tradotto ("Sezioni"), quindi `IndexError` se manca o è stato rinominato.
- `BankElevationDetection.py:158-159`: `pyplot.figure(1)` e `pyplot.figure()` lasciano figure globali aperte dentro QGIS.

---

## 3. `mainFun`: branch attuale vs HydXS `BankFullDetection_NEW.py`

| Aspetto | Branch attuale (`tools/BankElevationDetection.py:44`) | HydXS (`BankFullDetection_NEW.py:217`) |
|---|---|---|
| Firma | `mainFun(pointList, nVsteps=100, minVdep=1, maxMPdep=0, firstSlope=False, Graph=0)` | `mainFun(pointList, nVsteps=200, minVdep=0.1, allow_multichannel=False, create_plot=False)` |
| Default | 100 livelli, minVdep 1 m (0.5 nella UI) | 200 livelli, minVdep 0.1 m |
| Multipoligoni nella curva A/W | Si tiene solo il poligono che contiene il thalweg (`bounds[1]==minY`) **solo se `dept ≥ minY+maxMPdep`**: sotto quella soglia somma tutti i canali. Viene ritagliata solo la `wetWTLine`; il perimetro bagnato resta quello dell'intera sezione (incide solo su HydRad, che non è usato). Nessun `break`: vince l'ultimo poligono che soddisfa la condizione. | Con `allow_multichannel=False` filtra **sempre** il poligono del thalweg (`.geoms`, `break`) e ritaglia sia la `wetWTLine` sia il `wetPerimeter`. Con `maxMPdep=0` (default UI) il branch attuale si comporta in modo equivalente. |
| Ricerca dei massimi | Due modalità: **firstSlope**, cioè il primo massimo sulla curva *grezza* (gradiente discreto, senza smoothing), oppure spline R. In più calcola uno `UnivariateSpline` scipy con s=0 (interpolante) **usato solo per il grafico**. | Solo spline R. |
| spline R | Restituisce `(stat, x, y, spar)`; R ritenta fino a 50 volte se non trova massimi (`stat=TRUE` significa fallimento). Newton-Raphson con max 100 iterazioni e `cat` verbosi. | Restituisce `(x, y, spar, fit)`, dove `fit` è la curva smussata usata nel grafico. Nessun ciclo di 50 tentativi: esce al primo esito. NR con max 20 iterazioni. Timeout R (`setTimeLimit` / SIGALRM). Su eccezione restituisce `[None]` e il filtro con `try/except TypeError` lo assorbe. |
| Nessun massimo ≥ minVdep | Usa `depts[-1]` (sezione quasi piena) **e restituisce `err=1`**, così il chiamante scarta la sezione. | Usa `depts[-1]` in silenzio: non c'è flag d'errore, quindi il risultato a "bordo pieno" passa come valido (lo intercetta poi il ciclo di rilancio esterno). |
| Scelta del poligono finale | Se è Multi e `dept ≥ minY+maxMPdep` prende il poligono con il thalweg, altrimenti tiene il Multi; `nchannel` viene comunque forzato a `'1'` in quel ramo. | Prende il poligono con il thalweg (correzione 7: l'originale prendeva quello di area massima); `nchannel` è il numero reale di poligoni. |
| Output | `Graph=0` → `(dept - minY, err)`, cioè la **profondità di bankfull sopra il thalweg**, e accoda una riga a `test.csv`. `Graph=1` → `FigureCanvasQTAgg`. | Tupla `(left, right, wetArea.miny, bankfull_z, nchannel, fig/"-", spar)`: **quota assoluta** e distanze delle due sponde. Niente file. |
| Grafico | 2 subplot (sezione con descartes e curva A/W rispetto alla profondità). | 2 subplot affiancati (sezione e curva A/W in orizzontale, con il `fit` R sovrapposto). |
| Logica esterna (non in mainFun, ma è parte del metodo HydXS) | Il dialogo ricalcola i bordi da `dept`; c'è una "rustine" se il bordo destro è a meno di 1 m dalla fine. | `HydXS_modelling.HydXS_perXS`: **rilancia fino a `maxrun=3` volte** se la sponda tocca il bordo della sezione (funziona solo perché i fold CV sono casuali). `HydXS_run` + `HydXS_output.calcoutputs`: N run (dispari), **moda** del bankfull, oppure **binning in 3 classi** se meno di 2/3 dei run cadono entro ±5 cm dalla moda. `xs_preprocessor.XS_UseCentre`: **taglia la sezione** attorno al punto `RivCentre` (finestra di 10 punti) per non agganciare depressioni esterne al canale. |
| Qualità del codice | Shapely 1 (`.type is`, iterazione diretta), `descartes`, `except` nudo. | Shapely 2 a metà: `.geoms` in mainFun, ma `calc_hyd_outputs:204` itera ancora direttamente. Contiene `import pdb; pdb.set_trace()` (`:248`). Anche HydXS ha il `NameError` su `bankfullIndex` nel grafico quando non c'è un massimo valido. |

**Implicazioni per il core.**
1. Il risultato di riferimento per i golden va definito come quota assoluta (stile HydXS). Il branch attuale restituisce invece una profondità relativa: `z = minY + dept`.
2. Il non-determinismo della CV 10-fold casuale è la causa sia della variabilità che jeremyk6 misura nella tab Validation, sia del "rilancia se tocca il bordo" di HydXS. Nel core Python serviranno un `seed` esplicito e, come opzione, i run multipli con moda.
3. `firstSlope` e `maxMPdep` sono estensioni di jeremyk6 che HydXS non ha: vanno mantenuti come opzioni in `options.py`.

---

## Prossimo passo proposto (da confermare, non avviato)
Fase 1: scheletro di `bankfull_core/` e `tests/`, con test che caricano `tests/data/golden/` (cartella da verificare: oggi non esiste nel repo, quindi servono i tuoi file di riferimento generati con R). Poi `hydraulics.py` (curva A/W, Shapely 2, nessuna mutazione dell'input) e `smoothing.py` (smoothing spline scipy, CV k-fold con seed, regola 1-SE, massimi tramite derivate). Il dettaglio lo propongo quando confermi.
