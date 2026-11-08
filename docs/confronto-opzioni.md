# Confronto delle opzioni del metodo con le stime esperte

Generato da `analysis/compare_expert.py`; dati per riga in `docs/confronto-opzioni.csv`.

**Le sezioni sono solo 8: i risultati sono indicativi**, non una calibrazione. Le stime esperte (`tests/data/expert/expert_bankfull.csv`) sono valutazioni visive dell'autore.

## Definizioni

- Combinazioni: multichannel (original, thalweg) × selection (min_cv, one_se) × min_hyd_depth (0.2, 1.0, 2.0, 3.0) × criterio (first, highest, prominent) = 48. Tutti gli altri parametri ai default di `BankfullOptions`.
- Fold CV casuali numpy, seed 0–10 (11 run): i fold differiscono da quelli di R usati per i dati golden. Per ogni combinazione: mediana, minimo e massimo del livello sui seed che danno un bankfull.
- Criteri, tra i massimi della curva lisciata con A/W ≥ min_hyd_depth: **first** = il più basso (quello del core); **highest** = A/W lisciato più alto; **prominent** = prominenza più alta, con prominenza = A/W del massimo − il più alto dei due minimi adiacenti della curva lisciata. Il minimo adiacente di ciascun lato è il minimo della spline fino al massimo vicino o, se non c'è, fino all'estremo della curva (al bordo conta quindi il valore di fine curva se la curva è monotona).
- Errore = livello mediano − stima esperta (positivo = metodo più alto). Errore medio, errore medio assoluto e RMSE sono calcolati sulle sezioni con bankfull (colonna n).
- *Senza bankfull*: nessun seed dà un livello. *Seed parziali*: solo alcuni seed lo danno (la mediana è sui seed che lo danno). *Ampiezza media seed*: media di max − min.

## Riepilogo rispetto a z_expert_low

