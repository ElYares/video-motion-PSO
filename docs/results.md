# Resultados de optimizacion

Este documento resume los resultados locales guardados en `outputs/reports/`.
Los reportes y videos no se versionan porque `outputs/` esta ignorado por git.

El snapshot actualizado cubre `low_cpu` con `frame_diff` y las metricas de
recursos agregadas al score. Tambien documenta una evaluacion manual con
`mog2` para `sensitive` y `low_cpu`.

Si se necesita una comparacion final de `balanced` y `sensitive` con la misma
version del scoring y todos los optimizadores, hay que regenerar esos reportes.

## Contexto de ejecucion

- Video usado: `datasets/videos/workers_hallway.mp4`
- Frames fuente: `948`
- FPS fuente: `25.0`
- Objetivo `frame_diff` actualizado: `low_cpu`
- Objetivos `mog2` evaluados: `sensitive`, `low_cpu`
- Random search: `100` iteraciones, seed `42`
- PSO: `12` particulas, `10` iteraciones, seed `42`
- Comparador `frame_diff`: `apps/cli/compare_optimizers.py --objectives low_cpu --methods frame_diff`
- Comparador por metodo: `apps/cli/compare_optimizers.py --objectives sensitive low_cpu --methods frame_diff mog2`

## Reportes generados

| Tipo | JSON | CSV |
| --- | --- | --- |
| Perfiles manuales | `outputs/reports/evaluation_summary_<objective>_<method>.json` | `outputs/reports/evaluation_ranking_<objective>_<method>.csv` |
| Random search | `outputs/reports/random_search_<objective>.json` | `outputs/reports/random_search_<objective>.csv` |
| PSO | `outputs/reports/pso_search_<objective>.json` | `outputs/reports/pso_search_<objective>.csv` |
| Comparacion final | `outputs/reports/optimizer_comparison.json` | `outputs/reports/optimizer_comparison.csv` |

Nota: los reportes antiguos de `frame_diff` pueden existir sin sufijo de metodo.
El comparador los sigue leyendo como fallback para mantener compatibilidad.

## Resultado actualizado de low_cpu

| Rank | Metodo | Nombre | Score | Resource | Cost | Motion ratio | Eff FPS | Frame ratio | Avg ms | Configuracion |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `seeded_pso` | `pso_best` | `91.0649` | `92.6471` | `0.0735` | `0.2057` | `8.3333` | `0.3333` | `0.4552` | `w=320`, `fps=8.0`, `thr=36`, `blur=5`, `area=400`, `dilate=2`, `gap=0.5` |
| 2 | `manual_profiles` | `low_cpu` | `90.3681` | `92.6471` | `0.0735` | `0.1867` | `8.3333` | `0.3333` | `0.4357` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5` |
| 3 | `random_search` | `random_search_best` | `88.3826` | `92.6471` | `0.0735` | `0.1677` | `8.3333` | `0.3333` | `0.4321` | `w=320`, `fps=8.0`, `thr=32`, `blur=3`, `area=500`, `dilate=1`, `gap=0.7` |

Lectura rapida:

- PSO queda arriba por `0.6968` puntos sobre el perfil manual `low_cpu`.
- Las tres mejores configuraciones comparten el mismo costo de recursos:
  `resolution_width=320`, `effective_processed_fps=8.3333` y
  `processed_frame_ratio=0.3333`.
- La mejora de PSO viene de acercarse mas al ratio objetivo (`0.20`) y reducir
  fragmentacion (`0.0923`) con un costo de procesamiento todavia bajo.

## Mejor perfil manual low_cpu

| Rank | Profile | Score | Motion frames | Raw events | Events | Avg ms | Resource | Motion ratio |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `low_cpu` | `90.3681` | `59` | `7` | `3` | `0.4357` | `92.6471` | `0.1867` |
| 2 | `baseline` | `73.8257` | `103` | `9` | `4` | `0.5891` | `58.2353` | `0.2173` |
| 3 | `strict` | `72.6164` | `67` | `6` | `3` | `0.5444` | `58.2353` | `0.1414` |
| 4 | `sensitive` | `70.1430` | `144` | `13` | `3` | `0.5957` | `58.2353` | `0.3038` |
| 5 | `random_balanced_best` | `63.0781` | `241` | `15` | `2` | `0.5102` | `33.7500` | `0.2542` |
| 6 | `back_person_sensitive` | `54.1178` | `302` | `13` | `3` | `0.5743` | `22.5000` | `0.3186` |

## Resultado manual MOG2

Comandos ejecutados con `--method mog2` sobre
`datasets/videos/workers_hallway.mp4`. En ambos objetivos gano el perfil
manual `low_cpu`; las metricas de deteccion son iguales porque la configuracion
ganadora es la misma y solo cambia la ponderacion del objetivo.

| Objetivo | Mejor perfil | Score | Motion frames | Raw events | Events | Avg ms | Resource | Motion ratio | Configuracion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `sensitive` | `low_cpu` | `81.6724` | `98` | `10` | `6` | `1.8205` | `92.6471` | `0.3101` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5`, `history=120`, `var=25.0`, `shadows=true`, `warmup=5` |
| `low_cpu` | `low_cpu` | `78.1945` | `98` | `10` | `6` | `1.7969` | `92.6471` | `0.3101` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5`, `history=120`, `var=25.0`, `shadows=true`, `warmup=5` |

Lectura rapida:

- `sensitive` da mas score que `low_cpu` para la misma deteccion porque el
  ratio `0.3101` queda mas cerca del comportamiento buscado por el objetivo
  sensible.
- El costo estimado es bajo: `effective_processed_fps=8.3333`,
  `processed_frame_ratio=0.3333` y `resource_cost=0.0735`.
- MOG2 detecta mas movimiento que el perfil manual `low_cpu` historico con
  `frame_diff` (`motion_ratio=0.3101` vs `0.1867`), a cambio de mas tiempo por
  frame (`~1.8 ms` vs `~0.44 ms`).

## Comandos usados para reproducir

Evaluar perfiles:

```bash
python apps/cli/evaluate_configs.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective low_cpu \
  --method frame_diff \
  --write-videos
