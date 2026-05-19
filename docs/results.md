# Resultados de optimizacion

Este documento resume los resultados locales guardados en `outputs/reports/`.
Los reportes y videos no se versionan porque `outputs/` esta ignorado por git.

## Contexto de ejecucion

- Video usado: `datasets/videos/workers_hallway.mp4`
- Frames fuente: `948`
- FPS fuente: `25.0`
- Objetivos evaluados: `balanced`, `sensitive`, `low_cpu`
- Random seed: `42`
- Comparador: `apps/cli/compare_optimizers.py`

## Reportes generados

| Tipo | JSON | CSV |
| --- | --- | --- |
| Perfiles manuales | `outputs/reports/evaluation_summary_<objective>.json` | `outputs/reports/evaluation_ranking_<objective>.csv` |
| Random search | `outputs/reports/random_search_<objective>.json` | `outputs/reports/random_search_<objective>.csv` |
| PSO | `outputs/reports/pso_search_<objective>.json` | `outputs/reports/pso_search_<objective>.csv` |
| Comparacion final | `outputs/reports/optimizer_comparison.json` | `outputs/reports/optimizer_comparison.csv` |

## Ganadores por objetivo

| Objetivo | Rank | Metodo | Nombre | Score | Motion ratio | Avg ms | Configuracion |
| --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| `balanced` | 1 | `manual_profiles` | `random_balanced_best` | `92.0875` | `0.2542` | `0.5445` | `w=480`, `fps=18.0`, `thr=32`, `blur=3`, `area=300`, `dilate=3`, `gap=0.5` |
| `sensitive` | 1 | `seeded_pso` | `pso_best` | `93.1035` | `0.3186` | `0.5622` | `w=640`, `fps=25.0`, `thr=22`, `blur=3`, `area=300`, `dilate=2`, `gap=0.5` |
| `low_cpu` | 1 | `seeded_pso` | `pso_best` | `89.6734` | `0.2025` | `0.5622` | `w=640`, `fps=15.0`, `thr=43`, `blur=5`, `area=600`, `dilate=2`, `gap=0.4` |

## Ranking completo del comparador

| Objetivo | Rank | Metodo | Score | Configuracion |
| --- | ---: | --- | ---: | --- |
| `balanced` | 1 | `manual_profiles/random_balanced_best` | `92.0875` | `w=480`, `fps=18.0`, `thr=32`, `blur=3`, `area=300`, `dilate=3`, `gap=0.5` |
| `balanced` | 2 | `seeded_pso/pso_best` | `92.0669` | `w=480`, `fps=18.0`, `thr=32`, `blur=3`, `area=350`, `dilate=3`, `gap=0.6` |
| `balanced` | 3 | `random_search/random_search_best` | `91.6295` | `w=480`, `fps=18.0`, `thr=32`, `blur=3`, `area=300`, `dilate=3`, `gap=0.5` |
| `sensitive` | 1 | `seeded_pso/pso_best` | `93.1035` | `w=640`, `fps=25.0`, `thr=22`, `blur=3`, `area=300`, `dilate=2`, `gap=0.5` |
| `sensitive` | 2 | `manual_profiles/back_person_sensitive` | `92.4931` | `w=640`, `fps=25.0`, `thr=22`, `blur=3`, `area=300`, `dilate=2`, `gap=0.5` |
| `sensitive` | 3 | `random_search/random_search_best` | `90.5487` | `w=640`, `fps=10.0`, `thr=32`, `blur=7`, `area=300`, `dilate=3`, `gap=0.7` |
| `low_cpu` | 1 | `seeded_pso/pso_best` | `89.6734` | `w=640`, `fps=15.0`, `thr=43`, `blur=5`, `area=600`, `dilate=2`, `gap=0.4` |
| `low_cpu` | 2 | `random_search/random_search_best` | `89.0692` | `w=320`, `fps=15.0`, `thr=22`, `blur=5`, `area=800`, `dilate=3`, `gap=0.5` |
| `low_cpu` | 3 | `manual_profiles/low_cpu` | `87.7272` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5` |

## Comandos usados para reproducir

Evaluar perfiles:

```bash
python apps/cli/evaluate_configs.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective balanced \
  --write-videos

python apps/cli/evaluate_configs.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective sensitive \
  --write-videos

python apps/cli/evaluate_configs.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective low_cpu \
  --write-videos
```

Random search:

```bash
python apps/cli/random_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective balanced \
  --iterations 100 \
  --seed 42 \
  --write-best-video

python apps/cli/random_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective sensitive \
  --iterations 30 \
  --seed 42 \
  --write-best-video

python apps/cli/random_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective low_cpu \
  --iterations 30 \
  --seed 42 \
  --write-best-video
```

PSO:

```bash
python apps/cli/pso_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective balanced \
  --particles 12 \
  --iterations 10 \
  --seed 42 \
  --write-best-video

python apps/cli/pso_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective sensitive \
  --particles 12 \
  --iterations 10 \
  --seed 42 \
  --write-best-video

python apps/cli/pso_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective low_cpu \
  --particles 12 \
  --iterations 10 \
  --seed 42 \
  --write-best-video
```

Comparar optimizadores:

```bash
python apps/cli/compare_optimizers.py \
  --reports-dir outputs/reports \
  --objectives balanced sensitive low_cpu \
  --output-json outputs/reports/optimizer_comparison.json \
  --output-csv outputs/reports/optimizer_comparison.csv
```

## Lectura de columnas

- `w`: ancho objetivo del frame procesado.
- `fps`: FPS muestreados del video fuente.
- `thr`: threshold de diferencia de pixeles.
- `blur`: kernel de Gaussian blur.
- `area`: area minima de contorno.
- `dilate`: iteraciones de dilatacion.
- `gap`: segundos de hueco sin movimiento para fusionar eventos.
- `motion_ratio`: `motion_frames / processed_frames`.
- `avg_ms`: tiempo promedio de procesamiento por frame.
