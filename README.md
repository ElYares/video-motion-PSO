# Video Motion PSO

Proyecto experimental para detectar movimiento en video con OpenCV y optimizar
los parametros del detector usando perfiles manuales, random search y Particle
Swarm Optimization (PSO).

El objetivo es encontrar configuraciones que mantengan buen balance entre:

- deteccion de movimiento suficiente
- estabilidad de eventos
- bajo costo estimado de recursos: resolucion, FPS efectivo y frames procesados

## Que hace el proyecto

El pipeline principal vive en `core/motion/detector.py`:

1. Lee un video con OpenCV.
2. Muestrea frames segun `fps_sample`.
3. Redimensiona cada frame a `resolution_width`.
4. Convierte a escala de grises y aplica blur.
5. Detecta movimiento con `frame_diff` o con sustraccion de fondo `mog2`.
6. Aplica threshold y dilatacion.
7. Filtra contornos por area minima.
8. Calcula metricas de movimiento y rendimiento.
9. Opcionalmente genera un video anotado con cajas de movimiento.

La evaluacion y optimizacion usan una funcion heuristica de score definida en
`core/motion/evaluator.py`. Todavia no es una metrica de exactitud con ground
truth; compara configuraciones por proporcion de movimiento, estabilidad y costo
de procesamiento. El score tambien reporta `resource_score`, `resource_cost`,
`effective_processed_fps` y `processed_frame_ratio` para comparar el costo
estimado de cada configuracion.

## Instalacion

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Coloca videos de prueba en `datasets/videos/`. Esa carpeta y `outputs/` estan
ignoradas por git para no subir archivos pesados.

## Como correr el detector

Ejecuta una configuracion puntual y genera reporte JSON mas video anotado:

```bash
python apps/cli/optimize.py \
  --input datasets/videos/workers_hallway.mp4 \
  --output-report outputs/reports/motion_report.json \
  --output-video outputs/videos/motion_detected.mp4 \
  --method frame_diff \
  --resolution-width 640 \
  --fps-sample 12 \
  --motion-threshold 35 \
  --blur-kernel 5 \
  --min-contour-area 800
```

Salidas:

- `outputs/reports/motion_report.json`
- `outputs/videos/motion_detected.mp4`

## Como evaluar perfiles

Compara los perfiles manuales definidos en `get_default_profiles()`:

```bash
python apps/cli/evaluate_configs.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective balanced \
  --method frame_diff \
  --write-videos
```

Objetivos disponibles:

- `balanced`: balance entre movimiento esperado, estabilidad y rendimiento.
- `sensitive`: favorece detectar mas movimiento sutil.
- `low_cpu`: favorece menor costo de procesamiento.

Metodos disponibles:

- `frame_diff`: diferencia entre frames consecutivos.
- `mog2`: sustraccion de fondo con OpenCV MOG2.

Salidas principales:

- `outputs/reports/evaluation_summary_<objective>_<method>.json`
- `outputs/reports/evaluation_ranking_<objective>_<method>.csv`
- `outputs/videos/<method>_<profile>_evaluated.mp4` si se usa `--write-videos`

Los reportes incluyen los componentes del score: ratio, estabilidad,
rendimiento y recursos.

## Como correr random search

Random search prueba configuraciones aleatorias del espacio definido en
`core/motion/optimizer.py`.

```bash
python apps/cli/random_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective balanced \
  --methods frame_diff mog2 \
  --iterations 100 \
  --seed 42 \
  --write-best-video
```

Salidas:

- `outputs/reports/random_search_<objective>.json`
- `outputs/reports/random_search_<objective>.csv`
- `outputs/videos/random_search_best_<objective>_<method>.mp4` si se usa `--write-best-video`

`--methods` permite probar `frame_diff`, `mog2` o ambos en la misma corrida. El
ranking y el CSV incluyen la columna `detector_method`.

## Como correr PSO

PSO optimiza un vector continuo y lo decodifica a un `MotionConfig` valido. Por
default usa semillas conocidas de perfiles manuales y resultados previos.

```bash
python apps/cli/pso_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective balanced \
  --methods frame_diff mog2 \
  --particles 12 \
  --iterations 10 \
  --seed 42 \
  --write-best-video
```

Parametros utiles:

- `--particles`: numero de particulas.
- `--iterations`: iteraciones del enjambre.
- `--inertia-weight`: peso de inercia, default `0.65`.
- `--cognitive-weight`: peso del mejor personal, default `1.5`.
- `--social-weight`: peso del mejor global, default `1.5`.
- `--methods`: metodos de deteccion a comparar, default `frame_diff`.
- `--no-seeds`: desactiva semillas conocidas y arranca aleatorio.

