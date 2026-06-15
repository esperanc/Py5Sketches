"""
Filtragem no dominio da frequencia (Fourier).

Mostra, lado a lado:
  - esquerda : imagem original (intensidade)
  - centro   : magnitude do espectro JA filtrado, log|F . H|  (mostra quais
               frequencias o filtro deixa passar)
  - direita  : imagem reconstruida pela transformada inversa

Filtros (mascara H aplicada ao espectro, com DC no centro):
  - passa-baixa / passa-alta : raio de corte + tipo (ideal, gaussiano, butterworth)
  - borramento gaussiano     : passa-baixa gaussiano (raio)
  - passa-faixa / rejeita-faixa : anel gaussiano (centro, largura)
  - nitidez (high-boost)     : H = 1 + ganho * passa-alta

Interface: GuiBlock MESTRE escolhe imagem e filtro; cada filtro tem o seu
GuiBlock de parametros (visibilidade alternada via display).
"""
import numpy as np
from gui import GuiBlock
from pyodide.ffi import to_js

N = 256
LUMA = np.array([0.2126, 0.7152, 0.0722])

image_files = {
    "cameraman": "cameraman.bmp",
    "lenna": "lenna.bmp",
    "baboon": "baboon.bmp",
}
synthetic = ["sine H", "sine diagonal", "stripes", "checker", "disk",
             "gaussian", "impulse"]

filters = ["passa-baixa", "passa-alta", "borramento gaussiano",
           "passa-faixa", "rejeita-faixa", "nitidez (high-boost)"]

# filtros cuja reconstrucao e ~zero-media -> normalizar min-max para exibir
NORM_FILTERS = {"passa-alta", "passa-faixa"}


# ---------------- colormaps ----------------

def build_inferno():
    pos = np.array([0.0, 0.15, 0.30, 0.50, 0.70, 0.85, 1.0])
    cols = np.array([0, 0, 4, 40, 11, 84, 101, 21, 110, 159, 42, 99,
                     212, 72, 66, 245, 125, 21, 252, 255, 164],
                    dtype=np.float64).reshape(7, 3)
    xs = np.linspace(0.0, 1.0, 256)
    lut = np.zeros((256, 3))
    for ch in range(3):
        lut[:, ch] = np.interp(xs, pos, cols[:, ch])
    return lut.astype(np.uint8)


def build_gray():
    g = np.linspace(0, 255, 256).astype(np.uint8)
    return np.stack([g, g, g], axis=1)


INFERNO = build_inferno()
GRAY = build_gray()


def apply_lut(values01, lut):
    idx = np.clip((values01 * 255.0).round().astype(np.int32), 0, 255)
    return lut[idx]


# ---------------- fontes ----------------