| # | multichannel / selection / min_hyd_depth / criterio | n | errore medio | errore medio ass. | RMSE | entro 0.25 m | entro 0.50 m | senza bankfull | seed parziali | ampiezza media seed |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | thalweg / min_cv / 1.0 / first | 8 | -0.256 | 0.461 | 0.892 | 5 | 7 | 0 | 0 | 1.732 |
| 2 | thalweg / min_cv / 2.0 / first | 8 | -0.256 | 0.461 | 0.892 | 5 | 7 | 0 | 0 | 1.732 |
| 3 | thalweg / min_cv / 0.2 / first | 8 | -0.638 | 0.784 | 1.334 | 4 | 6 | 0 | 0 | 2.113 |
| 4 | original / min_cv / 1.0 / first | 8 | -0.633 | 1.168 | 1.651 | 3 | 4 | 0 | 0 | 0.022 |
| 5 | original / min_cv / 2.0 / first | 8 | -0.633 | 1.168 | 1.651 | 3 | 4 | 0 | 0 | 0.022 |
| 6 | thalweg / min_cv / 3.0 / first | 8 | 0.503 | 1.221 | 2.000 | 3 | 5 | 0 | 0 | 0.728 |
| 7 | original / min_cv / 3.0 / first | 8 | -0.464 | 1.336 | 1.718 | 2 | 3 | 0 | 0 | 0.021 |
| 8 | original / one_se / 1.0 / first | 8 | -0.328 | 1.542 | 1.883 | 0 | 2 | 0 | 0 | 0.059 |
| 9 | original / one_se / 2.0 / first | 8 | -0.328 | 1.542 | 1.883 | 0 | 2 | 0 | 0 | 0.059 |
| 10 | original / one_se / 3.0 / first | 8 | -0.328 | 1.542 | 1.883 | 0 | 2 | 0 | 0 | 0.059 |
| 11 | original / one_se / 0.2 / first | 8 | -0.330 | 1.544 | 1.886 | 0 | 2 | 0 | 0 | 0.697 |
| 12 | original / min_cv / 0.2 / highest | 8 | -0.070 | 1.673 | 1.936 | 0 | 1 | 0 | 0 | 0.021 |
| 13 | original / min_cv / 1.0 / highest | 8 | -0.070 | 1.673 | 1.936 | 0 | 1 | 0 | 0 | 0.021 |
| 14 | original / min_cv / 2.0 / highest | 8 | -0.070 | 1.673 | 1.936 | 0 | 1 | 0 | 0 | 0.021 |
| 15 | original / min_cv / 3.0 / highest | 8 | -0.070 | 1.673 | 1.936 | 0 | 1 | 0 | 0 | 0.021 |
| 16 | original / min_cv / 3.0 / prominent | 8 | -0.070 | 1.673 | 1.936 | 0 | 1 | 0 | 0 | 0.021 |
| 17 | original / one_se / 0.2 / highest | 8 | -0.124 | 1.683 | 1.943 | 0 | 1 | 0 | 0 | 0.061 |
| 18 | original / one_se / 0.2 / prominent | 8 | -0.124 | 1.683 | 1.943 | 0 | 1 | 0 | 0 | 0.061 |
| 19 | original / one_se / 1.0 / highest | 8 | -0.124 | 1.683 | 1.943 | 0 | 1 | 0 | 0 | 0.061 |
| 20 | original / one_se / 1.0 / prominent | 8 | -0.124 | 1.683 | 1.943 | 0 | 1 | 0 | 0 | 0.061 |
| 21 | original / one_se / 2.0 / highest | 8 | -0.124 | 1.683 | 1.943 | 0 | 1 | 0 | 0 | 0.061 |
| 22 | original / one_se / 2.0 / prominent | 8 | -0.124 | 1.683 | 1.943 | 0 | 1 | 0 | 0 | 0.061 |
| 23 | original / one_se / 3.0 / highest | 8 | -0.124 | 1.683 | 1.943 | 0 | 1 | 0 | 0 | 0.061 |
| 24 | original / one_se / 3.0 / prominent | 8 | -0.124 | 1.683 | 1.943 | 0 | 1 | 0 | 0 | 0.061 |
| 25 | original / min_cv / 0.2 / first | 8 | -1.301 | 1.836 | 3.190 | 3 | 4 | 0 | 0 | 0.022 |
| 26 | original / min_cv / 0.2 / prominent | 8 | 0.169 | 1.912 | 2.317 | 0 | 1 | 0 | 0 | 0.225 |
| 27 | original / min_cv / 1.0 / prominent | 8 | 0.169 | 1.912 | 2.317 | 0 | 1 | 0 | 0 | 0.225 |
| 28 | original / min_cv / 2.0 / prominent | 8 | 0.169 | 1.912 | 2.317 | 0 | 1 | 0 | 0 | 0.225 |
| 29 | thalweg / one_se / 0.2 / first | 8 | 1.335 | 2.127 | 2.748 | 1 | 3 | 0 | 0 | 1.127 |
| 30 | thalweg / one_se / 1.0 / first | 8 | 1.335 | 2.127 | 2.748 | 1 | 3 | 0 | 0 | 1.127 |
| 31 | thalweg / one_se / 2.0 / first | 8 | 1.335 | 2.127 | 2.748 | 1 | 3 | 0 | 0 | 1.127 |
| 32 | thalweg / one_se / 3.0 / first | 8 | 1.335 | 2.127 | 2.748 | 1 | 3 | 0 | 0 | 1.127 |
| 33 | thalweg / one_se / 0.2 / highest | 8 | 2.088 | 2.322 | 2.967 | 1 | 3 | 0 | 0 | 0.285 |
| 34 | thalweg / one_se / 0.2 / prominent | 8 | 2.088 | 2.322 | 2.967 | 1 | 3 | 0 | 0 | 0.285 |
| 35 | thalweg / one_se / 1.0 / highest | 8 | 2.088 | 2.322 | 2.967 | 1 | 3 | 0 | 0 | 0.285 |
| 36 | thalweg / one_se / 1.0 / prominent | 8 | 2.088 | 2.322 | 2.967 | 1 | 3 | 0 | 0 | 0.285 |
| 37 | thalweg / one_se / 2.0 / highest | 8 | 2.088 | 2.322 | 2.967 | 1 | 3 | 0 | 0 | 0.285 |
| 38 | thalweg / one_se / 2.0 / prominent | 8 | 2.088 | 2.322 | 2.967 | 1 | 3 | 0 | 0 | 0.285 |
| 39 | thalweg / one_se / 3.0 / highest | 8 | 2.088 | 2.322 | 2.967 | 1 | 3 | 0 | 0 | 0.285 |
| 40 | thalweg / one_se / 3.0 / prominent | 8 | 2.088 | 2.322 | 2.967 | 1 | 3 | 0 | 0 | 0.285 |
| 41 | thalweg / min_cv / 0.2 / highest | 8 | 2.256 | 2.365 | 3.078 | 2 | 3 | 0 | 0 | 0.254 |
| 42 | thalweg / min_cv / 1.0 / highest | 8 | 2.256 | 2.365 | 3.078 | 2 | 3 | 0 | 0 | 0.254 |
| 43 | thalweg / min_cv / 2.0 / highest | 8 | 2.256 | 2.365 | 3.078 | 2 | 3 | 0 | 0 | 0.254 |
| 44 | thalweg / min_cv / 3.0 / highest | 8 | 2.256 | 2.365 | 3.078 | 2 | 3 | 0 | 0 | 0.254 |
| 45 | thalweg / min_cv / 0.2 / prominent | 8 | 2.622 | 2.731 | 3.733 | 2 | 3 | 0 | 0 | 0.779 |
| 46 | thalweg / min_cv / 1.0 / prominent | 8 | 2.622 | 2.731 | 3.733 | 2 | 3 | 0 | 0 | 0.779 |
| 47 | thalweg / min_cv / 2.0 / prominent | 8 | 2.622 | 2.731 | 3.733 | 2 | 3 | 0 | 0 | 0.779 |
| 48 | thalweg / min_cv / 3.0 / prominent | 8 | 2.622 | 2.731 | 3.733 | 2 | 3 | 0 | 0 | 0.779 |

