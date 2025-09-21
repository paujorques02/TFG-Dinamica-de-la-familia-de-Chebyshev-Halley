import argparse
import colorsys
import cmath
import os
import sys
import time
from dataclasses import dataclass
from typing import Tuple
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import ttk

# ==========================
# Modelo de parámetros
# ==========================
@dataclass
class Params:
    alpha_re: float = 0.0
    alpha_im: float = 0.0
    x_min: float = -2.5
    x_max: float = 1.5
    y_min: float = -2.5
    y_max: float = 1.5
    width: int = 1400
    height: int = 800
    iter_max: int = 300
    eps: float = 1e-3
    escape: float = None  # si None, se usa 1/eps
    color_basin0: Tuple[int,int,int] = (250,208,36)   # oro
    color_basin1: Tuple[int,int,int] = (34,209,185)   # turquesa
    color_unknown: Tuple[int,int,int] = (40,40,40)    # gris
    color_escape_mode: str = "hsv"                   # "hsv" o un color fijo hexadecimal
    basin2_mode: str = "s12"                         # "s12" o "one" (1 como segundo atractor)
    draw_s12: bool = True                            # dibujar s1/s2 como cuadrados
    draw_marks: bool = True                          # dibujar marcas de 0 y 1
    outdir: str = "imagenes"
    filename_prefix: str = "dinamico"

    def finalize(self):
        if self.escape is None:
            self.escape = 1.0 / self.eps

# ==========================
# Utilidades de color
# ==========================
def hex_to_rgb255(s: str) -> Tuple[int,int,int]:
    s = s.strip()
    if s.startswith('#'):
        s = s[1:]
    if len(s) == 3:
        s = ''.join(ch*2 for ch in s)
    if len(s) != 6:
        raise ValueError("Hex color inválido")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (r,g,b)

def hsv_to_rgb255(h: float, s: float, v: float) -> Tuple[int,int,int]:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(255*r), int(255*g), int(255*b))

# ==========================
# Dinámica compleja
# ==========================
def O_alpha(z: complex, a: complex) -> complex:
    num = z**3 * (z - 2*(a - 1))
    den = 1 - 2*(a - 1)*z
    if abs(den) < 1e-10:
        return complex(float("inf"), 0.0)
    return num/den

def extra_fixed_points(a: complex) -> Tuple[complex, complex]:
    disc = cmath.sqrt(4*a*a - 12*a + 5)
    return (2*a - 3 - disc)/2, (2*a - 3 + disc)/2

# ==========================
# Render
# ==========================
def classify_color(z0: complex, a: complex, P: Params):
    z = z0
    s1, s2 = extra_fixed_points(a)
    for k in range(1, P.iter_max + 1):
        if abs(z) < P.eps:
            return P.color_basin0
        if P.basin2_mode == "one":
            if abs(z - 1) < P.eps:
                return P.color_basin1
        else:  # s1/s2
            if abs(z - s1) < P.eps or abs(z - s2) < P.eps:
                return P.color_basin1
        if abs(z) > P.escape:
            if P.color_escape_mode.lower() == "hsv":
                h = (k % 90) / 90.0
                return hsv_to_rgb255(h, 0.85, 1.0)
            else:
                # color fijo vía hex
                try:
                    return hex_to_rgb255(P.color_escape_mode)
                except Exception:
                    return (0,0,0)
        z = O_alpha(z, a)
    return P.color_unknown


def px_to_complex(i: int, j: int, P: Params) -> complex:
    re = P.x_min + (i / (P.width - 1))  * (P.x_max - P.x_min)
    im = P.y_min + (j / (P.height - 1)) * (P.y_max - P.y_min)
    return complex(re, im)


def complex_to_px(z: complex, P: Params):
    x = int((z.real - P.x_min) / (P.x_max - P.x_min) * (P.width - 1))
    y = int((z.imag - P.y_min) / (P.y_max - P.y_min) * (P.height - 1))
    return x, y


