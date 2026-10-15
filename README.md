# TP Grupal - Equipo 2 - Cámara de Diputados Argentina

## Estructura del proyecto 

### Scraper 
Completar con cómo se hizo

#### ¿Cuántas votaciones y cuántas filas nuevas encontraron?
- 142 votaciones nuevas, 36494 votos nuevos (total: 537 votaciones, 138009 votos).

#### ¿Qué controles hicieron para saber que la base está completa y bien unida?
Realizamos un script para validar la integridad de los datos. 

Este es el output del script validar_tablas.py:
OK     id_votacion coincide entre las dos tablas (142 sesiones)
OK     legislador_id es biyección correlativa con 373 valores distintos
OK     bloque_id es biyección correlativa con 39 valores distintos
OK     provincia_id es biyección correlativa con 24 valores distintos
OK     ningún legislador vota dos veces en la misma sesión
OK     142 sesiones, todas con >= 231 votos (mediana 257)
       gráfico guardado en /tmp/validar_ok/votos_por_sesion.png

#### Cómo ejecutar el scraper?
- Datos de entrada: Para correr el script formatear_votaciones.py, primero debemos contar con las sesiones ya bajadas previamente (para no bajas todas desde cero). 
- Ubicar `sesiones_dt.csv.gz` y `info_sesiones_dt.csv` dentro de la carpeta `scraper/votaciones_csvs`
- Correr `scraper_votaciones.py` para bajar los csvs, ubicarlos en `scraper/votaciones_csvs`

```
python3 scraper_votaciones.py    # baja los csvs
python3 formatear_votaciones.py votaciones_csvs ./ # formatea los csvs
python3 validar_tablas.py votaciones_csvs
```

- Datos de salida: Dentro de la carpeta `scraper/votaciones_csvs` se generarán los nuevos archivos `sesiones_dt.csv.gz` y `info_sesiones_dt.csv`. Adicionalmente se generará el png con los gráficos de verificación y un backup de los datos previos.