Salidas:

- `outputs/reports/pso_search_<objective>.json`
- `outputs/reports/pso_search_<objective>.csv`
- `outputs/videos/pso_best_<objective>_<method>.mp4` si se usa `--write-best-video`

## Como comparar optimizadores

Primero genera reportes para los objetivos que quieras comparar. Ejemplo para
los tres objetivos:

```bash
for objective in balanced sensitive low_cpu; do
  python apps/cli/evaluate_configs.py --input datasets/videos/workers_hallway.mp4 --objective "$objective" --method frame_diff
  python apps/cli/evaluate_configs.py --input datasets/videos/workers_hallway.mp4 --objective "$objective" --method mog2
  python apps/cli/random_search.py --input datasets/videos/workers_hallway.mp4 --objective "$objective" --methods frame_diff mog2 --iterations 100 --seed 42
  python apps/cli/pso_search.py --input datasets/videos/workers_hallway.mp4 --objective "$objective" --methods frame_diff mog2 --particles 12 --iterations 10 --seed 42
done
```

Despues compara los JSON existentes sin reprocesar video:

```bash
python apps/cli/compare_optimizers.py \
  --reports-dir outputs/reports \
  --objectives balanced sensitive low_cpu \
  --methods frame_diff mog2 \
  --output-json outputs/reports/optimizer_comparison.json \
  --output-csv outputs/reports/optimizer_comparison.csv
```

La tabla de comparacion muestra `Detector`, `Method Rank`, `Resource`,
`Eff FPS` y `Frame Ratio`. Esas columnas salen de `detector_method`,
`method_rank`, `resource_score`, `effective_processed_fps` y
`processed_frame_ratio`.

## Configs ganadoras actuales

Snapshot local actualizado con `datasets/videos/workers_hallway.mp4` para el
comparador completo `balanced`, `sensitive` y `low_cpu`, usando reportes de
`frame_diff` y `mog2`. Los archivos de salida estan en
`outputs/reports/optimizer_comparison.*`.

| Objetivo | Metodo ganador | Score | Resource | Eff FPS | Frame ratio | Configuracion |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `balanced` | `frame_diff/random_search` | `89.7032` | `92.6471` | `8.3333` | `0.3333` | `w=320`, `fps=8.0`, `thr=28`, `blur=5`, `area=300`, `dilate=2`, `gap=0.5` |
| `sensitive` | `frame_diff/random_search` | `90.5733` | `58.2353` | `12.5` | `0.5` | `w=640`, `fps=10.0`, `thr=28`, `blur=3`, `area=250`, `dilate=1`, `gap=0.3` |
| `low_cpu` | `frame_diff/seeded_pso` | `91.0673` | `92.6471` | `8.3333` | `0.3333` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=450`, `dilate=2`, `gap=0.6` |

Snapshot MOG2 de perfiles manuales:

| Objetivo | Mejor perfil | Score | Motion ratio | Resource | Configuracion |
| --- | --- | ---: | ---: | ---: | --- |
| `balanced` | `low_cpu` | `74.4352` | `0.3101` | `92.6471` | `w=320`, `fps=8.0`, `thr=35`, `area=500`, `history=120`, `var=25.0` |
| `sensitive` | `low_cpu` | `81.6724` | `0.3101` | `92.6471` | `w=320`, `fps=8.0`, `thr=35`, `area=500`, `history=120`, `var=25.0` |
| `low_cpu` | `low_cpu` | `78.1945` | `0.3101` | `92.6471` | `w=320`, `fps=8.0`, `thr=35`, `area=500`, `history=120`, `var=25.0` |

Mas detalle en [docs/results.md](docs/results.md).

## Estructura

```txt
video-motion-PSO/
├── apps/cli/
│   ├── optimize.py
│   ├── evaluate_configs.py
│   ├── random_search.py
│   ├── pso_search.py
│   └── compare_optimizers.py
├── core/motion/
│   ├── detector.py
│   ├── evaluator.py
│   ├── optimizer.py
│   ├── pso_optimizer.py
│   └── comparator.py
├── datasets/videos/
├── outputs/
│   ├── reports/
│   └── videos/
└── docs/
    ├── architecture.md
    └── results.md
```

## Documentacion tecnica

- [docs/architecture.md](docs/architecture.md): arquitectura, metricas, scoring y optimizadores.
- [docs/results.md](docs/results.md): resultados actuales y comandos usados.