## Riepilogo rispetto a z_expert_high

| # | multichannel / selection / min_hyd_depth / criterio | n | errore medio | errore medio ass. | RMSE | entro 0.25 m | entro 0.50 m | senza bankfull | seed parziali | ampiezza media seed |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | thalweg / min_cv / 0.2 / highest | 8 | -0.508 | 0.508 | 0.981 | 5 | 6 | 0 | 0 | 0.254 |
| 2 | thalweg / min_cv / 1.0 / highest | 8 | -0.508 | 0.508 | 0.981 | 5 | 6 | 0 | 0 | 0.254 |
| 3 | thalweg / min_cv / 2.0 / highest | 8 | -0.508 | 0.508 | 0.981 | 5 | 6 | 0 | 0 | 0.254 |
| 4 | thalweg / min_cv / 3.0 / highest | 8 | -0.508 | 0.508 | 0.981 | 5 | 6 | 0 | 0 | 0.254 |
| 5 | thalweg / one_se / 0.2 / highest | 8 | -0.676 | 0.682 | 1.075 | 2 | 5 | 0 | 0 | 0.285 |
| 6 | thalweg / one_se / 0.2 / prominent | 8 | -0.676 | 0.682 | 1.075 | 2 | 5 | 0 | 0 | 0.285 |
| 7 | thalweg / one_se / 1.0 / highest | 8 | -0.676 | 0.682 | 1.075 | 2 | 5 | 0 | 0 | 0.285 |
| 8 | thalweg / one_se / 1.0 / prominent | 8 | -0.676 | 0.682 | 1.075 | 2 | 5 | 0 | 0 | 0.285 |
| 9 | thalweg / one_se / 2.0 / highest | 8 | -0.676 | 0.682 | 1.075 | 2 | 5 | 0 | 0 | 0.285 |
| 10 | thalweg / one_se / 2.0 / prominent | 8 | -0.676 | 0.682 | 1.075 | 2 | 5 | 0 | 0 | 0.285 |
| 11 | thalweg / one_se / 3.0 / highest | 8 | -0.676 | 0.682 | 1.075 | 2 | 5 | 0 | 0 | 0.285 |
| 12 | thalweg / one_se / 3.0 / prominent | 8 | -0.676 | 0.682 | 1.075 | 2 | 5 | 0 | 0 | 0.285 |
| 13 | thalweg / min_cv / 0.2 / prominent | 8 | -0.141 | 0.743 | 1.284 | 5 | 6 | 0 | 0 | 0.779 |
| 14 | thalweg / min_cv / 1.0 / prominent | 8 | -0.141 | 0.743 | 1.284 | 5 | 6 | 0 | 0 | 0.779 |
| 15 | thalweg / min_cv / 2.0 / prominent | 8 | -0.141 | 0.743 | 1.284 | 5 | 6 | 0 | 0 | 0.779 |
| 16 | thalweg / min_cv / 3.0 / prominent | 8 | -0.141 | 0.743 | 1.284 | 5 | 6 | 0 | 0 | 0.779 |
| 17 | thalweg / one_se / 0.2 / first | 8 | -1.428 | 1.434 | 2.004 | 1 | 3 | 0 | 0 | 1.127 |
| 18 | thalweg / one_se / 1.0 / first | 8 | -1.428 | 1.434 | 2.004 | 1 | 3 | 0 | 0 | 1.127 |
| 19 | thalweg / one_se / 2.0 / first | 8 | -1.428 | 1.434 | 2.004 | 1 | 3 | 0 | 0 | 1.127 |
| 20 | thalweg / one_se / 3.0 / first | 8 | -1.428 | 1.434 | 2.004 | 1 | 3 | 0 | 0 | 1.127 |
| 21 | thalweg / min_cv / 3.0 / first | 8 | -2.261 | 2.261 | 2.595 | 1 | 1 | 0 | 0 | 0.728 |
| 22 | original / min_cv / 0.2 / prominent | 8 | -2.595 | 2.595 | 2.715 | 0 | 0 | 0 | 0 | 0.225 |
| 23 | original / min_cv / 1.0 / prominent | 8 | -2.595 | 2.595 | 2.715 | 0 | 0 | 0 | 0 | 0.225 |
| 24 | original / min_cv / 2.0 / prominent | 8 | -2.595 | 2.595 | 2.715 | 0 | 0 | 0 | 0 | 0.225 |
| 25 | original / min_cv / 0.2 / highest | 8 | -2.834 | 2.834 | 2.865 | 0 | 0 | 0 | 0 | 0.021 |
| 26 | original / min_cv / 1.0 / highest | 8 | -2.834 | 2.834 | 2.865 | 0 | 0 | 0 | 0 | 0.021 |
| 27 | original / min_cv / 2.0 / highest | 8 | -2.834 | 2.834 | 2.865 | 0 | 0 | 0 | 0 | 0.021 |
| 28 | original / min_cv / 3.0 / highest | 8 | -2.834 | 2.834 | 2.865 | 0 | 0 | 0 | 0 | 0.021 |
| 29 | original / min_cv / 3.0 / prominent | 8 | -2.834 | 2.834 | 2.865 | 0 | 0 | 0 | 0 | 0.021 |
| 30 | original / one_se / 0.2 / highest | 8 | -2.887 | 2.887 | 2.917 | 0 | 0 | 0 | 0 | 0.061 |
| 31 | original / one_se / 0.2 / prominent | 8 | -2.887 | 2.887 | 2.917 | 0 | 0 | 0 | 0 | 0.061 |
| 32 | original / one_se / 1.0 / highest | 8 | -2.887 | 2.887 | 2.917 | 0 | 0 | 0 | 0 | 0.061 |
| 33 | original / one_se / 1.0 / prominent | 8 | -2.887 | 2.887 | 2.917 | 0 | 0 | 0 | 0 | 0.061 |
| 34 | original / one_se / 2.0 / highest | 8 | -2.887 | 2.887 | 2.917 | 0 | 0 | 0 | 0 | 0.061 |
| 35 | original / one_se / 2.0 / prominent | 8 | -2.887 | 2.887 | 2.917 | 0 | 0 | 0 | 0 | 0.061 |
| 36 | original / one_se / 3.0 / highest | 8 | -2.887 | 2.887 | 2.917 | 0 | 0 | 0 | 0 | 0.061 |
| 37 | original / one_se / 3.0 / prominent | 8 | -2.887 | 2.887 | 2.917 | 0 | 0 | 0 | 0 | 0.061 |
| 38 | thalweg / min_cv / 1.0 / first | 8 | -3.020 | 3.020 | 3.411 | 1 | 1 | 0 | 0 | 1.732 |
| 39 | thalweg / min_cv / 2.0 / first | 8 | -3.020 | 3.020 | 3.411 | 1 | 1 | 0 | 0 | 1.732 |
| 40 | original / one_se / 1.0 / first | 8 | -3.092 | 3.092 | 3.172 | 0 | 0 | 0 | 0 | 0.059 |
| 41 | original / one_se / 2.0 / first | 8 | -3.092 | 3.092 | 3.172 | 0 | 0 | 0 | 0 | 0.059 |
| 42 | original / one_se / 3.0 / first | 8 | -3.092 | 3.092 | 3.172 | 0 | 0 | 0 | 0 | 0.059 |
| 43 | original / one_se / 0.2 / first | 8 | -3.094 | 3.094 | 3.173 | 0 | 0 | 0 | 0 | 0.697 |
| 44 | original / min_cv / 3.0 / first | 8 | -3.228 | 3.228 | 3.297 | 0 | 0 | 0 | 0 | 0.021 |
| 45 | original / min_cv / 1.0 / first | 8 | -3.397 | 3.397 | 3.518 | 0 | 0 | 0 | 0 | 0.022 |
| 46 | original / min_cv / 2.0 / first | 8 | -3.397 | 3.397 | 3.518 | 0 | 0 | 0 | 0 | 0.022 |
| 47 | thalweg / min_cv / 0.2 / first | 8 | -3.401 | 3.401 | 4.091 | 1 | 1 | 0 | 0 | 2.113 |
| 48 | original / min_cv / 0.2 / first | 8 | -4.065 | 4.065 | 4.453 | 0 | 0 | 0 | 0 | 0.022 |

