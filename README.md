# Beyond the Cage

Sitio informativo sobre la UFC masculina: rankings, perfiles, simulador de combates. Todo el código está separado por archivos y los datos viven en JSON.

## Estructura
```
index.html              página (home, divisiones, simulador)
css/styles.css          estilos (modo oscuro gris/rojo/negro, modo claro azul/blanco)
js/i18n.js              textos en español e inglés
js/model.js             estimaciones y simulador de combate
js/images.js            fotos de peleadores (nombre -> ruta)
js/app.js               interfaz: carga el JSON, dibuja, eventos
assets/logo.png         logo Beyond the Cage
data/rankings.json      campeón + top 15 por división (orden, país, estilo, récord base)
data/seed_ratings.json  valoraciones de respaldo (solo si un peleador tiene pocas peleas)
data/aliases.json       nombres que se escriben distinto en el dataset
data/fighters.json      LO QUE LEE EL SITIO (se genera solo)
scripts/fetch_ufc_data.py     baja los CSV públicos de UFCStats (repo Greco1899/scrape_ufc_stats)
scripts/update_rankings.py    actualiza rankings.json desde Wikipedia (sin probar, ver abajo)
scripts/build_data.py         calcula estadísticas, récords y valoraciones -> fighters.json
scripts/bundle.py             junta todo en dist/index.single.html
.github/workflows/update-data.yml   actualización automática semanal
```

## Probarlo en tu PC
```
python -m http.server 8000      # y abrí http://localhost:8000
```
(Abrir index.html con doble clic no sirve: el navegador bloquea la lectura de data/fighters.json.)

## Publicarlo con actualización automática (GitHub Pages)
1. Creá un repositorio en GitHub y subí esta carpeta.
2. Settings > Pages > Deploy from branch > `main` / root.
3. Settings > Actions > General > Workflow permissions: "Read and write".
4. Listo: cada martes el workflow baja los datos, recalcula y hace commit de `data/fighters.json`. También podés lanzarlo a mano en la pestaña Actions.

El "API en JSON" es `data/fighters.json`, servido por tu propio GitHub Pages.

## Qué es automático y qué no
- Automático (probado): estadísticas de golpeo y grappling, alcance, récord UFC, valoraciones 0-99 y récords (se suman las peleas posteriores a `asOf`). Fuente: dataset público Greco1899/scrape_ufc_stats, que se actualiza después de cada evento.
- Automático pero SIN probar: `update_rankings.py` (orden del ranking desde Wikipedia). Si falla, el workflow sigue con el ranking anterior y lo verás en rojo en Actions. Mientras tanto se puede editar `data/rankings.json` a mano.
- Manual: fotos (`js/images.js`), estilo de pelea (`s`) de peleadores nuevos, país, y el campeón fijado en `champions` (hoy HW: Gane).

## Cómo se calculan las valoraciones
Cada rubro es el percentil del peleador entre los peleadores activos (últimos 4 años, 3+ peleas) de SU MISMA división (así un peso pesado no puntúa más fuerza que un mosca solo por pesar más): potencia (knockdowns y KO), striking (golpes por minuto, precisión, defensa y golpes recibidos), grappling (derribos, precisión, defensa, control), sumisiones y resistencia. El simulador usa esos números, el récord, el alcance, el diferencial de golpes y los cruces previos entre ambos y la forma reciente (últimos 5 combates).
