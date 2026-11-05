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
scripts/fetch_photos.py       baja fotos libres (Wikimedia Commons) de las 8 peleas -> assets/photos + data/fight_photos.json
scripts/bundle.py             junta todo en dist/index.single.html
science/pit.py                características punto en el tiempo (sin fuga de información)
science/train_model.py        backtest hacia adelante + entrenamiento del modelo -> data/model.json, data/model_report.json
science/analysis.ipynb        análisis (tendencias, alcance, edad, estilos, radar) con resultados incluidos
data/model.json               modelo que usa el simulador (coeficientes + características actuales)
data/styles.json              perfil estadístico (clustering) de cada peleador
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

## Fotos de las peleas
`python scripts/fetch_photos.py` (una sola vez) baja una foto con licencia libre de Wikimedia Commons para cada pelea y guarda autor y licencia, que el sitio muestra al pie de la foto. Al tocar la cara activa del octágono la cámara baja a la lona y aparece la foto; sin foto se ve un afiche. Para forzar una foto concreta, editá `FIGHTS` en el script (campo `file`).

## Ícono de la pestaña
`assets/favicon.ico`, `favicon-32.png` y `apple-touch-icon.png` (emblema sobre negro). Si no cambia al instante, recargá sin caché (Ctrl+F5): el navegador guarda los íconos.

## Actualización diaria
El workflow corre todos los días a las 09:00 UTC (también a mano desde Actions > Actualizar datos > Run workflow) y solo hace commit si algo cambió. No usa ninguna clave ni cuenta de pago.

### Fotos propias
Las fotos de `assets/photos/fight-1.jpg` ... `fight-8.jpg` (orden cronológico) ya están cargadas y `fetch_photos.py` no las pisa (salvo `--force`). En `data/fight_photos.json`, `credit`, `license`, `page` y `source` son opcionales: si los completás, se muestran al pie de la foto. Si las fotos son de una agencia o fotógrafo, poné su crédito ahí. Formato recomendado: JPG de hasta ~1400 px de ancho (AVIF/WebP funcionan en navegadores modernos, pero JPG funciona en todos).

## Ciencia de datos: ¿qué tan bueno es el simulador?
El simulador del sitio usa una **regresión logística** entrenada con el historial de la UFC y validada **hacia adelante en el tiempo**:
cada año (2018–hoy) se predice usando solo las peleas anteriores, con características calculadas "como estaban el día de la pelea" (`science/pit.py`).
Resultados con 4.427 peleas (foto del momento en que se escribió; se recalcula con cada actualización):

| Modelo | Acierto | Log loss (menor = mejor) | Calibración (ECE) |
|---|---|---|---|
| Azar | 50,0% | 0,693 | – |
| Solo Elo | 55,4% | 0,685 | 0,008 |
| Solo récord | 57,6% | 0,676 | 0,015 |
| Simulador v1 (fórmula a mano, el anterior) | 58,4% | 0,687 | 0,062 |
| Gradient boosting | 60,1% | 0,661 | 0,013 |
| **Regresión logística (actual)** | **61,9%** (IC95% 60,5–63,3) | **0,653** | 0,014 |

- La fórmula anterior acertaba más que el azar pero sus probabilidades eran demasiado extremas: en log loss no se distingue del azar. El modelo actual está bien calibrado (cuando dice 64%, gana el 67%).
- Gradient boosting no mejora a la regresión logística: con pocos datos y mucho ruido gana el modelo simple.
- El factor con más peso es la edad; después derribos, golpes recibidos y defensa. Detalle en `data/model_report.json` y en `science/analysis.ipynb`.
- Límites: solo UFC, sin lesiones ni contexto, debutantes con pocos datos. Es un modelo estadístico recreativo, no consejo de apuestas.
- Reproducir: `python scripts/fetch_ufc_data.py && python science/train_model.py`.
