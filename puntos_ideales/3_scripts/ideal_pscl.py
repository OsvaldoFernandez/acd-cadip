"""
Puntos ideales de Clinton, Jackman y Rivers (2004) en Python, como pscl::ideal().

El modelo (una dimensión):

    P(y_ij = 1) = Φ(β_j · x_i − α_j)

    x_i  punto ideal del legislador i            prior N(0, 1)
    β_j  discriminación de la votación j          prior N(0, 25)
    α_j  dificultad de la votación j              prior N(0, 25)
    el corte de la votación está en x = α_j / β_j

Se estima igual que pscl: muestreo de Gibbs con aumento de datos
(Albert y Chib, 1993). El truco es inventar, para cada voto, una «utilidad
latente» continua y*_ij = β_j · x_i − α_j + ε_ij, con ε ~ N(0, 1):
votó Sí si y* > 0 y No si y* < 0. Con y* en la mano, todo lo demás son
regresiones lineales comunes. Cada vuelta tiene tres pasos:

  1. y*  | x, β, α   normal truncada: positiva si votó Sí, negativa si votó No
                     (sin truncar si el voto falta e impute=True)
  2. x_i | y*, β, α  regresión de (y*_ij + α_j) sobre β_j, una por legislador
  3. β_j, α_j | y*, x  regresión de y*_ij sobre (x_i, −1), una por votación

Valores por defecto como en pscl::ideal(): maxiter=10000, burnin=5000,
thin=100 y arranque «eigen». normalize=True como en el script de R (en pscl
el valor por defecto es False).
"""

import numpy as np
from scipy.special import ndtr, ndtri

PREC_X = 1.0        # precisión del prior de x      (pscl: xpv = 1)
PREC_BA = 0.04      # precisión del prior de β y α  (pscl: bpv = 0.04, varianza 25)


def arranque_eigen(Y):
    """Valores iniciales como startvals="eigen" de pscl: primer autovector de la
    matriz de acuerdo entre legisladores, centrada por filas y columnas. Es la misma
    idea que el PCA: el modelo bayesiano arranca desde ahí."""
    obs = ~np.isnan(Y)
    S, N = (Y == 1).astype(float), (Y == 0).astype(float)
    O = obs.astype(float)
    acuerdo = (S @ S.T + N @ N.T) / np.maximum(O @ O.T, 1)   # share de votos iguales, par a par
    A = acuerdo - acuerdo.mean(0) - acuerdo.mean(1)[:, None] + acuerdo.mean()
    x = np.linalg.eigh(A)[1][:, -1]
    return (x - x.mean()) / x.std()


def normal_truncada(mu, si, rng):
    """e ~ N(mu, 1) truncada: > 0 donde si=True, < 0 donde si=False.
    Por la cola que corresponde, para no perder precisión cuando mu es extremo."""
    u = rng.uniform(1e-12, 1.0, mu.shape)
    m = np.clip(mu, -30, 30)               # más allá, ndtr da 0 y ndtri(0) = infinito
    return np.where(si, mu - ndtri(u * ndtr(m)), mu + ndtri(u * ndtr(-m)))


def regresion_por_votacion(ystar, x, W, rng):
    """Paso 3: para cada votación j, sortea (β_j, α_j) de la regresión bayesiana
    y*_ij = β_j · x_i − α_j + ε, con prior N(0, 25) para los dos coeficientes.
    Las m regresiones de 2 coeficientes se resuelven juntas (m matrices de 2 × 2)."""
    sx, s1, sxx = W.T @ x, W.sum(0), W.T @ x**2
    sxy, sy = (W * ystar).T @ x, (W * ystar).sum(0)
    P = np.stack([[sxx + PREC_BA, -sx], [-sx, s1 + PREC_BA]]).transpose(2, 0, 1)   # X'X + prior
    cov = np.linalg.inv(P)
    media = np.einsum("jkl,jl->jk", cov, np.stack([sxy, -sy], 1))                # (X'X + prior)⁻¹ X'y
    draw = media + np.einsum("jkl,jl->jk", np.linalg.cholesky(cov), rng.standard_normal((len(s1), 2)))
    return draw[:, 0], draw[:, 1]


def ideal(Y, maxiter=10_000, burnin=5_000, thin=100, impute=False, normalize=True, seed=0):
    """Y: matriz legisladores × votaciones con 1 = Sí, 0 = No y NaN = sin dato.
    Devuelve dict con xbar (media posterior de x), xsd (desvío posterior) y x (las muestras)."""
    rng = np.random.default_rng(seed)
    n, m = Y.shape
    obs = ~np.isnan(Y)
    si = Y == 1
    # W: qué celdas pesan en las regresiones. Sin imputar, sólo donde hubo voto.
    W = np.ones(Y.shape) if impute else obs.astype(float)

    x = arranque_eigen(Y)
    beta, alpha = np.zeros(m), np.zeros(m)
    # arranque de β y α: un probit por votación aproximado con mínimos cuadrados
    for j in range(m):
        o = obs[:, j]
        X = np.column_stack([x[o], -np.ones(o.sum())])
        beta[j], alpha[j] = np.linalg.lstsq(X, np.where(si[o, j], 1.0, -1.0), rcond=None)[0]

    guardadas = []
    for it in range(1, maxiter + 1):
        # 1. utilidades latentes: del lado del voto; si el voto falta, sin cortar (o nada)
        mu = np.outer(x, beta) - alpha
        ystar = normal_truncada(mu, si, rng)
        ystar = np.where(obs, ystar, mu + rng.standard_normal(mu.shape) if impute else 0.0)
        # 2. puntos ideales: una regresión por diputado, todas juntas
        prec = PREC_X + W @ beta**2
        x = (W * (ystar + alpha)) @ beta / prec + rng.standard_normal(n) / np.sqrt(prec)
        # 3. β y α: una regresión por votación
        beta, alpha = regresion_por_votacion(ystar, x, W, rng)
        if it > burnin and it % thin == 0:
            guardadas.append(x.copy())

    X = np.array(guardadas)
    # normalize=True, como pscl: cada muestra guardada se lleva a media 0 y desvío 1.
    # El modelo no cambia si se corre y se estira el eje (y se ajustan β y α):
    # esto elige una escala y hace comparables las muestras.
    if normalize:
        X = (X - X.mean(1, keepdims=True)) / X.std(1, keepdims=True)
    return {"xbar": X.mean(0), "xsd": X.std(0), "x": X}
