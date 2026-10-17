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


------------

ALGUNAS CONCLUSIONES
Tomo en cuenta el output de 2024

```
2024: 261 legisladores × 170 votaciones (10 unánimes fuera) · PCA explica 62% · r(PCA, bayes) = +0.946 · 262 s
```

- (10 unánimes fuera): cuántas columnas se descartaron porque todos votaron igual — no aportan nada para ubicar a nadie en el eje.

- PCA explica 62%: de toda la variación en los votos Sí/No de ese año, cuánta queda explicada por un solo eje (la primera componente). Es, en los hechos, una medida de polarización/alineamiento: cuánto se "unidimensionaliza" el Congreso ese año.  2022-2023 rondan 40-48%, 2024-2026 saltan a 62-65% — sugiere que, en años más recientes, los votos se explican mucho mejor por una sola dimensión izquierda-derecha (menos votaciones cruzadas, bloques más consistentes).

- r(PCA, bayes) = +0.946: correlación entre el punto PCA y el punto bayesiano de cada legislador — qué tan parecido ordenan a la gente los dos métodos. Valores altos en valor absoluto (0.86 a 0.96 en todos los años) dicen que el atajo y el modelo completo coinciden bastante.Ojo con el signo de esta correlación: en 2023 y 2025 es negativa (pero es porque PCA no alinea)

- EJEMPLOS 

  - Ajmechet, Sabrina (pca 0.56, bayes 0.97, sd 0.16): claramente a la derecha, confianza razonable.
  - Aguirre, Hilda (pca -0.82, bayes -0.98, sd 0.498): izquierda, pero con mucha incertidumbre — probablemente votó poco (ausencias/abstenciones) o su patrón de votos fue menos consistente con el resto de los que están en su zona del espectro.


  ---------
PCA:

- CÓMO SE ARMA LA MATRIZ PARA PCA: el CSV viene en formato largo (una fila por legislador×votación, con texto AFIRMATIVO/NEGATIVO/ABSTENCION/AUSENTE), y PCA necesita una matriz numérica, sin faltantes, de observaciones (filas) × variables (columnas) para poder calcular varianza por columna. El script lo arma en tres pasos:

  - pivotear: `tabla.pivot()` convierte el formato largo en una matriz legislador × votación, codificando AFIRMATIVO=1, NEGATIVO=0 y todo lo demás (abstención, ausencia) como NaN.
  - re-codificar a −1/0/1: los 0 (No) pasan a −1 y los NaN se rellenan con 0 — así Sí=+1, No=−1 quedan simétricos alrededor de un punto neutro (0 = sin información), y ya no hay faltantes.
  - estandarizar: `StandardScaler` resta la media y divide por el desvío de cada columna (cada votación), para que una votación muy pareja y una muy dividida pesen igual. Esta es la matriz de la que PCA calcula la varianza/covarianza; el primer componente es el punto ideal crudo, que al final se reescala a [−1, 1].

  Las "observaciones" son los legisladores; las "variables numéricas" son las votaciones, ya convertidas de categóricas a −1/0/1 y estandarizadas.