def render_plane(P: Params) -> Image.Image:
    P.finalize()
    a = complex(P.alpha_re, P.alpha_im)

    img = Image.new("RGB", (P.width, P.height), color=(0, 0, 0))
    put = img.putpixel

    for i in range(P.width):
        for j in range(P.height):
            z0 = px_to_complex(i, j, P)
            put((i, j), classify_color(z0, a, P))

    draw = ImageDraw.Draw(img)

    # Marcas
    if P.draw_marks:
        # 0 y 1 como círculos
        for pf, r in [(0+0j, 6), (1+0j, 6)]:
            cx, cy = complex_to_px(pf, P)
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(255,255,255), width=2)
    if P.draw_s12:
        s1, s2 = extra_fixed_points(a)
        for pf, r in [(s1, 5), (s2, 5)]:
            cx, cy = complex_to_px(pf, P)
            draw.rectangle((cx-r, cy-r, cx+r, cy+r), outline=(255,255,255), width=2)

    return img


# ==========================
# CLI y GUI
# ==========================
def build_parser():
    p = argparse.ArgumentParser(description="Plano dinámico parametrizable de O_alpha")
    p.add_argument('--alpha-re', type=float)
    p.add_argument('--alpha-im', type=float)
    p.add_argument('--x-min', type=float)
    p.add_argument('--x-max', type=float)
    p.add_argument('--y-min', type=float)
    p.add_argument('--y-max', type=float)
    p.add_argument('--width', type=int)
    p.add_argument('--height', type=int)
    p.add_argument('--iter-max', type=int)
    p.add_argument('--eps', type=float)
    p.add_argument('--escape', type=float, help='Por defecto 1/eps')
    p.add_argument('--color-basin0', type=str, help='Hex (#RRGGBB) o por defecto oro')
    p.add_argument('--color-basin1', type=str, help='Hex (#RRGGBB) o por defecto teal')
    p.add_argument('--color-unknown', type=str, help='Hex, por defecto gris #282828')
    p.add_argument('--color-escape', type=str, default='hsv', help='"hsv" o hex fijo')
    p.add_argument('--basin2-mode', choices=['s12','one'], default='s12')
    p.add_argument('--draw-s12', action='store_true')
    p.add_argument('--no-draw-s12', action='store_true')
    p.add_argument('--no-draw-marks', action='store_true')
    p.add_argument('--outdir', type=str)
    p.add_argument('--filename-prefix', type=str)
    return p


def args_to_params(ns: argparse.Namespace) -> Params:
    P = Params()
    for f in ['alpha_re','alpha_im','x_min','x_max','y_min','y_max','width','height',
              'iter_max','eps','escape','color_escape_mode','basin2_mode','outdir','filename_prefix']:
        v = getattr(ns, f.replace('-', '_'), None)
        if v is not None:
            setattr(P, f if hasattr(P,f) else f.replace('-', '_'), v)

    # colores
    if ns.color_basin0:
        P.color_basin0 = hex_to_rgb255(ns.color_basin0)
    if ns.color_basin1:
        P.color_basin1 = hex_to_rgb255(ns.color_basin1)
    if ns.color_unknown:
        P.color_unknown = hex_to_rgb255(ns.color_unknown)

    # flags
    if ns.no_draw_marks:
        P.draw_marks = False
    if ns.draw_s12:
        P.draw_s12 = True
    if ns.no_draw_s12:
        P.draw_s12 = False

    return P


def ensure_outdir(path: str):
    os.makedirs(path, exist_ok=True)


def save_image(img: Image.Image, P: Params) -> str:
    ts = time.strftime('%Y%m%d_%H%M%S')
    fname = f"{P.filename_prefix}_{P.alpha_re:+.1f}_{P.alpha_im:+.1f}.png"
    ensure_outdir(P.outdir)
    full = os.path.join(P.outdir, fname)
    img.save(full)
    return full


