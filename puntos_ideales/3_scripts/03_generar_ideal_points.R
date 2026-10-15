rm(list = ls())
gc()

library(data.table)
library(pbapply)
library(tidyverse)
library(lubridate)
library(pscl)

# Correr parado en la carpeta de este script o en la carpeta de la clase (el proyecto de RStudio)
carpeta_puntos_ideales <- getwd()
setwd(if (dir.exists("2_datos")) "2_datos" else "../2_datos")
sesiones <- fread("sesiones_dt.csv.gz")

anios <- sort(unique(sesiones$yr))

sesiones <- sesiones[voto %in% c("AUSENTE","AFIRMATIVO","NEGATIVO","ABSTENCION")]

setorder(sesiones,yr,id_votacion)
sesiones[,id:=seq(1,nrow(sesiones))]

gc()

##########################
# FUNCIÓN PARA CORREGIR SIGNO DE IDPS
# Usa legisladores de referencia conocidos para verificar orientación
##########################
corregir_signo_idps <- function(idps_anio, anio) {
  
  # Legisladores de referencia por año
  # Estos legisladores ESTUVIERON en el período 2022-2025 y son claramente identificables
  
  # DERECHA (deben tener IDP POSITIVO): 
  # LLA, PRO, UCR más conservadores
  legisladores_derecha <- c(
    # La Libertad Avanza (2022-2025)
    "MILEI, JAVIER GERARDO",         # LLA - CABA (2022-2025)
    "ESPERT, JOSE LUIS",             # Avanza Libertad/LLA - Buenos Aires (2022-2025)
    "PIPARO, CAROLINA",              # Avanza Libertad/Buenos Aires Libre/LLA (2022-2025)
    "IGLESIAS, FERNANDO ADOLFO",    # PRO - CABA (2022-2025)
    # La Libertad Avanza (2024-2026): votaron en las 107 votaciones de 2026
    "BORNORONI, GABRIEL",            # LLA - Córdoba (2024-2026)
    "LEMOINE, LILIA",                # LLA - Buenos Aires (2024-2026)
    "ALMIRON, LISANDRO",             # LLA - Corrientes (2024-2026)
    "MAYORAZ, NICOLAS"               # LLA - Santa Fe (2024-2026)
  )
  
  # IZQUIERDA (deben tener IDP NEGATIVO): 
  # Kirchnerismo (FdT/UxP), Izquierda
  legisladores_izquierda <- c(
    # Kirchnerismo - Buenos Aires (todo el período)
    "KIRCHNER, MAXIMO CARLOS",       # FdT/UxP - Buenos Aires (2022-2025)
    "MOREAU, LEOPOLDO",              # FdT/UxP - Buenos Aires (2022-2025)
    "TAILHADE, RODOLFO",            # FdT/UxP - Buenos Aires (2022-2025)
    "YASKY, HUGO",                   # FdT/UxP - Buenos Aires (2022-2025)
    "PALAZZO, SERGIO OMAR",          # FdT/UxP - Buenos Aires (2022-2025)
    "GROSSO, LEONARDO",              # FdT/UxP - Buenos Aires (2022-2023)
    "SANTORO, LEANDRO",              # FdT/UxP - CABA (2022-2025)
    "HELLER, CARLOS"                # FdT/UxP - CABA (2022-2025)
  )
  
  # Buscar legisladores presentes en este año
  derecha_presente <- idps_anio[nombre %in% legisladores_derecha]
  izquierda_presente <- idps_anio[nombre %in% legisladores_izquierda]
  
  # Reportar quiénes fueron encontrados
  if (nrow(derecha_presente) > 0) {
    cat("  ├─ Legisladores de DERECHA encontrados (", nrow(derecha_presente), "):\n")
    cat("  │  ", paste(derecha_presente$nombre, collapse="\n  │  "), "\n")
  } else {
    cat("  ├─ ⚠️  No se encontraron legisladores de DERECHA en este año\n")
  }
  
  if (nrow(izquierda_presente) > 0) {
    cat("  ├─ Legisladores de IZQUIERDA encontrados (", nrow(izquierda_presente), "):\n")
    cat("  │  ", paste(izquierda_presente$nombre, collapse="\n  │  "), "\n")
  } else {
    cat("  ├─ ⚠️  No se encontraron legisladores de IZQUIERDA en este año\n")
  }
  
  # Calcular promedio de cada grupo
  promedio_derecha <- mean(derecha_presente$idp, na.rm = TRUE)
  promedio_izquierda <- mean(izquierda_presente$idp, na.rm = TRUE)
  
  # Determinar si hay que invertir
  # Si la derecha tiene promedio negativo o izquierda positivo, invertir
  invertir <- FALSE
  
  if (length(derecha_presente$idp) > 0 && promedio_derecha < 0) {
    invertir <- TRUE
    cat("  └─ 🔄 Año", anio, ": Derecha tiene IDP negativo (", 
        round(promedio_derecha, 3), "). INVIRTIENDO SIGNO\n\n")
  } else if (length(izquierda_presente$idp) > 0 && promedio_izquierda > 0) {
    invertir <- TRUE
    cat("  └─ 🔄 Año", anio, ": Izquierda tiene IDP positivo (", 
        round(promedio_izquierda, 3), "). INVIRTIENDO SIGNO\n\n")
  } else {
    cat("  └─ ✅ Año", anio, ": Signo correcto (Derecha:", 
        round(promedio_derecha, 3), "/ Izquierda:", 
        round(promedio_izquierda, 3), ")\n\n")
  }
  
  # Aplicar corrección si es necesario
  if (invertir) {
    idps_anio[, idp := idp * -1]
  }
  
  return(idps_anio)
}