## Le 6 combinazioni più vicine per sezione

### arno.csv sezione 1

z_expert_low = 15.71 m, z_expert_high = 18.11 m

Nota: piana interna bassa in sinistra a 15,2–15,5 m (200–228 m); piana dietro argine destro a ~15,2 m

Più vicine a z_expert_low:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / first | 15.421 | 15.345–15.447 | 11/11 | -0.289 |
| thalweg / min_cv / 0.2 / highest | 15.421 | 15.345–15.447 | 11/11 | -0.289 |
| thalweg / min_cv / 0.2 / prominent | 15.421 | 15.345–15.447 | 11/11 | -0.289 |
| thalweg / min_cv / 1.0 / first | 15.421 | 15.345–15.447 | 11/11 | -0.289 |
| thalweg / min_cv / 1.0 / highest | 15.421 | 15.345–15.447 | 11/11 | -0.289 |
| thalweg / min_cv / 1.0 / prominent | 15.421 | 15.345–15.447 | 11/11 | -0.289 |

Più vicine a z_expert_high:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / first | 15.421 | 15.345–15.447 | 11/11 | -2.689 |
| thalweg / min_cv / 0.2 / highest | 15.421 | 15.345–15.447 | 11/11 | -2.689 |
| thalweg / min_cv / 0.2 / prominent | 15.421 | 15.345–15.447 | 11/11 | -2.689 |
| thalweg / min_cv / 1.0 / first | 15.421 | 15.345–15.447 | 11/11 | -2.689 |
| thalweg / min_cv / 1.0 / highest | 15.421 | 15.345–15.447 | 11/11 | -2.689 |
| thalweg / min_cv / 1.0 / prominent | 15.421 | 15.345–15.447 | 11/11 | -2.689 |