# --------- GUI (Tkinter) ---------
def launch_gui_and_get_params() -> Params:

    P = Params()

    root = tk.Tk()
    root.title("Plano dinámico – Parámetros")

    frm = ttk.Frame(root, padding=10)
    frm.grid()

    entries = {}
    specs = [
        ("alpha_re", P.alpha_re), ("alpha_im", P.alpha_im),
        ("x_min", P.x_min), ("x_max", P.x_max), ("y_min", P.y_min), ("y_max", P.y_max),
        ("width", P.width), ("height", P.height),
        ("iter_max", P.iter_max), ("eps", P.eps), ("escape", ""),
        ("color_basin0", "#FAD024"), ("color_basin1", "#22D1B9"), ("color_unknown", "#282828"),
        ("color_escape_mode", "hsv"),
        ("basin2_mode", P.basin2_mode),
        ("outdir", P.outdir), ("filename_prefix", P.filename_prefix),
    ]

    row = 0
    for key, default in specs:
        ttk.Label(frm, text=key).grid(column=0, row=row, sticky='w')
        var = tk.StringVar(value=str(default))
        ent = ttk.Entry(frm, textvariable=var, width=24)
        ent.grid(column=1, row=row, sticky='ew', pady=2)
        entries[key] = var
        row += 1

    draw_marks_var = tk.BooleanVar(value=P.draw_marks)
    ttk.Checkbutton(frm, text="Dibujar marcas 0 y 1", variable=draw_marks_var).grid(column=0, row=row, columnspan=2, sticky='w'); row+=1

    draw_s12_var = tk.BooleanVar(value=P.draw_s12)
    ttk.Checkbutton(frm, text="Dibujar s1/s2", variable=draw_s12_var).grid(column=0, row=row, columnspan=2, sticky='w'); row+=1

    def on_ok():
        try:
            P.alpha_re = float(entries['alpha_re'].get())
            P.alpha_im = float(entries['alpha_im'].get())
            P.x_min = float(entries['x_min'].get())
            P.x_max = float(entries['x_max'].get())
            P.y_min = float(entries['y_min'].get())
            P.y_max = float(entries['y_max'].get())
            P.width = int(entries['width'].get())
            P.height = int(entries['height'].get())
            P.iter_max = int(entries['iter_max'].get())
            P.eps = float(entries['eps'].get())
            esc = entries['escape'].get().strip()
            P.escape = float(esc) if esc else None

            P.color_basin0 = hex_to_rgb255(entries['color_basin0'].get())
            P.color_basin1 = hex_to_rgb255(entries['color_basin1'].get())
            P.color_unknown = hex_to_rgb255(entries['color_unknown'].get())
            P.color_escape_mode = entries['color_escape_mode'].get().strip()

            mode = entries['basin2_mode'].get().strip().lower()
            P.basin2_mode = 'one' if mode.startswith('o') else 's12'

            P.outdir = entries['outdir'].get().strip() or P.outdir
            P.filename_prefix = entries['filename_prefix'].get().strip() or P.filename_prefix

            P.draw_marks = bool(draw_marks_var.get())
            P.draw_s12 = bool(draw_s12_var.get())
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Error en parámetros", str(e))
            return
        root.destroy()

    btn = ttk.Button(frm, text="Generar", command=on_ok)
    btn.grid(column=0, row=row, columnspan=2, pady=8)

    root.mainloop()
    return P


# ==========================
# Main
# ==========================
def main(argv=None):
    parser = build_parser()
    ns = parser.parse_args(argv)

    # Si no hay argumentos, lanzar GUI
    use_gui = (len(sys.argv) == 1)

    if use_gui:
        P = launch_gui_and_get_params()
    else:
        P = args_to_params(ns)

    img = render_plane(P)
    path = save_image(img, P)
    print(f"Imagen guardada en: {path}")


if __name__ == '__main__':
    main()
