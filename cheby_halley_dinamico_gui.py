import threading
import time
import os
import colorsys
import cmath
from dataclasses import dataclass
from typing import Tuple, Optional
from PIL import Image, ImageTk, ImageDraw

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox

# ==========================
# Modelo de parámetros
# ==========================
@dataclass
class Params:
    alpha_re: float = -0.3
    alpha_im: float = 0.0
    x_min: float = -2.0
    x_max: float = 3.0
    y_min: float = -2.0
    y_max: float = 2.0
    width: int = 900
    height: int = 600
    iter_max: int = 300
    eps: float = 1e-3
    escape: Optional[float] = None  # None => 1/eps

    color_basin0: Tuple[int,int,int] = (250,208,36)   # oro
    color_basin1: Tuple[int,int,int] = (34,209,185)   # teal
    color_unknown: Tuple[int,int,int] = (40,40,40)    # gris oscuro
    color_escape_mode: str = "hsv"                   # "hsv" o un hex "#RRGGBB"

    basin2_mode: str = "s12"                         # "s12" o "one"
    draw_marks: bool = True                          # dibujar 0 y 1
    draw_s12: bool = True                            # dibujar s1/s2

    outdir: str = "imagenes"
    filename_prefix: str = "dinamico"

    def finalize(self):
        if self.escape is None or self.escape == 0:
            self.escape = 1.0 / float(self.eps)

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
        raise ValueError("Color hex inválido")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (r,g,b)

def rgb255_to_hex(rgb: Tuple[int,int,int]) -> str:
    r,g,b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"

# ==========================
# Dinámica compleja
# ==========================

def O_alpha(z: complex, a: complex) -> complex:
    num = z**3 * (z - 2*(a - 1))
    den = 1 - 2*(a - 1)*z
    if abs(den) < 1e-10:
        return complex(float("inf"), 0.0)
    return num/den

def extra_fixed_points(a: complex):
    disc = cmath.sqrt(4*a*a - 12*a + 5)
    return (2*a - 3 - disc)/2, (2*a - 3 + disc)/2

# ==========================
# Render (píxel a píxel)
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
        else:
            if abs(z - s1) < P.eps or abs(z - s2) < P.eps:
                return P.color_basin1
        if abs(z) > P.escape:
            if P.color_escape_mode.lower() == "hsv":
                h = (k % 90) / 90.0
                r,g,b = colorsys.hsv_to_rgb(h, 0.85, 1.0)
                return (int(255*r), int(255*g), int(255*b))
            else:
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