### arno.csv sezione 2

z_expert_low = 13.54 m, z_expert_high = 17.90 m

Nota: la sezione interseca un fosso laterale (futuro affluente dell’Arno) tra 100 e 130 m; bankfull riferito all’alveo principale

Più vicine a z_expert_low:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| original / min_cv / 0.2 / first | 13.315 | 13.308–13.315 | 11/11 | -0.225 |
| original / min_cv / 1.0 / first | 13.315 | 13.308–13.315 | 11/11 | -0.225 |
| original / min_cv / 2.0 / first | 13.315 | 13.308–13.315 | 11/11 | -0.225 |
| original / min_cv / 3.0 / first | 13.315 | 13.308–13.315 | 11/11 | -0.225 |
| thalweg / one_se / 0.2 / first | 13.767 | 13.750–17.366 | 11/11 | 0.227 |
| thalweg / one_se / 1.0 / first | 13.767 | 13.750–17.366 | 11/11 | 0.227 |

Più vicine a z_expert_high:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / highest | 17.576 | 17.560–17.594 | 11/11 | -0.324 |
| thalweg / min_cv / 0.2 / prominent | 17.576 | 17.560–17.594 | 11/11 | -0.324 |
| thalweg / min_cv / 1.0 / highest | 17.576 | 17.560–17.594 | 11/11 | -0.324 |
| thalweg / min_cv / 1.0 / prominent | 17.576 | 17.560–17.594 | 11/11 | -0.324 |
| thalweg / min_cv / 2.0 / highest | 17.576 | 17.560–17.594 | 11/11 | -0.324 |
| thalweg / min_cv / 2.0 / prominent | 17.576 | 17.560–17.594 | 11/11 | -0.324 |

### arno.csv sezione 3

z_expert_low = 17.59 m, z_expert_high = 17.59 m

Nota: nessun gradino interno evidente; piana dietro argine destro a ~15 m (480-720 m); piccolo fosso in sinistra a ~55 m (fondo ~15,6)

Più vicine a z_expert_low:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / first | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 0.2 / highest | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 0.2 / prominent | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 1.0 / first | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 1.0 / highest | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 1.0 / prominent | 17.501 | 17.491–17.556 | 11/11 | -0.089 |

Più vicine a z_expert_high:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / first | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 0.2 / highest | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 0.2 / prominent | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 1.0 / first | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 1.0 / highest | 17.501 | 17.491–17.556 | 11/11 | -0.089 |
| thalweg / min_cv / 1.0 / prominent | 17.501 | 17.491–17.556 | 11/11 | -0.089 |

### arno.csv sezione 5

z_expert_low = 17.70 m, z_expert_high = 17.70 m

Più vicine a z_expert_low:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / highest | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 0.2 / prominent | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 1.0 / highest | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 1.0 / prominent | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 2.0 / highest | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 2.0 / prominent | 17.642 | 17.609–17.686 | 11/11 | -0.058 |

Più vicine a z_expert_high:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / highest | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 0.2 / prominent | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 1.0 / highest | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 1.0 / prominent | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 2.0 / highest | 17.642 | 17.609–17.686 | 11/11 | -0.058 |
| thalweg / min_cv / 2.0 / prominent | 17.642 | 17.609–17.686 | 11/11 | -0.058 |

### arno.csv sezione 6

z_expert_low = 12.60 m, z_expert_high = 18.00 m

Più vicine a z_expert_low:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 1.0 / first | 12.837 | 12.837–17.465 | 11/11 | 0.237 |
| thalweg / min_cv / 2.0 / first | 12.837 | 12.837–17.465 | 11/11 | 0.237 |
| original / one_se / 0.2 / first | 14.582 | 14.582–14.591 | 11/11 | 1.982 |
| original / one_se / 0.2 / highest | 14.582 | 14.582–14.591 | 11/11 | 1.982 |
| original / one_se / 0.2 / prominent | 14.582 | 14.582–14.591 | 11/11 | 1.982 |
| original / one_se / 1.0 / first | 14.582 | 14.582–14.591 | 11/11 | 1.982 |

