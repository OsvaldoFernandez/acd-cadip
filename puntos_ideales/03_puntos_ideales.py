"""
Puntos ideales por año con dos métodos, sobre la base 2022–hoy:

  - pca:   el atajo: primera componente principal de la matriz de votos
  - bayes: el modelo de Clinton, Jackman y Rivers, como pscl::ideal() (ideal_pscl.py)

Mismos datos y la misma codificación que 03_generar_ideal_points.R:
AFIRMATIVO = 1, NEGATIVO = 0, ABSTENCION y AUSENTE = sin dato; los demás
valores (PRESIDENTE, SIN VOTAR, ...) se descartan.

Uso: python 03_puntos_ideales.py [--rapido]     (--rapido: 2.000 vueltas en vez de 100.000, para probar)
Salida: idps_py/idps.csv con nombre, anio, idp_pca, idp_bayes, sd_bayes
"""

import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from ideal_pscl import ideal

AQUI = Path(__file__).parent
RAPIDO = "--rapido" in sys.argv

# Los mismos legisladores de referencia que corregir_signo_idps() del script de R
DERECHA = ["MILEI, JAVIER GERARDO", "ESPERT, JOSE LUIS", "PIPARO, CAROLINA", "IGLESIAS, FERNANDO ADOLFO",
           "BORNORONI, GABRIEL", "LEMOINE, LILIA", "ALMIRON, LISANDRO", "MAYORAZ, NICOLAS"]   # 2024-2026
IZQUIERDA = ["KIRCHNER, MAXIMO CARLOS", "MOREAU, LEOPOLDO", "TAILHADE, RODOLFO", "YASKY, HUGO",
             "PALAZZO, SERGIO OMAR", "GROSSO, LEONARDO", "SANTORO, LEANDRO", "HELLER, CARLOS"]


def matriz(votos):
    """Legisladores × votaciones: 1 = Sí, 0 = No, NaN = abstención o ausencia."""
    codigo = votos["voto"].map({"AFIRMATIVO": 1.0, "NEGATIVO": 0.0})
    tabla = votos.assign(y=codigo).pivot(index="legislador", columns="id_votacion", values="y")
    return tabla


def pca_atajo(tabla):
    """El atajo con PCA, con sklearn (StandardScaler + PCA de 1 componente).
    Sí = 1, No = −1, ausencia y abstención = 0; cada votación se estandariza; la primera
    componente principal es el «punto ideal»; al final se lleva a [−1, 1].
    El signo de la componente es arbitrario: lo decide la librería, no los datos."""
    M = tabla.replace({0.0: -1.0}).fillna(0.0).to_numpy()
    activos = np.abs(M).sum(1) > 0
    pca = PCA(n_components=1)
    pc1 = pca.fit_transform(StandardScaler().fit_transform(M[activos])).ravel()
    idp = (pc1 - pc1.min()) / (pc1.max() - pc1.min()) * 2 - 1
    return pd.Series(idp, index=tabla.index[activos]), pca.explained_variance_ratio_[0]


def orientar(idp):
    """Signo: la derecha de referencia tiene que dar positivo (como en el script de R)."""
    der, izq = idp.reindex(DERECHA).mean(), idp.reindex(IZQUIERDA).mean()
    invertir = (der < 0) if not np.isnan(der) else (izq > 0)
    return -idp if invertir else idp


def preparar_pscl(tabla):
    """Lo que hace el dropList por defecto de ideal(): fuera las votaciones unánimes
    (lop = 0). Los legisladores sin ningún Sí o No quedan, como en pscl: su punto ideal
    sale del prior (media 0, desvío 1)."""
    Y = tabla.to_numpy()
    si, no = np.nansum(Y == 1, 0), np.nansum(Y == 0, 0)
    return tabla.loc[:, (si > 0) & (no > 0)]


def un_anio(args):
    anio, votos, kw = args
    t0 = time.time()
    tabla = matriz(votos)
    idp_pca, var = pca_atajo(tabla)
    t = preparar_pscl(tabla)
    fit = ideal(t.to_numpy(), impute=True, normalize=True, **kw)
    idp_bayes = orientar(pd.Series(fit["xbar"], index=t.index))
    sd = pd.Series(fit["xsd"], index=t.index)
    r = np.corrcoef(idp_pca.reindex(t.index).fillna(0), idp_bayes)[0, 1]
    print(f"{anio}: {t.shape[0]} legisladores × {t.shape[1]} votaciones "
          f"({tabla.shape[1] - t.shape[1]} unánimes fuera) · PCA explica {var:.0%} · "
          f"r(PCA, bayes) = {r:+.3f} · {time.time() - t0:.0f} s", flush=True)
    return pd.DataFrame({"nombre": tabla.index, "anio": anio,
                         "idp_pca": idp_pca.reindex(tabla.index).to_numpy(),
                         "idp_bayes": idp_bayes.reindex(tabla.index).to_numpy(),
                         "sd_bayes": sd.reindex(tabla.index).to_numpy()})


if __name__ == "__main__":
    ses = pd.read_csv(AQUI.parent / "2_datos" / "sesiones_dt.csv.gz",
                      dtype={"legislador": str}, keep_default_na=False)
    ses = ses[ses["voto"].isin(["AUSENTE", "AFIRMATIVO", "NEGATIVO", "ABSTENCION"])]

    # 100.000 vueltas y no las 10.000 por defecto de pscl: con 10.000 la cadena no llega
    # (dos corridas con distinta semilla correlacionan 0,97; con 100.000, 0,996).
    kw = dict(maxiter=2_000, burnin=1_000, thin=20) if RAPIDO else dict(maxiter=100_000, burnin=50_000, thin=100)
    with ProcessPoolExecutor() as ex:              # un año por proceso
        filas = list(ex.map(un_anio, [(anio, votos, kw) for anio, votos in ses.groupby("yr")]))

    out = AQUI / "idps_py"
    out.mkdir(exist_ok=True)
    pd.concat(filas).to_csv(out / "idps.csv", index=False)
    print("guardado:", out / "idps.csv")