def render_plane(P: Params, progress_cb=None, stop_flag=None) -> Image.Image:
    P.finalize()
    a = complex(P.alpha_re, P.alpha_im)
    img = Image.new("RGB", (P.width, P.height), color=(0, 0, 0))
    put = img.putpixel

    for i in range(P.width):
        if stop_flag and stop_flag():
            return None
        for j in range(P.height):
            z0 = px_to_complex(i, j, P)
            put((i, j), classify_color(z0, a, P))
        if progress_cb:
            progress_cb(i+1, P.width)

    draw = ImageDraw.Draw(img)

    # Marcas
    if P.draw_marks:
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
# GUI
# ==========================

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Plano dinámico – Interfaz")
        self.P = Params()
        self.worker = None
        self.stop_req = False
        self.current_image: Optional[Image.Image] = None
        self.tk_img = None

        self._build_ui()
        self._update_preview_placeholder()

    # ---------- UI layout ----------
    def _build_ui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        ctrl = ttk.Frame(self.root, padding=8)
        ctrl.grid(row=0, column=0, sticky='nsw')

        preview = ttk.Frame(self.root, padding=8)
        preview.grid(row=0, column=1, sticky='nsew')
        preview.rowconfigure(0, weight=1)
        preview.columnconfigure(0, weight=1)

        # --- Controls ---
        self.vars = {}
        def add_entry(lbl, key, val):
            frame = ttk.Frame(ctrl)
            frame.pack(fill='x', pady=2)
            ttk.Label(frame, text=lbl, width=16).pack(side='left')
            var = tk.StringVar(value=str(val))
            ent = ttk.Entry(frame, textvariable=var, width=14)
            ent.pack(side='left')
            self.vars[key] = var
            return ent

        ttk.Label(ctrl, text="Parámetros de α", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(0,2))
        add_entry("alpha_re", 'alpha_re', self.P.alpha_re)
        add_entry("alpha_im", 'alpha_im', self.P.alpha_im)

        ttk.Separator(ctrl).pack(fill='x', pady=4)
        ttk.Label(ctrl, text="Rangos", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        add_entry("x_min", 'x_min', self.P.x_min)
        add_entry("x_max", 'x_max', self.P.x_max)
        add_entry("y_min", 'y_min', self.P.y_min)
        add_entry("y_max", 'y_max', self.P.y_max)

        ttk.Separator(ctrl).pack(fill='x', pady=4)
        ttk.Label(ctrl, text="Resolución", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        add_entry("width", 'width', self.P.width)
        add_entry("height", 'height', self.P.height)

        ttk.Separator(ctrl).pack(fill='x', pady=4)
        ttk.Label(ctrl, text="Condiciones de parada", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        add_entry("iter_max", 'iter_max', self.P.iter_max)
        add_entry("eps", 'eps', self.P.eps)
        add_entry("escape (vacío=1/eps)", 'escape', "")

        ttk.Separator(ctrl).pack(fill='x', pady=4)
        ttk.Label(ctrl, text="Colores", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        self.color_vars = {
            'basin0': tk.StringVar(value=rgb255_to_hex(self.P.color_basin0)),
            'basin1': tk.StringVar(value=rgb255_to_hex(self.P.color_basin1)),
            'unknown': tk.StringVar(value=rgb255_to_hex(self.P.color_unknown)),
            'escape': tk.StringVar(value=self.P.color_escape_mode)
        }
        for label,key in [("basin0","basin0"),("basin1","basin1"),("unknown","unknown")]:
            row = ttk.Frame(ctrl)
            row.pack(fill='x', pady=2)
            ttk.Label(row, text=label, width=16).pack(side='left')
            ent = ttk.Entry(row, textvariable=self.color_vars[key], width=14)
            ent.pack(side='left')
            btn = ttk.Button(row, text="…", width=3, command=lambda k=key: self.pick_color(k))
            btn.pack(side='left', padx=2)
        row = ttk.Frame(ctrl)
        row.pack(fill='x', pady=2)
        ttk.Label(row, text="escape", width=16).pack(side='left')
        ttk.Entry(row, textvariable=self.color_vars['escape'], width=14).pack(side='left')
        ttk.Label(row, text='(hsv o #RRGGBB)').pack(side='left')

        ttk.Separator(ctrl).pack(fill='x', pady=4)
        ttk.Label(ctrl, text="Modo cuenca 2", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        self.basin2 = tk.StringVar(value=self.P.basin2_mode)
        ttk.Radiobutton(ctrl, text='s1/s2', variable=self.basin2, value='s12').pack(anchor='w')
        ttk.Radiobutton(ctrl, text='1', variable=self.basin2, value='one').pack(anchor='w')

        self.draw_marks = tk.BooleanVar(value=self.P.draw_marks)
        ttk.Checkbutton(ctrl, text="Dibujar 0 y 1", variable=self.draw_marks).pack(anchor='w')
        self.draw_s12 = tk.BooleanVar(value=self.P.draw_s12)
        ttk.Checkbutton(ctrl, text="Dibujar s1/s2", variable=self.draw_s12).pack(anchor='w')

        ttk.Separator(ctrl).pack(fill='x', pady=4)
        ttk.Label(ctrl, text="Guardado", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        add_entry("outdir", 'outdir', self.P.outdir)
        add_entry("filename_prefix", 'filename_prefix', self.P.filename_prefix)

        # Buttons
        btns = ttk.Frame(ctrl)
        btns.pack(fill='x', pady=6)
        self.btn_render = ttk.Button(btns, text="Generar", command=self.on_render)
        self.btn_render.pack(side='left', padx=2)
        self.btn_cancel = ttk.Button(btns, text="Cancelar", command=self.on_cancel, state='disabled')
        self.btn_cancel.pack(side='left', padx=2)
        self.btn_save = ttk.Button(btns, text="Guardar…", command=self.on_save, state='disabled')
        self.btn_save.pack(side='left', padx=2)

        self.status = ttk.Label(ctrl, text="Listo", foreground='#555')
        self.status.pack(anchor='w', pady=(4,0))

        # --- Preview ---
        self.canvas = tk.Canvas(preview, bg='#1e1e1e')
        self.canvas.grid(row=0, column=0, sticky='nsew')

    def pick_color(self, key):
        initial = self.color_vars[key].get()
        try:
            rgb = hex_to_rgb255(initial)
            initial = rgb255_to_hex(rgb)
        except Exception:
            initial = '#FFFFFF'
        rgb, _ = colorchooser.askcolor(color=initial, parent=self.root, title=f"Color {key}")
        if rgb:
            r,g,b = map(int, rgb)
            self.color_vars[key].set(rgb255_to_hex((r,g,b)))

    def _update_preview_placeholder(self):
        self.canvas.delete('all')
        self.canvas.create_text(10, 10, anchor='nw', fill='#ccc', text='Vista previa: genera una imagen', font=('TkDefaultFont', 11))

    # ---------- Actions ----------
    def on_render(self):
        try:
            P = self._read_params_from_ui()
        except Exception as e:
            messagebox.showerror("Parámetros inválidos", str(e))
            return
        self._start_render(P)

    def on_cancel(self):
        self.stop_req = True

    def on_save(self):
        if not self.current_image:
            messagebox.showinfo("Nada para guardar", "Primero genera una imagen.")
            return
        P = self.P
        default_name = f"{P.filename_prefix}_{P.alpha_re:+.1f}_{P.alpha_im:+.1f}.png"
        initialdir = self.vars['outdir'].get().strip() or P.outdir
        os.makedirs(initialdir, exist_ok=True)
        path = filedialog.asksaveasfilename(defaultextension='.png', initialdir=initialdir, initialfile=default_name,
                                            filetypes=[('PNG','*.png')])
        if not path:
            return
        try:
            self.current_image.save(path)
            messagebox.showinfo("Guardado", f"Imagen guardada en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

    def _read_params_from_ui(self) -> Params:
        P = Params()
        P.alpha_re = float(self.vars['alpha_re'].get())
        P.alpha_im = float(self.vars['alpha_im'].get())
        P.x_min = float(self.vars['x_min'].get())
        P.x_max = float(self.vars['x_max'].get())
        P.y_min = float(self.vars['y_min'].get())
        P.y_max = float(self.vars['y_max'].get())
        P.width = int(self.vars['width'].get())
        P.height = int(self.vars['height'].get())
        P.iter_max = int(self.vars['iter_max'].get())
        P.eps = float(self.vars['eps'].get())
        esc = self.vars['escape'].get().strip()
        P.escape = float(esc) if esc else None

        # colores
        P.color_basin0 = hex_to_rgb255(self.color_vars['basin0'].get())
        P.color_basin1 = hex_to_rgb255(self.color_vars['basin1'].get())
        P.color_unknown = hex_to_rgb255(self.color_vars['unknown'].get())
        P.color_escape_mode = self.color_vars['escape'].get().strip()

        P.basin2_mode = self.basin2.get()
        P.draw_marks = bool(self.draw_marks.get())
        P.draw_s12 = bool(self.draw_s12.get())

        P.outdir = self.vars['outdir'].get().strip() or P.outdir
        P.filename_prefix = self.vars['filename_prefix'].get().strip() or P.filename_prefix
        return P

    def _start_render(self, P: Params):
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("En curso", "Ya hay un render en progreso. Cancélalo o espera a que termine.")
            return
        self.P = P
        self.stop_req = False
        self._set_rendering_state(True)
        self.status.configure(text="Generando… 0%")
        self.worker = threading.Thread(target=self._render_worker, daemon=True)
        self.worker.start()
        self._poll_worker()

    def _set_rendering_state(self, busy: bool):
        self.btn_render['state'] = 'disabled' if busy else 'normal'
        self.btn_cancel['state'] = 'normal' if busy else 'disabled'
        self.btn_save['state'] = 'disabled' if busy else ('normal' if self.current_image else 'disabled')

    def _render_worker(self):
        def progress(done, total):
            pct = int(100*done/total)
            self._progress_pct = pct
        def stop_flag():
            return self.stop_req
        self._progress_pct = 0
        try:
            img = render_plane(self.P, progress_cb=progress, stop_flag=stop_flag)
            self._render_result = img
            self._render_error = None
        except Exception as e:
            self._render_result = None
            self._render_error = e

    def _poll_worker(self):
        if self.worker and self.worker.is_alive():
            self.status.configure(text=f"Generando… {getattr(self, '_progress_pct', 0)}%")
            self.root.after(100, self._poll_worker)
            return
        # finished
        self._set_rendering_state(False)
        err = getattr(self, '_render_error', None)
        img = getattr(self, '_render_result', None)
        if err:
            self.status.configure(text="Error")
            messagebox.showerror("Error durante el render", str(err))
            return
        if img is None:
            self.status.configure(text="Cancelado")
            return
        self.current_image = img
        self.status.configure(text="Listo – render completado")
        self._show_image_on_canvas(img)
        self.btn_save['state'] = 'normal'

    def _show_image_on_canvas(self, img: Image.Image):
        # Ajustar al tamaño del canvas manteniendo aspect ratio
        cw = self.canvas.winfo_width() or 1
        ch = self.canvas.winfo_height() or 1
        iw, ih = img.size
        scale = min(cw/iw, ch/ih)
        if scale <= 0:
            scale = 1
        nw, nh = max(1, int(iw*scale)), max(1, int(ih*scale))
        disp = img.resize((nw, nh), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(disp)
        self.canvas.delete('all')
        self.canvas.create_image(cw//2, ch//2, image=self.tk_img, anchor='center')

# ==========================
# Main
# ==========================

def main():
    root = tk.Tk()
    # Mejor redimensionamiento
    root.geometry('1200x720')
    app = App(root)
    root.mainloop()

if __name__ == '__main__':
    main()
