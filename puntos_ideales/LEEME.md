# Clase 2 · Puntos ideales · datos y scripts

| Carpeta | Qué hay |
|---|---|
| `2_datos/` | La base de votaciones de Diputados 2022–hoy: `sesiones_dt.csv.gz` (un voto por fila) e `info_sesiones_dt.csv` (una votación por fila). 537 votaciones, del 11/03/2022 al 09/09/2026 |
| `3_scripts/` | `03_generar_ideal_points.R` (pscl, 100.000 vueltas, los cinco años: unos 46 minutos), `ideal_pscl.py` (el mismo modelo escrito en Python) y `03_puntos_ideales.py` (lo corre, junto con el PCA; unos 75 minutos, o `--rapido`) |
| `4_demo_rapida/` | `03_generar_ideal_points_demo.R`: el mismo script de R, sólo 2026 y 5.000 vueltas. Tarda unos 2 minutos |

## Para correr

Descomprimir todo junto, sin cambiar los nombres de las carpetas. Los scripts de R buscan los datos en `2_datos`:
se pueden correr parado en la carpeta del script o en esta carpeta. El resultado queda en la carpeta desde donde
se corren.

```bash
Rscript 4_demo_rapida/03_generar_ideal_points_demo.R      # deja el resultado en idps_R_demo/
Rscript 3_scripts/03_generar_ideal_points.R               # deja el resultado en idps_R/
python 3_scripts/03_puntos_ideales.py --rapido            # deja el resultado en 3_scripts/idps_py/
```

Paquetes de R: `pscl`, `data.table`, `pbapply`, `tidyverse`, `lubridate`, `R.utils`.
Python: `numpy`, `scipy`, `pandas`, `scikit-learn`.

La demo sirve para ver que corre y qué devuelve; con tan pocas vueltas el resultado cambia de una corrida a otra.
