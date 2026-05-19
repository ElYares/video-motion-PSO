# Video Motion PSO

Proyecto experimental para detectar movimiento en video con OpenCV y optimizar
los parametros del detector usando perfiles manuales, random search y Particle
Swarm Optimization (PSO).

El objetivo es encontrar configuraciones que mantengan buen balance entre:

- deteccion de movimiento suficiente
- estabilidad de eventos
- bajo costo de CPU por frame procesado

## Que hace el proyecto

El pipeline principal vive en `core/motion/detector.py`:

1. Lee un video con OpenCV.
2. Muestrea frames segun `fps_sample`.
3. Redimensiona cada frame a `resolution_width`.
4. Convierte a escala de grises y aplica blur.
5. Compara el frame actual contra el anterior.
6. Aplica threshold y dilatacion.
7. Filtra contornos por area minima.
8. Calcula metricas de movimiento y rendimiento.
9. Opcionalmente genera un video anotado con cajas de movimiento.

La evaluacion y optimizacion usan una funcion heuristica de score definida en
`core/motion/evaluator.py`. Todavia no es una metrica de exactitud con ground
truth; compara configuraciones por proporcion de movimiento, estabilidad y costo
de procesamiento.

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
  --write-videos
```

Objetivos disponibles:

- `balanced`: balance entre movimiento esperado, estabilidad y rendimiento.
- `sensitive`: favorece detectar mas movimiento sutil.
- `low_cpu`: favorece menor costo de procesamiento.

Salidas principales:

- `outputs/reports/evaluation_summary_<objective>.json`
- `outputs/reports/evaluation_ranking_<objective>.csv`
- `outputs/videos/<profile>_evaluated.mp4` si se usa `--write-videos`

## Como correr random search

Random search prueba configuraciones aleatorias del espacio definido en
`core/motion/optimizer.py`.

```bash
python apps/cli/random_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective balanced \
  --iterations 30 \
  --seed 42 \
  --write-best-video
```

Salidas:

- `outputs/reports/random_search_<objective>.json`
- `outputs/reports/random_search_<objective>.csv`
- `outputs/videos/random_search_best_<objective>.mp4` si se usa `--write-best-video`

## Como correr PSO

PSO optimiza un vector continuo y lo decodifica a un `MotionConfig` valido. Por
default usa semillas conocidas de perfiles manuales y resultados previos.

```bash
python apps/cli/pso_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective balanced \
  --particles 10 \
  --iterations 8 \
  --seed 42 \
  --write-best-video
```

Parametros utiles:

- `--particles`: numero de particulas.
- `--iterations`: iteraciones del enjambre.
- `--inertia-weight`: peso de inercia, default `0.65`.
- `--cognitive-weight`: peso del mejor personal, default `1.5`.
- `--social-weight`: peso del mejor global, default `1.5`.
- `--no-seeds`: desactiva semillas conocidas y arranca aleatorio.

Salidas:

- `outputs/reports/pso_search_<objective>.json`
- `outputs/reports/pso_search_<objective>.csv`
- `outputs/videos/pso_best_<objective>.mp4` si se usa `--write-best-video`

## Como comparar optimizadores

Primero genera reportes para los objetivos que quieras comparar. Ejemplo para
los tres objetivos:

```bash
for objective in balanced sensitive low_cpu; do
  python apps/cli/evaluate_configs.py --input datasets/videos/workers_hallway.mp4 --objective "$objective"
  python apps/cli/random_search.py --input datasets/videos/workers_hallway.mp4 --objective "$objective" --iterations 30 --seed 42
  python apps/cli/pso_search.py --input datasets/videos/workers_hallway.mp4 --objective "$objective" --particles 12 --iterations 10 --seed 42
done
```

Despues compara los JSON existentes sin reprocesar video:

```bash
python apps/cli/compare_optimizers.py \
  --reports-dir outputs/reports \
  --objectives balanced sensitive low_cpu \
  --output-json outputs/reports/optimizer_comparison.json \
  --output-csv outputs/reports/optimizer_comparison.csv
```

## Configs ganadoras actuales

Resultados locales generados con `datasets/videos/workers_hallway.mp4`. Los
archivos de salida estan en `outputs/reports/optimizer_comparison.*`.

| Objetivo | Metodo ganador | Score | Configuracion |
| --- | --- | ---: | --- |
| `balanced` | `manual_profiles/random_balanced_best` | `92.0875` | `w=480`, `fps=18.0`, `thr=32`, `blur=3`, `area=300`, `dilate=3`, `gap=0.5` |
| `sensitive` | `seeded_pso/pso_best` | `93.1035` | `w=640`, `fps=25.0`, `thr=22`, `blur=3`, `area=300`, `dilate=2`, `gap=0.5` |
| `low_cpu` | `seeded_pso/pso_best` | `89.6734` | `w=640`, `fps=15.0`, `thr=43`, `blur=5`, `area=600`, `dilate=2`, `gap=0.4` |

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