def make_synthetic(name):
    x = np.arange(N)
    X, Y = np.meshgrid(x, x)
    xn, yn = X / N, Y / N
    cx, cy = N / 2.0, N / 2.0
    r2 = (X - cx) ** 2 + (Y - cy) ** 2
    if name == "sine H":
        return 0.5 + 0.5 * np.cos(2 * np.pi * 16 * xn)
    if name == "sine diagonal":
        return 0.5 + 0.5 * np.cos(2 * np.pi * (12 * xn + 12 * yn))
    if name == "stripes":
        return (np.floor(X / (N / 16.0)) % 2).astype(np.float64)
    if name == "checker":
        return ((np.floor(X / (N / 16.0)) + np.floor(Y / (N / 16.0))) % 2).astype(np.float64)
    if name == "disk":
        return (r2 < (N * 0.12) ** 2).astype(np.float64)
    if name == "gaussian":
        return np.exp(-r2 / (2 * (N * 0.07) ** 2))
    f = np.zeros((N, N))
    f[N // 2, N // 2] = 1.0
    return f


# ---------------- p5 ----------------

def preload():
    global images
    images = {name: loadImage(f) for name, f in image_files.items()}


def make_image(rgb):
    img = create_image(N, N)
    img.loadPixels()
    rgba = np.empty((N, N, 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb
    rgba[:, :, 3] = 255
    img.pixels.set(to_js(rgba.tobytes()))
    img.updatePixels()
    return img


def make_bar(lut):
    bar = create_image(1, 256)
    bar.loadPixels()
    rgba = np.empty((256, 1, 4), dtype=np.uint8)
    rgba[:, 0, :3] = lut[::-1]
    rgba[:, :, 3] = 255
    bar.pixels.set(to_js(rgba.tobytes()))
    bar.updatePixels()
    return bar


def setup():
    createCanvas(windowWidth, windowHeight)
    pixelDensity(1)
    noSmooth()

    global INFERNO_BAR, GRAY_BAR
    INFERNO_BAR = make_bar(INFERNO)
    GRAY_BAR = make_bar(GRAY)

    # grade de frequencia radial (com DC no centro), em ciclos/pixel
    global R
    u = np.fft.fftshift(np.fft.fftfreq(N))
    U, V = np.meshgrid(u, u)
    R = np.sqrt(U * U + V * V)

    # fontes (sinteticas + luminancia das fotos)
    global sources
    sources = {name: make_synthetic(name) for name in synthetic}
    for name, img in images.items():
        img.resize(N, N)
        img.loadPixels()
        arr = np.asarray(img.pixels.to_py(), dtype=np.uint8)
        rgb = arr.reshape((N, N, 4))[:, :, :3].astype(np.float64) / 255.0
        sources[name] = rgb @ LUMA

    # GuiBlock mestre
    global master
    master = GuiBlock("Fourier filter")
    master.addSelect("imagem", synthetic + list(image_files.keys()), "cameraman")
    master.addSelect("filtro", filters, "passa-baixa")
    master.change(select_filter)
    master.position(10, 10)

    # blocos de parametros por filtro
    global param_blocks
    param_blocks = {}

    def add_block(name, builder):
        g = GuiBlock(name)
        builder(g)
        g.position(10, 150)
        param_blocks[name] = g

    tipos = ["ideal", "gaussiano", "butterworth"]
    add_block("passa-baixa", lambda g: (
        g.addNumber("corte", 0.02, 0.5, 0.15, 0.01),
        g.addSelect("tipo", tipos, "gaussiano")))
    add_block("passa-alta", lambda g: (
        g.addNumber("corte", 0.02, 0.5, 0.15, 0.01),
        g.addSelect("tipo", tipos, "gaussiano")))
    add_block("borramento gaussiano", lambda g: g.addNumber("raio", 0.02, 0.4, 0.08, 0.01))
    add_block("passa-faixa", lambda g: (
        g.addNumber("centro", 0.02, 0.5, 0.20, 0.01),
        g.addNumber("largura", 0.01, 0.2, 0.05, 0.005)))
    add_block("rejeita-faixa", lambda g: (
        g.addNumber("centro", 0.02, 0.5, 0.20, 0.01),
        g.addNumber("largura", 0.01, 0.2, 0.05, 0.005)))
    add_block("nitidez (high-boost)", lambda g: (
        g.addNumber("corte", 0.02, 0.5, 0.10, 0.01),
        g.addNumber("ganho", 0.0, 3.0, 1.0, 0.1)))
    for blk in param_blocks.values():
        blk.change(compute)

    global input_img, mag_img, recon_img
    input_img = mag_img = recon_img = None
    select_filter()


def select_filter():
    active = master.filtro
    for name, blk in param_blocks.items():
        blk.div.style("display", "block" if name == active else "none")
    compute()


def lowpass(d0, tipo):
    if tipo == "ideal":
        return (R <= d0).astype(np.float64)
    if tipo == "butterworth":
        return 1.0 / (1.0 + (R / d0) ** 4)
    return np.exp(-(R * R) / (2.0 * d0 * d0))  # gaussiano


def build_mask():
    name = master.filtro
    pb = param_blocks[name]
    if name == "passa-baixa":
        return lowpass(pb.corte, pb.tipo)
    if name == "passa-alta":
        return 1.0 - lowpass(pb.corte, pb.tipo)
    if name == "borramento gaussiano":
        return np.exp(-(R * R) / (2.0 * pb.raio * pb.raio))
    if name == "passa-faixa":
        return np.exp(-((R - pb.centro) ** 2) / (2.0 * pb.largura ** 2))
    if name == "rejeita-faixa":
        return 1.0 - np.exp(-((R - pb.centro) ** 2) / (2.0 * pb.largura ** 2))
    if name == "nitidez (high-boost)":
        return 1.0 + pb.ganho * (1.0 - np.exp(-(R * R) / (2.0 * pb.corte * pb.corte)))
    return np.ones_like(R)


def minmax(x):
    lo, hi = x.min(), x.max()
    if hi - lo < 1e-9:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def compute():
    global input_img, mag_img, recon_img
    f = sources[master.imagem]

    fshift = np.fft.fftshift(np.fft.fft2(f))
    H = build_mask()
    g = fshift * H

    mag = np.log1p(np.abs(g))
    mx = mag.max()
    if mx > 0:
        mag = mag / mx

    recon = np.real(np.fft.ifft2(np.fft.ifftshift(g)))
    recon = minmax(recon) if master.filtro in NORM_FILTERS else np.clip(recon, 0, 1)

    input_img = make_image(apply_lut(np.clip(f, 0, 1), GRAY))
    mag_img = make_image(apply_lut(mag, INFERNO))
    recon_img = make_image(apply_lut(recon, GRAY))


# ---------------- desenho ----------------

def colorbar(px, py, w, h, bar, ticks, unit, fz):
    image(bar, px, py, w, h)
    no_fill()
    stroke(120)
    rect(px, py, w, h)
    no_stroke()
    fill(220)
    text_size(fz)
    text_align(LEFT, CENTER)
    for frac, lab in ticks:
        text(lab, px + w + 5, py + (1.0 - frac) * h)
    text_align(LEFT, BOTTOM)
    text(unit, px - 2, py - 5)


def draw_plot(px, py, s, img, title, mode, bar, ticks, unit, fz):
    image(img, px, py, s, s)
    no_fill()
    stroke(110)
    rect(px, py, s, s)

    tick_fz = fz * 0.85

    no_stroke()
    fill(255)
    text_size(fz * 1.3)
    text_align(CENTER, BOTTOM)
    text(title, px + s / 2, py - fz * 0.6)

    text_size(tick_fz)
    stroke(110)
    if mode == "freq":
        xt = [(-0.5, px), (-0.25, px + s * 0.25), (0.0, px + s / 2),
              (0.25, px + s * 0.75), (0.5, px + s)]
        yt = [(-0.5, py), (0.0, py + s / 2), (0.5, py + s)]
        xlabel, ylabel = "fx (ciclos/pixel)", "fy (ciclos/pixel)"
        xfmt = lambda v: f"{v:+.2f}"
    else:
        xt = [(0, px), (N // 2, px + s / 2), (N, px + s)]
        yt = [(0, py), (N // 2, py + s / 2), (N, py + s)]
        xlabel, ylabel = "x (pixels)", "y (pixels)"
        xfmt = lambda v: f"{int(v)}"

    for v, xx in xt:
        line(xx, py + s, xx, py + s + 4)
    for v, yy in yt:
        line(px, yy, px - 4, yy)

    no_stroke()
    fill(200)
    text_align(CENTER, TOP)
    for v, xx in xt:
        text(xfmt(v), xx, py + s + 6)
    text_align(RIGHT, CENTER)
    for v, yy in yt:
        text(xfmt(v), px - 6, yy)

    text_size(fz)
    text_align(CENTER, TOP)
    text(xlabel, px + s / 2, py + s + 8 + tick_fz)
    push()
    translate(px - 8 - tick_fz * 3.4, py + s / 2)
    rotate(-HALF_PI)
    text_align(CENTER, BOTTOM)
    text(ylabel, 0, 0)
    pop()

    if bar is not None:
        colorbar(px + s + 12, py, 14, s, bar, ticks, unit, fz)


def draw():
    background(22)

    plots = [
        (input_img, "original", "spatial", GRAY_BAR,
         [(1.0, "1"), (0.0, "0")], "I"),
        (mag_img, "magnitude filtrada  log|F·H|", "freq", INFERNO_BAR,
         [(1.0, "max"), (0.0, "0")], "log|F|"),
        (recon_img, "reconstruída", "spatial", GRAY_BAR,
         [(1.0, "1"), (0.0, "0")], "I"),
    ]

    fz = width * 0.0095
    if fz < 12:
        fz = 12
    if fz > 20:
        fz = 20

    ML = fz * 4 + 16
    MR = fz * 3 + 40
    GAP = fz * 1.5 + 14
    avail = width * 0.96
    s = (avail - 2 * GAP) / 3 - ML - MR
    hcap = height * 0.62
    if s > hcap:
        s = hcap
    if s < 80:
        s = 80
    cell_w = ML + s + MR
    total = 3 * cell_w + 2 * GAP
    start = (width - total) / 2
    py = (height - s) / 2 + fz

    for i, (img, title, mode, bar, ticks, unit) in enumerate(plots):
        px = start + i * (cell_w + GAP) + ML
        draw_plot(px, py, s, img, title, mode, bar, ticks, unit, fz)

    no_stroke()
    fill(170)
    text_size(fz)
    text_align(CENTER, BOTTOM)
    text(f"filtro: {master.filtro}   —   F·H aplicado ao espectro (DC no "
         f"centro); reconstrucao por transformada inversa.",
         width / 2, height - 10)


def window_resized():
    resizeCanvas(windowWidth, windowHeight)
