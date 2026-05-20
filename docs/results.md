# Resultados de optimizacion

Este documento resume los resultados locales guardados en `outputs/reports/`.
Los reportes y videos no se versionan porque `outputs/` esta ignorado por git.

El snapshot actualizado combina la nueva corrida de `balanced` con
`--methods frame_diff mog2`, reportes existentes de `sensitive` y `low_cpu` con
`frame_diff`, y el comparativo de perfiles manuales con `mog2`. Las corridas
nuevas de `random_search` y `pso_search` guardan el detector usado en
`detector_method`.

## Contexto de ejecucion

- Video usado: `datasets/videos/workers_hallway.mp4`
- Frames fuente: `948`
- FPS fuente: `25.0`
- Objetivos comparados: `balanced`, `sensitive`, `low_cpu`
- Metodos comparados: `frame_diff`, `mog2`
- Random search `balanced`: `100` iteraciones, seed `42`, `--methods frame_diff mog2`
- PSO `balanced`: `12` particulas, `10` iteraciones, seed `42`, `--methods frame_diff mog2`
- Reportes existentes `sensitive` y `low_cpu`: `frame_diff`, `100` iteraciones
  para random search y `12 x 10` para PSO
- Comparador final: `apps/cli/compare_optimizers.py --objectives balanced sensitive low_cpu --methods frame_diff mog2`

## Reportes generados

| Tipo | JSON | CSV |
| --- | --- | --- |
| Perfiles manuales | `outputs/reports/evaluation_summary_<objective>_<method>.json` | `outputs/reports/evaluation_ranking_<objective>_<method>.csv` |
| Random search | `outputs/reports/random_search_<objective>.json` | `outputs/reports/random_search_<objective>.csv` |
| PSO | `outputs/reports/pso_search_<objective>.json` | `outputs/reports/pso_search_<objective>.csv` |
| Comparacion final | `outputs/reports/optimizer_comparison.json` | `outputs/reports/optimizer_comparison.csv` |

Nota: los reportes antiguos de `frame_diff` pueden existir sin sufijo de metodo.
El comparador los sigue leyendo como fallback para mantener compatibilidad.

## Ganadores por objetivo

| Objetivo | Detector | Optimizador | Nombre | Score | Resource | Eff FPS | Frame ratio | Configuracion |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `balanced` | `frame_diff` | `random_search` | `random_search_best` | `89.7032` | `92.6471` | `8.3333` | `0.3333` | `w=320`, `fps=8.0`, `thr=28`, `blur=5`, `area=300`, `dilate=2`, `gap=0.5` |
| `sensitive` | `frame_diff` | `random_search` | `random_search_best` | `90.5733` | `58.2353` | `12.5` | `0.5` | `w=640`, `fps=10.0`, `thr=28`, `blur=3`, `area=250`, `dilate=1`, `gap=0.3` |
| `low_cpu` | `frame_diff` | `seeded_pso` | `pso_best` | `91.0673` | `92.6471` | `8.3333` | `0.3333` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=450`, `dilate=2`, `gap=0.6` |

Lectura rapida:

- `balanced` queda practicamente empatado entre random search y PSO:
  `89.7032` contra `89.6983`. Random search gana por `0.0049` puntos y usa una
  configuracion mas barata en recursos.
- `sensitive` favorece random search porque llega al ratio buscado
  (`motion_ratio=0.3249`) con mejor ranking global que PSO.
- `low_cpu` favorece PSO porque mantiene el costo bajo
  (`resource_score=92.6471`) y queda mas cerca del ratio objetivo de `0.20`.

## Ranking completo del comparador

| Objetivo | Rank | Detector | Optimizador | Nombre | Score | Motion ratio | Resource | Eff FPS | Avg ms | Configuracion |
| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `balanced` | 1 | `frame_diff` | `random_search` | `random_search_best` | `89.7032` | `0.2658` | `92.6471` | `8.3333` | `0.4601` | `w=320`, `fps=8.0`, `thr=28`, `blur=5`, `area=300`, `dilate=2`, `gap=0.5` |
| `balanced` | 2 | `frame_diff` | `seeded_pso` | `pso_best` | `89.6983` | `0.2468` | `69.4853` | `12.5` | `0.5960` | `w=480`, `fps=15.0`, `thr=33`, `blur=3`, `area=900`, `dilate=3`, `gap=0.5` |
| `balanced` | 3 | `frame_diff` | `manual_profiles` | `random_balanced_best` | `86.7209` | `0.2542` | `33.7500` | `25.0` | `0.5625` | `w=480`, `fps=18.0`, `thr=32`, `blur=3`, `area=300`, `dilate=3`, `gap=0.5` |
| `balanced` | 4 | `mog2` | `manual_profiles` | `low_cpu` | `74.4352` | `0.3101` | `92.6471` | `8.3333` | `2.0985` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5` |
| `sensitive` | 1 | `frame_diff` | `random_search` | `random_search_best` | `90.5733` | `0.3249` | `58.2353` | `12.5` | `0.6190` | `w=640`, `fps=10.0`, `thr=28`, `blur=3`, `area=250`, `dilate=1`, `gap=0.3` |
| `sensitive` | 2 | `frame_diff` | `seeded_pso` | `pso_best` | `90.2002` | `0.3249` | `58.2353` | `12.5` | `0.6000` | `w=640`, `fps=15.0`, `thr=26`, `blur=3`, `area=550`, `dilate=2`, `gap=0.5` |
| `sensitive` | 3 | `frame_diff` | `manual_profiles` | `back_person_sensitive` | `89.6053` | `0.3186` | `22.5000` | `25.0` | `0.5931` | `w=640`, `fps=25.0`, `thr=22`, `blur=3`, `area=300`, `dilate=2`, `gap=0.5` |
| `sensitive` | 4 | `mog2` | `manual_profiles` | `low_cpu` | `81.6724` | `0.3101` | `92.6471` | `8.3333` | `1.8205` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5` |
| `low_cpu` | 1 | `frame_diff` | `seeded_pso` | `pso_best` | `91.0673` | `0.2057` | `92.6471` | `8.3333` | `0.4546` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=450`, `dilate=2`, `gap=0.6` |
| `low_cpu` | 2 | `frame_diff` | `manual_profiles` | `low_cpu` | `90.3345` | `0.1867` | `92.6471` | `8.3333` | `0.4441` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5` |
| `low_cpu` | 3 | `frame_diff` | `random_search` | `random_search_best` | `88.0914` | `0.1677` | `92.6471` | `8.3333` | `0.5049` | `w=320`, `fps=8.0`, `thr=32`, `blur=3`, `area=500`, `dilate=1`, `gap=0.7` |
| `low_cpu` | 4 | `mog2` | `manual_profiles` | `low_cpu` | `78.1945` | `0.3101` | `92.6471` | `8.3333` | `1.7969` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5` |

