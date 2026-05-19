# Video Motion Optimizer

Proyecto experimental para optimizar parámetros de detección de movimiento en video, buscando buen balance entre precisión y bajo consumo de CPU.

## Objetivo

Detectar movimiento en videos usando OpenCV y optimizar parámetros como:

- Resolución
- FPS procesados
- Threshold de movimiento
- Kernel de blur
- Área mínima de contorno

## Stack inicial

- Python
- OpenCV
- NumPy
- PSO / búsqueda heurística
- Futuro core en C++ con OpenCV + pybind11

## Estructura

```txt
video-motion-optimizer/
├── apps/
│   └── cli/
├── core/
│   └── motion/
├── datasets/
│   └── videos/
├── outputs/
│   ├── frames/
│   ├── reports/
│   └── videos/
└── docs/