Più vicine a z_expert_high:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / highest | 17.836 | 17.748–17.839 | 11/11 | -0.164 |
| thalweg / min_cv / 0.2 / prominent | 17.836 | 17.748–17.839 | 11/11 | -0.164 |
| thalweg / min_cv / 1.0 / highest | 17.836 | 17.748–17.839 | 11/11 | -0.164 |
| thalweg / min_cv / 1.0 / prominent | 17.836 | 17.748–17.839 | 11/11 | -0.164 |
| thalweg / min_cv / 2.0 / highest | 17.836 | 17.748–17.839 | 11/11 | -0.164 |
| thalweg / min_cv / 2.0 / prominent | 17.836 | 17.748–17.839 | 11/11 | -0.164 |

### arno.csv sezione 7

z_expert_low = 14.30 m, z_expert_high = 16.90 m

Nota: argine in destra; oltre l’argine piana a ~15,9 m: con “original” il calcolo può fermarsi sotto 15,9

Più vicine a z_expert_low:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| original / min_cv / 0.2 / first | 14.454 | 14.421–14.468 | 11/11 | 0.154 |
| original / min_cv / 1.0 / first | 14.454 | 14.421–14.468 | 11/11 | 0.154 |
| original / min_cv / 2.0 / first | 14.454 | 14.421–14.468 | 11/11 | 0.154 |
| original / min_cv / 3.0 / first | 14.454 | 14.421–14.468 | 11/11 | 0.154 |
| thalweg / min_cv / 0.2 / first | 14.549 | 12.565–16.845 | 11/11 | 0.249 |
| thalweg / min_cv / 1.0 / first | 14.549 | 12.565–16.845 | 11/11 | 0.249 |

Più vicine a z_expert_high:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / highest | 16.888 | 16.845–17.681 | 11/11 | -0.012 |
| thalweg / min_cv / 0.2 / prominent | 16.888 | 16.845–17.681 | 11/11 | -0.012 |
| thalweg / min_cv / 1.0 / highest | 16.888 | 16.845–17.681 | 11/11 | -0.012 |
| thalweg / min_cv / 1.0 / prominent | 16.888 | 16.845–17.681 | 11/11 | -0.012 |
| thalweg / min_cv / 2.0 / highest | 16.888 | 16.845–17.681 | 11/11 | -0.012 |
| thalweg / min_cv / 2.0 / prominent | 16.888 | 16.845–17.681 | 11/11 | -0.012 |

### arno.csv sezione 8

z_expert_low = 12.66 m, z_expert_high = 17.80 m

Più vicine a z_expert_low:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| original / min_cv / 0.2 / first | 12.656 | 12.654–12.686 | 11/11 | -0.004 |
| original / min_cv / 1.0 / first | 12.656 | 12.654–12.686 | 11/11 | -0.004 |
| original / min_cv / 2.0 / first | 12.656 | 12.654–12.686 | 11/11 | -0.004 |
| thalweg / min_cv / 0.2 / first | 12.684 | 12.654–17.272 | 11/11 | 0.024 |
| thalweg / min_cv / 1.0 / first | 12.684 | 12.654–17.272 | 11/11 | 0.024 |
| thalweg / min_cv / 2.0 / first | 12.684 | 12.654–17.272 | 11/11 | 0.024 |

Più vicine a z_expert_high:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / highest | 17.272 | 17.191–17.765 | 11/11 | -0.528 |
| thalweg / min_cv / 1.0 / highest | 17.272 | 17.191–17.765 | 11/11 | -0.528 |
| thalweg / min_cv / 2.0 / highest | 17.272 | 17.191–17.765 | 11/11 | -0.528 |
| thalweg / min_cv / 3.0 / highest | 17.272 | 17.191–17.765 | 11/11 | -0.528 |
| thalweg / one_se / 0.2 / first | 17.151 | 16.968–17.324 | 11/11 | -0.649 |
| thalweg / one_se / 0.2 / highest | 17.151 | 16.968–17.324 | 11/11 | -0.649 |

### arno.csv sezione 9

z_expert_low = 15.19 m, z_expert_high = 17.40 m

Nota: gradino stretto in sinistra a ~15,2 m (185-188 m) e altro minore a ~13,2; piana dietro argine destro a ~15,2 m (380-450 m), stessa quota del gradino: effetti non distinguibili con “original”

Più vicine a z_expert_low:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / first | 15.158 | 15.139–15.166 | 11/11 | -0.032 |
| thalweg / min_cv / 1.0 / first | 15.158 | 15.139–15.166 | 11/11 | -0.032 |
| thalweg / min_cv / 2.0 / first | 15.158 | 15.139–15.166 | 11/11 | -0.032 |
| thalweg / min_cv / 3.0 / first | 15.158 | 15.139–15.166 | 11/11 | -0.032 |
| original / min_cv / 0.2 / first | 14.928 | 14.904–14.928 | 11/11 | -0.262 |
| original / min_cv / 0.2 / highest | 14.928 | 14.904–14.928 | 11/11 | -0.262 |