```

Evaluar perfiles con MOG2:

```bash
python apps/cli/evaluate_configs.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective sensitive \
  --method mog2 \
  --write-videos

python apps/cli/evaluate_configs.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective low_cpu \
  --method mog2 \
  --write-videos
```

Random search:

```bash
python apps/cli/random_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective low_cpu \
  --iterations 100 \
  --seed 42 \
  --write-best-video
```

PSO:

```bash
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
  --objectives low_cpu \
  --methods frame_diff \
  --output-json outputs/reports/optimizer_comparison.json \
  --output-csv outputs/reports/optimizer_comparison.csv
```

Comparar por metodo de deteccion:

```bash
python apps/cli/compare_optimizers.py \
  --reports-dir outputs/reports \
  --objectives sensitive low_cpu \
  --methods frame_diff mog2 \
  --output-json outputs/reports/optimizer_comparison.json \
  --output-csv outputs/reports/optimizer_comparison.csv
```

## Lectura de columnas

- `w`: ancho objetivo del frame procesado.
- `fps`: FPS solicitados para muestreo.
- `thr`: threshold de diferencia de pixeles.
- `blur`: kernel de Gaussian blur.
- `area`: area minima de contorno.
- `dilate`: iteraciones de dilatacion.
- `gap`: segundos de hueco sin movimiento para fusionar eventos.
- `motion_ratio`: `motion_frames / processed_frames`.
- `avg_ms`: tiempo promedio de procesamiento por frame.
- `resource_score`: score de recursos; mas alto significa menor costo estimado.
- `resource_cost`: proxy normalizado de costo entre `0` y `1`.
- `effective_processed_fps`: FPS realmente procesado segun frames procesados y duracion del video.
- `processed_frame_ratio`: proporcion de frames fuente que fueron procesados.
- `detector_method`: metodo de deteccion usado, por ejemplo `frame_diff` o
  `mog2`.
- `method_rank`: posicion dentro del mismo `objective` y `detector_method`.

Los CSV de perfiles, random search, PSO y comparacion incluyen las columnas de
recursos. El CSV de PSO tambien incluye `source`; el CSV del comparador agrega
`objective`, `detector_method`, `method_rank`, `method`, `name` y
`source_file`.
