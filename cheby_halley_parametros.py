import cmath
import os
import colorsys
from PIL import Image

# =====================================
# CONFIGURACIÓN GENERAL DEL PROGRAMA
# =====================================

# Dimensiones y rango en el plano complejo
X_MIN, X_MAX = -0.4, 4.6
Y_MIN, Y_MAX = -2.0, 2.0
WIDTH, HEIGHT = 1500, 1200

# Parámetros de iteración
ITER_MAX = 150
EPS = 1e-4
EPS_INV = 1 / EPS

# Archivo de salida
FILENAME = "imagenes/plano_parametros.png"
GUARDAR = True


# =====================================
# FUNCIONES AUXILIARES
# =====================================

def paleta_colores(n):
    """Devuelve una lista de colores (RGB) generada en el espacio HSV."""
    return [
        tuple(int(255 * c) for c in colorsys.hsv_to_rgb(k / n, 1.0, 1.0))
        for k in range(n)
    ]


def critico_secundario(alpha):
    """Cálculo de un punto crítico no trivial."""
    num = 3 - 4 * alpha + 2 * alpha**2
    disc = -6 * alpha + 19 * alpha**2 - 16 * alpha**3 + 4 * alpha**4
    raiz = cmath.sqrt(disc)
    den = 3 * (alpha - 1)
    if abs(den) < 1e-12:
        return None
    return (num + raiz) / den


def operador(z, alpha):
    """Operador normalizado de la familia Chebyshev-Halley."""
    numer = z**3 * (z - 2 * (alpha - 1))
    denom = 1 - 2 * (alpha - 1) * z
    if abs(denom) < 1e-12:
        return float("inf")  # Divergencia
    return numer / denom


def construir_imagen():
    """Genera la imagen del espacio de parámetros."""
    colores = paleta_colores(ITER_MAX)
    imagen = Image.new("RGB", (WIDTH, HEIGHT))
    pix = imagen.load()

    for i in range(WIDTH):
        for j in range(HEIGHT):
            re = X_MIN + (i / WIDTH) * (X_MAX - X_MIN)
            im = Y_MAX - (j / HEIGHT) * (Y_MAX - Y_MIN)
            alpha = complex(re, im)

            z0 = critico_secundario(alpha)
            if z0 is None:
                pix[i, j] = (0, 0, 0)
                continue

            n = 0
            while n < ITER_MAX:
                if abs(z0) < EPS or abs(z0) > EPS_INV:
                    break
                z0 = operador(z0, alpha)
                n += 1

            pix[i, j] = (0, 0, 0) if n == ITER_MAX else colores[n % len(colores)]

    return imagen


# =====================================
# PROGRAMA PRINCIPAL
# =====================================

if __name__ == "__main__":
    img = construir_imagen()
    img.show()

    if GUARDAR:
        os.makedirs(os.path.dirname(FILENAME), exist_ok=True)
        img.save(FILENAME)
        print(f"Imagen exportada en: {FILENAME}")
