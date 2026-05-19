# Arquitectura tecnica

## Componentes

El proyecto esta separado en dos capas:

- `core/motion/`: logica reutilizable de deteccion, evaluacion, optimizacion y comparacion.
- `apps/cli/`: comandos ejecutables para correr cada flujo desde terminal.

La capa CLI solo parsea argumentos, llama al core y renderiza tablas o mensajes.
La capa core contiene el comportamiento que se puede probar o reutilizar desde
otros frontends.

## Flujo de deteccion

Entrada principal: `core.motion.detector.detect_motion()`.

Configuracion: `MotionConfig`.

Campos optimizables:

| Campo | Uso |
| --- | --- |
| `resolution_width` | Ancho al que se redimensiona cada frame antes de procesar. |
| `fps_sample` | FPS objetivo a procesar del video fuente. |
| `motion_threshold` | Threshold binario aplicado a la diferencia entre frames. |
| `blur_kernel` | Kernel de Gaussian blur; si llega par, se ajusta a impar. |
| `min_contour_area` | Area minima para considerar movimiento relevante. |
| `dilate_iterations` | Iteraciones de dilatacion para unir regiones de movimiento. |
| `event_merge_gap_seconds` | Gap maximo para fusionar eventos separados por pausas cortas. |

Pipeline:

1. Abrir video con `cv2.VideoCapture`.
2. Calcular `frame_interval` con base en FPS fuente y `fps_sample`.
3. Leer frames y saltar los que no correspondan al muestreo.
4. Redimensionar conservando aspecto.
5. Convertir a grayscale.
6. Aplicar Gaussian blur.
7. Comparar contra el frame anterior con `cv2.absdiff`.
8. Threshold, dilatacion y `cv2.findContours`.
9. Filtrar contornos por `min_contour_area`.
10. Contar frames con movimiento, eventos crudos y eventos fusionados.
11. Medir tiempo promedio por frame.
12. Generar video anotado si `output_video_path` viene definido.

## Metricas producidas

`detect_motion()` regresa un diccionario con:

- `video`: path, FPS fuente, frames fuente, frames leidos, intervalo efectivo y FPS procesado.
- `config`: copia serializable de `MotionConfig`.
- `metrics`: frames procesados, frames con movimiento, eventos, tiempo promedio y FPS estimado.
- `output`: path del video anotado cuando aplica.

Metricas clave:

| Metrica | Significado |
| --- | --- |
| `processed_frames` | Frames realmente evaluados despues del muestreo. |
| `motion_frames` | Frames procesados donde hubo al menos un contorno valido. |
| `raw_motion_events` | Transiciones directas de no movimiento a movimiento. |
| `motion_events` | Eventos despues de fusionar gaps cortos sin movimiento. |
| `avg_processing_ms` | Tiempo promedio de procesamiento por frame. |
| `estimated_processing_fps` | FPS estimado a partir de `avg_processing_ms`. |

## Scoring

Entrada principal: `core.motion.evaluator.calculate_score()`.

El score es heuristico. No reemplaza una evaluacion con etiquetas reales. Usa:

- `motion_ratio = motion_frames / processed_frames`
- `events_per_minute`
- `fragmentation = raw_motion_events / motion_frames`
- `avg_processing_ms`

Cada objetivo cambia pesos y ratio esperado:

| Objetivo | Ratio objetivo | Peso ratio | Peso estabilidad | Peso rendimiento |
| --- | ---: | ---: | ---: | ---: |
| `balanced` | `0.25` | `0.45` | `0.30` | `0.25` |
| `sensitive` | `0.32` | `0.50` | `0.15` | `0.35` |
| `low_cpu` | `0.20` | `0.30` | `0.20` | `0.50` |

Componentes:

- `ratio_score`: premia estar cerca del ratio objetivo.
- `stability_score`: penaliza eventos por minuto altos y fragmentacion.
- `performance_score`: penaliza mayor `avg_processing_ms`.
- `final_score`: combinacion ponderada de los tres componentes.

## Perfiles manuales