Più vicine a z_expert_high:

| combinazione | mediana | min–max seed | seed ok | errore |
|---|---|---|---|---|
| thalweg / min_cv / 0.2 / highest | 17.201 | 16.958–17.213 | 11/11 | -0.199 |
| thalweg / min_cv / 0.2 / prominent | 17.201 | 15.139–17.213 | 11/11 | -0.199 |
| thalweg / min_cv / 1.0 / highest | 17.201 | 16.958–17.213 | 11/11 | -0.199 |
| thalweg / min_cv / 1.0 / prominent | 17.201 | 15.139–17.213 | 11/11 | -0.199 |
| thalweg / min_cv / 2.0 / highest | 17.201 | 16.958–17.213 | 11/11 | -0.199 |
| thalweg / min_cv / 2.0 / prominent | 17.201 | 15.139–17.213 | 11/11 | -0.199 |

## Diagnostica dei poligoni bagnati (original, first)

Ipotesi da verificare: su Arno 3, 5, 6, 7 e 9 il livello scelto cade subito prima che si allaghi la piana dietro l'argine, più bassa delle sponde (vedi le note nel CSV esperto, riportate sopra). Per ogni livello scelto (mediana sui seed): numero di poligoni bagnati a z e a z + 0.2 m (stessa costruzione del core), e quota del prossimo minimo locale del profilo sopra z, dove si apre un nuovo poligono (Δ = quota − z).