##########################
# GENERACIÓN DE IDEAL POINTS POR AÑO
##########################
cat("\n=== GENERANDO IDEAL POINTS ===\n\n")

idps <- lapply(anios, function(x){
  
  cat("📅 Procesando año", x, "...\n")
  
  votos_anio <- sesiones[yr==x]
  nvotos_periodo <- dim(votos_anio)[1]
  legis.names <- unique(votos_anio$legislador)
  nlegis <- length(legis.names) # Cantidad de legisladores
  legis.partidos <- unique(votos_anio[,.(bloque=last(bloque)),legislador])$bloque
  actas.names <- unique(votos_anio[,.(id_votacion)])$id_votacion # Ids de las actas votadas
  nactas <- length(actas.names) # Cantidad de actas votadas
  niveles <- unique(votos_anio[,voto]) # Variantes de voto ("AFIRMATIVO", "NEGATIVO", etc.)
  niveles <- sort(niveles)
  
  notInLegis <- match('AUSENTE', niveles)
  yea <- match('AFIRMATIVO', niveles)
  nay <- match('NEGATIVO', niveles)
  abstencion <- match('ABSTENCION', niveles)
  
  # Genero matriz vacia con dimension nlegis x nactas
  data <- matrix(, nlegis, nactas)
  
  # Matriz con votos por legislador y acta con valores numericos de acuerdo al 'nivel'
  for (n in 1:nvotos_periodo) {
    nombre <- legis.names == votos_anio[n, legislador]
    acta <- actas.names == votos_anio[n, id_votacion]
    nivel <- match(votos_anio[n, voto], niveles)
    data[nombre, acta] <- nivel
  }
  
  legis.data <- data.frame(party=legis.partidos) # Convierto la tabla con partidos x legislador en formato dataframe de R
  row.names(legis.data) <- legis.names # Asigno los nombres de los legisladores como etiquetas de fila
  desc <- paste('Votos de diputados', x) # Etiqueta descriptiva para el periodo
  # La funcion a continuacion, es especifica de pscl y es esencial para el calculo
  # Se utilizan todos los valores que fueron calculados previamente
  rData <- rollcall(data, yea=yea, nay=nay, missing=abstencion,
                    notInLegis=notInLegis, legis.names=legis.names, vote.names=actas.names,
                    legis.data=legis.data, vote.data=NULL, desc=desc, source=NULL)
  
  # El algoritmo de ideal points en si, en este caso, con valores normalizados
  # impute = F: el voto que falta no entra. 100.000 vueltas: con menos, dos corridas
  # con distinta semilla no dan lo mismo
  fitted <- ideal(rData, normalize=T, impute = F, maxiter = 100000, burnin = 50000)
  outcome <- fitted$xbar # Extraigo el vector de puntos ideales
  
  outcome <- cbind(outcome, anio=x) # Le pego la columna que indica el periodo
  
  outcome <- as.data.frame(outcome) # Lo transformo al formato dataframe de R
  names(outcome) <- c("idp","anio") # Agrego nombres de columna
  outcome <- tibble::rownames_to_column(outcome,"nombre") # Extraigo las etiquetas de fila y las transformo en nueva columna con el nombre de cada legislador
  outcome <- as.data.table(outcome)
  
  # APLICAR CORRECCIÓN DE SIGNO
  outcome <- corregir_signo_idps(outcome, x)
  
  return(outcome)
})