Entrada principal: `core.motion.evaluator.evaluate_profiles()`.

Evalua los perfiles definidos en `get_default_profiles()`:

- `baseline`
- `random_balanced_best`
- `strict`
- `sensitive`
- `low_cpu`
- `back_person_sensitive`

Cada perfil se ejecuta con `detect_motion()`, recibe score con
`calculate_score()` y se ordena de mayor a menor `final_score`.

Salidas:

- Reporte individual por perfil: `outputs/reports/<profile>_evaluation.json`
- Resumen por objetivo: `outputs/reports/evaluation_summary_<objective>.json`
- Ranking CSV: `outputs/reports/evaluation_ranking_<objective>.csv`

## Random search

Entrada principal: `core.motion.optimizer.run_random_search()`.

El espacio de busqueda esta en `get_default_search_space()`:

| Parametro | Valores |
| --- | --- |
| `resolution_widths` | `320`, `480`, `640`, `800`, `960` |
| `fps_samples` | `8`, `10`, `12`, `15`, `18`, `20`, `25` |
| `motion_thresholds` | `18`, `22`, `25`, `28`, `32`, `35`, `40`, `45`, `50` |
| `blur_kernels` | `3`, `5`, `7` |
| `min_contour_areas` | `250`, `300`, `400`, `500`, `650`, `800`, `1000`, `1200`, `1500` |
| `dilate_iterations` | `1`, `2`, `3` |
| `event_merge_gap_seconds` | `0.3`, `0.5`, `0.7` |

Algoritmo:

1. Crear generador `random.Random(seed)`.
2. Muestrear una configuracion del espacio discreto.
3. Evitar duplicados con firma de configuracion.
4. Ejecutar `detect_motion()`.
5. Calcular score.
6. Repetir hasta `iterations` o `iterations * 10` intentos.
7. Ordenar por `final_score`.
8. Guardar JSON y CSV.

## PSO

Entrada principal: `core.motion.pso_optimizer.run_pso_search()`.

PSO trabaja con vectores continuos y luego los decodifica a valores validos de
`MotionConfig`.

Bounds:

| Dimension | Min | Max |
| --- | ---: | ---: |
| `resolution_width` | `320` | `960` |
| `fps_sample` | `8` | `25` |
| `motion_threshold` | `18` | `50` |
| `blur_kernel` | `3` | `7` |
| `min_contour_area` | `250` | `1500` |
| `dilate_iterations` | `1` | `3` |
| `event_merge_gap_seconds` | `0.3` | `0.7` |

Decodificacion:

- Resolucion, FPS y blur se ajustan al valor permitido mas cercano.
- `motion_threshold` se redondea y limita al rango.
- `min_contour_area` se redondea en pasos de `50`.
- `event_merge_gap_seconds` se redondea a un decimal.

Semillas conocidas:

- `random_balanced_best`
- `back_person_sensitive`
- `low_cpu`
- `baseline`

Las semillas cambian por objetivo y se pueden desactivar con `--no-seeds`.

Parametros default:

- `particles_count=10`
- `iterations=8`
- `seed=42`
- `inertia_weight=0.65`
- `cognitive_weight=1.5`
- `social_weight=1.5`
- `use_seed_configs=True`

## Comparador

Entrada principal: `core.motion.comparator.compare_optimizers()`.

El comparador no corre deteccion otra vez. Lee los JSON ya generados:

- `evaluation_summary_<objective>.json`
- `random_search_<objective>.json`
- `pso_search_<objective>.json`

Normaliza cada ganador a una estructura comun, ordena por `final_score` y
genera:

- `outputs/reports/optimizer_comparison.json`
- `outputs/reports/optimizer_comparison.csv`

## Limitaciones actuales

- El score es heuristico y depende del video usado.
- No hay ground truth ni precision/recall contra etiquetas humanas.
- El tiempo promedio puede variar entre ejecuciones por carga de maquina.
- `outputs/` y videos estan ignorados; para reproducir resultados se deben volver a correr los comandos.
