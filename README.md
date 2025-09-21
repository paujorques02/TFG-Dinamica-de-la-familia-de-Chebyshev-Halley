# Dinámica de la familia de Chebyshev–Halley

Este repositorio contiene los programas desarrollados para el estudio de la dinámica compleja de la **familia de operadores de Chebyshev–Halley**.  
Los scripts permiten generar tanto **planos dinámicos** como **planos de parámetros**, así como visualizar los resultados mediante interfaces gráficas simples.

---

## 📂 Estructura del repositorio

```
├── cheby_halley_dinamico.py       # Generación de planos dinámicos (CLI + GUI básica)
├── cheby_halley_dinamico_gui.py   # Interfaz gráfica avanzada para planos dinámicos
├── cheby_halley_parametros.py     # Generación del plano de parámetros
├── imagenes/                      # Carpeta donde se guardan las imágenes generadas
└── README.md                      # Este archivo
```

---

## ⚙️ Dependencias

Los scripts están implementados en **Python 3** y requieren las siguientes librerías:

- [Pillow](https://pypi.org/project/Pillow/)  
- [tkinter](https://docs.python.org/3/library/tkinter.html) (incluida en la mayoría de instalaciones de Python)

Instalación rápida:

```bash
pip install pillow
```

---

## ▶️ Uso

### 1. Plano dinámico (con parámetros desde línea de comandos o GUI básica)

```bash
python cheby_halley_dinamico.py --alpha-re -0.3 --alpha-im 0.0 --width 1200 --height 800
```

Si no se pasan argumentos, se abrirá una pequeña ventana para introducir los parámetros.

Los resultados se guardan en la carpeta `imagenes/`.

---

### 2. Plano dinámico con interfaz gráfica avanzada

```bash
python cheby_halley_dinamico_gui.py
```

Se abrirá una interfaz con:

- Configuración de **α** (parte real e imaginaria).  
- Rango de visualización en el plano complejo.  
- Resolución de la imagen.  
- Condiciones de parada (iteraciones máximas, tolerancias).  
- Opciones de color y modos de cuencas.  
- Posibilidad de **previsualizar y guardar la imagen**.

---

### 3. Plano de parámetros

```bash
python cheby_halley_parametros.py
```

Genera y guarda el **plano de parámetros** en la carpeta `imagenes/`.

---

## 📊 Ejemplos de resultados

En la carpeta [`imagenes/`](./imagenes) se incluyen ejemplos generados de:

- **Planos dinámicos** para distintos valores de α.  
- **Plano de parámetros** de la familia Chebyshev–Halley.