idps <- rbindlist(idps)

cat("\n=== GUARDANDO RESULTADOS ===\n")

setwd(carpeta_puntos_ideales)
dir.create("idps_R", showWarnings = FALSE)
setwd("idps_R")

fwrite(idps, "idps.csv")
cat("✅ Archivo guardado: idps.csv\n")

##########################
# CALCULAR DISTANCIAS ENTRE IDPS
##########################
cat("\n=== CALCULANDO DISTANCIAS ===\n")

distancias <- pblapply(anios, function(a){
  idps_anio <- idps[anio==a]
  comb_idps_anio <- as.data.table(expand.grid(nombre1=idps_anio$nombre, nombre2=idps_anio$nombre))
  comb_idps_anio <- comb_idps_anio[idps_anio, on=c("nombre1"="nombre")]
  setnames(comb_idps_anio, "idp", "idp_desde")
  comb_idps_anio <- comb_idps_anio[idps_anio[,!"anio"], on=c("nombre2"="nombre")]
  setnames(comb_idps_anio, "idp", "idp_hasta")
  comb_idps_anio[, distancia:=abs(idp_desde-idp_hasta)]
})

distancias <- rbindlist(distancias)
distancias <- distancias[distancia>0]

fwrite(distancias, "distancias_idps.csv.gz")
cat("✅ Archivo guardado: distancias_idps.csv.gz\n")

gc()

##########################
# GENERAR METADATA CON TAXONOMÍA
##########################
cat("\n=== GENERANDO METADATA ===\n")

setorder(sesiones, yr, id_votacion)
legisladores_bloque_provincia <- sesiones[,.(bloque=last(bloque), provincia=last(provincia)), .(legislador,yr)]

fwrite(legisladores_bloque_provincia, "legisladores_bloque_provincia.csv")
cat("✅ Archivo guardado: legisladores_bloque_provincia.csv (original)\n")

# CARGAR TAXONOMÍA SI EXISTE
archivo_taxonomia <- "legisladores_bloque_provincia_taxonomia.csv"
if (file.exists(archivo_taxonomia)) {
  cat("\n⚠️  Ya existe archivo con taxonomía:", archivo_taxonomia, "\n")
  cat("   Si necesitas regenerar la taxonomía, ejecuta: 02b_crear_taxonomia_bloques.R\n")
} else {
  cat("\n⚠️  No existe archivo con taxonomía.\n")
  cat("   Para generar taxonomía, ejecuta: 02b_crear_taxonomia_bloques.R\n")
}

##########################
# VISUALIZACIONES
##########################
cat("\n=== GENERANDO VISUALIZACIONES ===\n")

# Gráfico de puntos ideales por año
p1 <- idps %>% 
  arrange(anio, idp) %>% 
  group_by(anio) %>% 
  mutate(i=1, i=cumsum(i)) %>% 
  ungroup() %>% 
  ggplot(aes(i, y=idp, col=factor(anio))) +
  geom_line(size=1) +
  labs(
    title="Puntos Ideales por Año",
    subtitle="Distribución de legisladores en el espectro ideológico",
    x="Legislador (ordenado por IDP)",
    y="Punto Ideal (IDP)",
    color="Año"
  ) +
  theme_minimal() +
  theme(legend.position="bottom")

ggsave("puntos_ideales_por_año.png", p1, width=10, height=6, dpi=300)
cat("✅ Gráfico guardado: puntos_ideales_por_año.png\n")

# Gráfico de cantidad de legisladores por año
p2 <- idps[,.N, by="anio"] %>% 
  ggplot(aes(anio, N)) +
  geom_point(size=3) +
  geom_line() +
  labs(
    title="Cantidad de Legisladores por Año",
    x="Año",
    y="Cantidad de Legisladores"
  ) +
  theme_minimal()

ggsave("legisladores_por_año.png", p2, width=8, height=5, dpi=300)
cat("✅ Gráfico guardado: legisladores_por_año.png\n")

cat("\n=== PROCESO COMPLETADO ===\n")
cat("Archivos generados en:", getwd(), "\n\n")

# Resumen estadístico
cat("=== RESUMEN ESTADÍSTICO ===\n")
resumen <- idps[, .(
  n_legisladores = .N,
  idp_min = min(idp),
  idp_max = max(idp),
  idp_media = mean(idp),
  idp_sd = sd(idp)
), by = anio]

print(resumen)
cat("\n")