| sezione | selection | min_hyd_depth | z scelto (mediana) | poligoni a z | poligoni a z + 0.2 | prossimo minimo locale del profilo sopra z | Δ | distanza del minimo [m] |
|---|---|---|---|---|---|---|---|---|
| arno 1 | min_cv | 0.2 | 14.813 | 1 | 5 | 14.857 | 0.044 | 452.0 |
| arno 1 | min_cv | 1.0 | 14.813 | 1 | 5 | 14.857 | 0.044 | 452.0 |
| arno 1 | min_cv | 2.0 | 14.813 | 1 | 5 | 14.857 | 0.044 | 452.0 |
| arno 1 | min_cv | 3.0 | 14.813 | 1 | 5 | 14.857 | 0.044 | 452.0 |
| arno 1 | one_se | 0.2 | 14.788 | 1 | 3 | 14.857 | 0.069 | 452.0 |
| arno 1 | one_se | 1.0 | 14.788 | 1 | 3 | 14.857 | 0.069 | 452.0 |
| arno 1 | one_se | 2.0 | 14.788 | 1 | 3 | 14.857 | 0.069 | 452.0 |
| arno 1 | one_se | 3.0 | 14.788 | 1 | 3 | 14.857 | 0.069 | 452.0 |
| arno 2 | min_cv | 0.2 | 13.315 | 4 | 7 | 13.330 | 0.015 | 109.9 |
| arno 2 | min_cv | 1.0 | 13.315 | 4 | 7 | 13.330 | 0.015 | 109.9 |
| arno 2 | min_cv | 2.0 | 13.315 | 4 | 7 | 13.330 | 0.015 | 109.9 |
| arno 2 | min_cv | 3.0 | 13.315 | 4 | 7 | 13.330 | 0.015 | 109.9 |
| arno 2 | one_se | 0.2 | 13.288 | 4 | 6 | 13.330 | 0.042 | 109.9 |
| arno 2 | one_se | 1.0 | 13.288 | 4 | 6 | 13.330 | 0.042 | 109.9 |
| arno 2 | one_se | 2.0 | 13.288 | 4 | 6 | 13.330 | 0.042 | 109.9 |
| arno 2 | one_se | 3.0 | 13.288 | 4 | 6 | 13.330 | 0.042 | 109.9 |
| arno 3 | min_cv | 0.2 | 14.680 | 2 | 9 | 14.745 | 0.065 | 514.7 |
| arno 3 | min_cv | 1.0 | 14.680 | 2 | 9 | 14.745 | 0.065 | 514.7 |
| arno 3 | min_cv | 2.0 | 14.680 | 2 | 9 | 14.745 | 0.065 | 514.7 |
| arno 3 | min_cv | 3.0 | 14.680 | 2 | 9 | 14.745 | 0.065 | 514.7 |
| arno 3 | one_se | 0.2 | 14.628 | 1 | 7 | 14.665 | 0.037 | 511.7 |
| arno 3 | one_se | 1.0 | 14.628 | 1 | 7 | 14.665 | 0.037 | 511.7 |
| arno 3 | one_se | 2.0 | 14.628 | 1 | 7 | 14.665 | 0.037 | 511.7 |
| arno 3 | one_se | 3.0 | 14.628 | 1 | 7 | 14.665 | 0.037 | 511.7 |
| arno 5 | min_cv | 0.2 | 9.450 | 3 | 9 | 9.475 | 0.025 | 301.8 |
| arno 5 | min_cv | 1.0 | 14.794 | 1 | 7 | 14.861 | 0.067 | 722.6 |
| arno 5 | min_cv | 2.0 | 14.794 | 1 | 7 | 14.861 | 0.067 | 722.6 |
| arno 5 | min_cv | 3.0 | 14.794 | 1 | 7 | 14.861 | 0.067 | 722.6 |
| arno 5 | one_se | 0.2 | 14.677 | 1 | 2 | 14.861 | 0.184 | 722.6 |
| arno 5 | one_se | 1.0 | 14.693 | 1 | 2 | 14.861 | 0.168 | 722.6 |
| arno 5 | one_se | 2.0 | 14.693 | 1 | 2 | 14.861 | 0.168 | 722.6 |
| arno 5 | one_se | 3.0 | 14.693 | 1 | 2 | 14.861 | 0.168 | 722.6 |
| arno 6 | min_cv | 0.2 | 14.587 | 2 | 3 | 14.601 | 0.014 | 397.6 |
| arno 6 | min_cv | 1.0 | 14.587 | 2 | 3 | 14.601 | 0.014 | 397.6 |
| arno 6 | min_cv | 2.0 | 14.587 | 2 | 3 | 14.601 | 0.014 | 397.6 |
| arno 6 | min_cv | 3.0 | 14.587 | 2 | 3 | 14.601 | 0.014 | 397.6 |
| arno 6 | one_se | 0.2 | 14.582 | 2 | 3 | 14.601 | 0.019 | 397.6 |
| arno 6 | one_se | 1.0 | 14.582 | 2 | 3 | 14.601 | 0.019 | 397.6 |
| arno 6 | one_se | 2.0 | 14.582 | 2 | 3 | 14.601 | 0.019 | 397.6 |
| arno 6 | one_se | 3.0 | 14.582 | 2 | 3 | 14.601 | 0.019 | 397.6 |
| arno 7 | min_cv | 0.2 | 14.454 | 3 | 1 | 14.879 | 0.425 | 661.4 |
| arno 7 | min_cv | 1.0 | 14.454 | 3 | 1 | 14.879 | 0.425 | 661.4 |
| arno 7 | min_cv | 2.0 | 14.454 | 3 | 1 | 14.879 | 0.425 | 661.4 |
| arno 7 | min_cv | 3.0 | 14.454 | 3 | 1 | 14.879 | 0.425 | 661.4 |
| arno 7 | one_se | 0.2 | 14.878 | 1 | 4 | 14.879 | 0.001 | 661.4 |
| arno 7 | one_se | 1.0 | 14.878 | 1 | 4 | 14.879 | 0.001 | 661.4 |
| arno 7 | one_se | 2.0 | 14.878 | 1 | 4 | 14.879 | 0.001 | 661.4 |
| arno 7 | one_se | 3.0 | 14.878 | 1 | 4 | 14.879 | 0.001 | 661.4 |
| arno 8 | min_cv | 0.2 | 12.656 | 2 | 1 | 13.509 | 0.853 | 353.5 |
| arno 8 | min_cv | 1.0 | 12.656 | 2 | 1 | 13.509 | 0.853 | 353.5 |
| arno 8 | min_cv | 2.0 | 12.656 | 2 | 1 | 13.509 | 0.853 | 353.5 |
| arno 8 | min_cv | 3.0 | 14.004 | 2 | 3 | 14.088 | 0.084 | 267.6 |
| arno 8 | one_se | 0.2 | 14.954 | 2 | 3 | 14.981 | 0.027 | 440.4 |
| arno 8 | one_se | 1.0 | 14.954 | 2 | 3 | 14.981 | 0.027 | 440.4 |
| arno 8 | one_se | 2.0 | 14.954 | 2 | 3 | 14.981 | 0.027 | 440.4 |
| arno 8 | one_se | 3.0 | 14.954 | 2 | 3 | 14.981 | 0.027 | 440.4 |
| arno 9 | min_cv | 0.2 | 14.928 | 2 | 3 | 15.037 | 0.109 | 387.9 |
| arno 9 | min_cv | 1.0 | 14.928 | 2 | 3 | 15.037 | 0.109 | 387.9 |
| arno 9 | min_cv | 2.0 | 14.928 | 2 | 3 | 15.037 | 0.109 | 387.9 |
| arno 9 | min_cv | 3.0 | 14.928 | 2 | 3 | 15.037 | 0.109 | 387.9 |
| arno 9 | one_se | 0.2 | 14.854 | 2 | 3 | 15.037 | 0.183 | 387.9 |
| arno 9 | one_se | 1.0 | 14.854 | 2 | 3 | 15.037 | 0.183 | 387.9 |
| arno 9 | one_se | 2.0 | 14.854 | 2 | 3 | 15.037 | 0.183 | 387.9 |
| arno 9 | one_se | 3.0 | 14.854 | 2 | 3 | 15.037 | 0.183 | 387.9 |