## Corridas nuevas de balanced

Se regenero `balanced` con `--methods frame_diff mog2`, `100` iteraciones para
random search y PSO con `12` particulas por `10` iteraciones.

| Optimizador | Detector | Score | Resource | Motion ratio | Eff FPS | Configuracion | Video |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `random_search` | `frame_diff` | `89.7032` | `92.6471` | `0.2658` | `8.3333` | `w=320`, `fps=8.0`, `thr=28`, `blur=5`, `area=300`, `dilate=2`, `gap=0.5` | `outputs/videos/random_search_best_balanced_frame_diff.mp4` |
| `seeded_pso` | `frame_diff` | `89.6983` | `69.4853` | `0.2468` | `12.5` | `w=480`, `fps=15.0`, `thr=33`, `blur=3`, `area=900`, `dilate=3`, `gap=0.5` | `outputs/videos/pso_best_balanced_frame_diff.mp4` |

Top 10 de random search `balanced`:

| Rank | Detector | Score | Resource | Resolucion | FPS | Threshold | Blur | Area | Motion frames | Raw events | Events | Avg ms |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `frame_diff` | `89.7032` | `92.6471` | `320` | `8.0` | `28` | `5` | `300` | `84` | `8` | `3` | `0.4601` |
| 2 | `frame_diff` | `87.6195` | `70.1471` | `640` | `8.0` | `40` | `3` | `1500` | `82` | `12` | `2` | `0.5738` |
| 3 | `frame_diff` | `87.3828` | `81.3971` | `480` | `8.0` | `40` | `5` | `800` | `79` | `9` | `4` | `0.7905` |
| 4 | `frame_diff` | `86.0303` | `92.6471` | `320` | `8.0` | `18` | `3` | `300` | `92` | `12` | `3` | `0.4463` |
| 5 | `frame_diff` | `85.0228` | `69.4853` | `480` | `12.0` | `32` | `3` | `1200` | `105` | `11` | `3` | `0.6356` |
| 6 | `frame_diff` | `84.0528` | `46.9853` | `800` | `15.0` | `45` | `7` | `650` | `113` | `6` | `3` | `1.1132` |
| 7 | `frame_diff` | `83.5810` | `58.2353` | `640` | `15.0` | `22` | `7` | `650` | `99` | `5` | `3` | `0.6979` |
| 8 | `frame_diff` | `83.3880` | `69.4853` | `480` | `12.0` | `22` | `7` | `250` | `144` | `11` | `2` | `0.8063` |
| 9 | `frame_diff` | `83.3853` | `45.0000` | `320` | `25.0` | `22` | `3` | `400` | `215` | `17` | `4` | `0.4451` |
| 10 | `frame_diff` | `82.4621` | `35.7353` | `960` | `10.0` | `45` | `7` | `650` | `111` | `3` | `3` | `1.2739` |

Top 10 de PSO `balanced`:

| Rank | Detector | Score | Resource | Resolucion | FPS | Threshold | Blur | Area | Motion frames | Raw events | Events | Avg ms |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `frame_diff` | `89.6983` | `69.4853` | `480` | `15.0` | `33` | `3` | `900` | `117` | `10` | `2` | `0.5960` |
| 2 | `frame_diff` | `89.5935` | `69.4853` | `480` | `15.0` | `34` | `3` | `900` | `117` | `10` | `2` | `0.6222` |
| 3 | `frame_diff` | `89.4747` | `69.4853` | `480` | `15.0` | `35` | `3` | `850` | `117` | `11` | `2` | `0.5985` |
| 4 | `frame_diff` | `89.2559` | `69.4853` | `480` | `15.0` | `35` | `3` | `900` | `116` | `11` | `2` | `0.5888` |
| 5 | `frame_diff` | `89.2082` | `69.4853` | `480` | `15.0` | `33` | `3` | `550` | `114` | `9` | `2` | `0.5813` |
| 6 | `frame_diff` | `89.1890` | `69.4853` | `480` | `15.0` | `33` | `3` | `850` | `121` | `11` | `2` | `0.6300` |
| 7 | `frame_diff` | `88.9928` | `69.4853` | `480` | `15.0` | `35` | `3` | `800` | `120` | `13` | `2` | `0.6295` |
| 8 | `frame_diff` | `88.9223` | `69.4853` | `480` | `15.0` | `36` | `3` | `900` | `115` | `11` | `2` | `0.6077` |
| 9 | `frame_diff` | `88.5483` | `58.2353` | `640` | `15.0` | `37` | `3` | `1100` | `118` | `12` | `2` | `0.5602` |
| 10 | `frame_diff` | `88.1844` | `69.4853` | `480` | `12.0` | `35` | `3` | `550` | `111` | `10` | `2` | `0.5896` |

## Resultado manual MOG2

Comandos ejecutados con `--method mog2` sobre
`datasets/videos/workers_hallway.mp4`. En los tres objetivos gano el perfil
manual `low_cpu`; las metricas de deteccion son iguales porque la configuracion
ganadora es la misma y solo cambia la ponderacion del objetivo.

| Objetivo | Mejor perfil | Score | Motion frames | Raw events | Events | Avg ms | Resource | Motion ratio | Configuracion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `balanced` | `low_cpu` | `74.4352` | `98` | `10` | `6` | `2.0985` | `92.6471` | `0.3101` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5`, `history=120`, `var=25.0`, `shadows=true`, `warmup=5` |
| `sensitive` | `low_cpu` | `81.6724` | `98` | `10` | `6` | `1.8205` | `92.6471` | `0.3101` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5`, `history=120`, `var=25.0`, `shadows=true`, `warmup=5` |
| `low_cpu` | `low_cpu` | `78.1945` | `98` | `10` | `6` | `1.7969` | `92.6471` | `0.3101` | `w=320`, `fps=8.0`, `thr=35`, `blur=5`, `area=500`, `dilate=2`, `gap=0.5`, `history=120`, `var=25.0`, `shadows=true`, `warmup=5` |

Lectura rapida:

- `sensitive` da mas score que `balanced` y `low_cpu` para la misma deteccion
  porque el ratio `0.3101` queda mas cerca del comportamiento buscado por el
  objetivo sensible.
- El costo estimado es bajo: `effective_processed_fps=8.3333`,
  `processed_frame_ratio=0.3333` y `resource_cost=0.0735`.
- MOG2 detecta mas movimiento que el perfil manual `low_cpu` historico con
  `frame_diff` (`motion_ratio=0.3101` vs `0.1867`), a cambio de mas tiempo por
  frame (`~1.8 ms` vs `~0.44 ms`).

## Comandos usados en esta ronda

PSO `balanced` con ambos detectores:

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

Random search `balanced` con ambos detectores:

```bash
python apps/cli/random_search.py \
  --input datasets/videos/workers_hallway.mp4 \
  --objective balanced \
  --methods frame_diff mog2 \
  --iterations 100 \
  --seed 42 \
  --write-best-video
```

Comparar contra todos los reportes disponibles:

```bash
python apps/cli/compare_optimizers.py \
  --reports-dir outputs/reports \
  --objectives balanced sensitive low_cpu \
  --methods frame_diff mog2
```

## Regenerar todo desde cero

Si se quiere reconstruir el comparador completo con la version nueva de
`--methods`, se pueden regenerar todos los objetivos:

```bash
for objective in balanced sensitive low_cpu; do
  python apps/cli/evaluate_configs.py \
    --input datasets/videos/workers_hallway.mp4 \
    --objective "$objective" \
    --method frame_diff

  python apps/cli/evaluate_configs.py \
    --input datasets/videos/workers_hallway.mp4 \
    --objective "$objective" \
    --method mog2

  python apps/cli/random_search.py \
    --input datasets/videos/workers_hallway.mp4 \
    --objective "$objective" \
    --methods frame_diff mog2 \
    --iterations 100 \
    --seed 42

  python apps/cli/pso_search.py \
    --input datasets/videos/workers_hallway.mp4 \
    --objective "$objective" \
    --methods frame_diff mog2 \
    --particles 12 \
    --iterations 10 \
    --seed 42
done
```

Luego:

```bash
python apps/cli/compare_optimizers.py \
  --reports-dir outputs/reports \
  --objectives balanced sensitive low_cpu \
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
