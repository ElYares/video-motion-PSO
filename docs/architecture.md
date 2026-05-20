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
| `method` | Metodo de deteccion: `frame_diff` o `mog2`. |
| `resolution_width` | Ancho al que se redimensiona cada frame antes de procesar. |
| `fps_sample` | FPS objetivo a procesar del video fuente. |
| `motion_threshold` | Threshold binario aplicado a la diferencia entre frames. |
| `blur_kernel` | Kernel de Gaussian blur; si llega par, se ajusta a impar. |
| `min_contour_area` | Area minima para considerar movimiento relevante. |
| `dilate_iterations` | Iteraciones de dilatacion para unir regiones de movimiento. |
| `event_merge_gap_seconds` | Gap maximo para fusionar eventos separados por pausas cortas. |

Campos especificos de `mog2`:

| Campo | Uso |
| --- | --- |
| `mog2_history` | Longitud de historial del sustractor de fondo. |
| `mog2_var_threshold` | Umbral de varianza de MOG2. |
| `mog2_detect_shadows` | Activa deteccion de sombras de OpenCV. |
| `mog2_learning_rate` | Tasa de aprendizaje; `-1.0` deja que OpenCV la ajuste. |
| `mog2_warmup_frames` | Frames iniciales usados para estabilizar el fondo. |

Pipeline:

1. Abrir video con `cv2.VideoCapture`.
2. Calcular `frame_interval` con base en FPS fuente y `fps_sample`.
3. Leer frames y saltar los que no correspondan al muestreo.
4. Redimensionar conservando aspecto.
5. Convertir a grayscale.
6. Aplicar Gaussian blur.
7. Detectar movimiento con `cv2.absdiff` si `method=frame_diff`, o con
   `cv2.createBackgroundSubtractorMOG2` si `method=mog2`.
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
- `resource_score`, calculado como proxy de costo de recursos

El costo de recursos se calcula en `core.motion.evaluator._calculate_resource_score()`.
El score favorece configuraciones mas ligeras usando tres senales normalizadas:

- `resolution_width`: ancho procesado, normalizado entre `320` y `960`.
- `effective_processed_fps`: FPS realmente procesado segun duracion del video.
- `processed_frame_ratio`: `processed_frames / source_frame_count`.

Formula:

```txt
resource_cost = width_ratio * 0.45 + fps_ratio * 0.35 + processed_frame_ratio * 0.20
resource_score = 100 - resource_cost * 100
```

`resource_cost` queda entre `0` y `1`; `resource_score` queda entre `0` y
`100`, donde un valor mas alto significa menor costo estimado.

Cada objetivo cambia pesos y ratio esperado:

| Objetivo | Ratio objetivo | Peso ratio | Peso estabilidad | Peso rendimiento | Peso recursos |
| --- | ---: | ---: | ---: | ---: | ---: |
| `balanced` | `0.25` | `0.45` | `0.25` | `0.20` | `0.10` |
| `sensitive` | `0.32` | `0.50` | `0.15` | `0.30` | `0.05` |
| `low_cpu` | `0.20` | `0.20` | `0.15` | `0.20` | `0.45` |

Componentes:

- `ratio_score`: premia estar cerca del ratio objetivo.
- `stability_score`: penaliza eventos por minuto altos y fragmentacion.
- `performance_score`: penaliza mayor `avg_processing_ms`.
- `resource_score`: premia menor costo estimado de resolucion, FPS efectivo y proporcion de frames procesados.
- `final_score`: combinacion ponderada de los cuatro componentes.

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

- Reporte individual por perfil: `outputs/reports/<method>_<profile>_evaluation.json`
- Resumen por objetivo: `outputs/reports/evaluation_summary_<objective>_<method>.json`
- Ranking CSV: `outputs/reports/evaluation_ranking_<objective>_<method>.csv`

## Random search

Entrada principal: `core.motion.optimizer.run_random_search()`.

El espacio de busqueda esta en `get_default_search_space()`. El metodo de
deteccion se elige desde la lista recibida por CLI con `--methods`.

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
2. Muestrear una configuracion del espacio discreto y un `method` de
   `--methods`.
3. Evitar duplicados con firma de configuracion, incluyendo `method`.
4. Ejecutar `detect_motion()`.
5. Calcular score.
6. Repetir hasta `iterations` o `iterations * 10` intentos.
7. Ordenar por `final_score`.
8. Guardar JSON y CSV.

El JSON guarda `methods` y cada resultado guarda `config.method`. El CSV agrega
`detector_method`. Si se pide `--write-best-video`, el archivo queda con sufijo
del detector: `random_search_best_<objective>_<method>.mp4`.

## PSO

Entrada principal: `core.motion.pso_optimizer.run_pso_search()`.

PSO trabaja con vectores continuos y luego los decodifica a valores validos de
`MotionConfig`. El metodo de deteccion no forma parte del vector numerico; cada
particula conserva el `detector_method` asignado al crearse.

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

Las semillas cambian por objetivo, se expanden sobre todos los metodos pedidos
con `--methods` y se pueden desactivar con `--no-seeds`.

Parametros default:

- `particles_count=10`
- `iterations=8`
- `seed=42`
- `inertia_weight=0.65`
- `cognitive_weight=1.5`
- `social_weight=1.5`
- `use_seed_configs=True`
- `detector_methods=["frame_diff"]`

El JSON guarda `detector_methods`, `methods_suffix` y cada resultado guarda
`config.method`. El CSV agrega `detector_method`. Si se pide
`--write-best-video`, el archivo queda con sufijo del detector:
`pso_best_<objective>_<method>.mp4`.

## Comparador

Entrada principal: `core.motion.comparator.compare_optimizers()`.

El comparador no corre deteccion otra vez. Lee los JSON ya generados:

- `evaluation_summary_<objective>_<method>.json`
- `random_search_<objective>.json`
- `pso_search_<objective>.json`

Para `frame_diff`, tambien acepta reportes antiguos sin sufijo de metodo como
fallback. Normaliza cada ganador a una estructura comun, agrega
`detector_method`, ordena por `final_score` y genera:

- `outputs/reports/optimizer_comparison.json`
- `outputs/reports/optimizer_comparison.csv`

La salida mantiene un ranking general por objetivo y agrega un desglose por
metodo de deteccion en `comparison[objective]["methods"][detector_method]`.

La tabla CLI y el CSV del comparador incluyen las columnas de recursos:

- `detector_method`
- `method_rank`
- `resource_score`
- `resource_cost`
- `effective_processed_fps`
- `processed_frame_ratio`

## Limitaciones actuales

- El score es heuristico y depende del video usado.
- No hay ground truth ni precision/recall contra etiquetas humanas.
- El tiempo promedio puede variar entre ejecuciones por carga de maquina.
- `outputs/` y videos estan ignorados; para reproducir resultados se deben volver a correr los comandos.
