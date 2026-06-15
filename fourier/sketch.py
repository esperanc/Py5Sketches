"""
Transformada de Fourier 2D — visualizacao didatica.

Um painel escolhe a imagem de teste (padroes sinteticos ou fotos reais). A FFT
2D e mostrada em dois graficos: MAGNITUDE (escala log) e FASE. Ao lado, a
imagem de entrada (intensidade). Cada grafico traz:
  - eixos de frequencia normalizada fx, fy (ciclos/pixel), com 0 (DC) no centro
    apos fftshift;
  - uma barra de cores legendada com a escala usada.

Padroes sinteticos ajudam a ler o espectro:
  - sine H/V/diagonal : dois impulsos simetricos na direcao da frequencia
  - stripes / checker : onda quadrada -> harmonicos
  - disk              : aneis (padrao jinc)
  - gaussian          : gaussiana (transformada de gaussiana)
  - impulse           : delta -> espectro plano
"""
import numpy as np
from gui import GuiBlock
from pyodide.ffi import to_js

N = 256  # tamanho da imagem / FFT
LUMA = np.array([0.2126, 0.7152, 0.0722])

image_files = {
    "cameraman": "cameraman.bmp",
    "lenna": "lenna.bmp",
    "baboon": "baboon.bmp",
}

synthetic = ["sine H", "sine V", "sine diagonal", "stripes", "checker",
             "disk", "gaussian", "impulse"]


# ---------------- colormaps ----------------

def _hsv_channel(h6, s, v, n):
    k = (n + h6) % 6.0
    m = np.clip(2.0 - np.abs(k - 2.0), 0.0, 1.0)  # = clip(min(k, 4-k), 0, 1)
    return v - v * s * m


def hsv_to_rgb(h, s, v):
    # Formula vetorizada (Wikipedia), sem funcoes aninhadas.
    h6 = np.asarray(h, dtype=np.float64) * 6.0
    s = np.asarray(s, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    return (_hsv_channel(h6, s, v, 5.0),
            _hsv_channel(h6, s, v, 3.0),
            _hsv_channel(h6, s, v, 1.0))


def build_inferno():
    pos = np.array([0.0, 0.15, 0.30, 0.50, 0.70, 0.85, 1.0])
    # lista plana + reshape (np.array de lista de tuplas quebra no numpy do Pyodide)
    cols = np.array([0, 0, 4, 40, 11, 84, 101, 21, 110, 159, 42, 99,
                     212, 72, 66, 245, 125, 21, 252, 255, 164],
                    dtype=np.float64).reshape(7, 3)
    xs = np.linspace(0.0, 1.0, 256)
    lut = np.zeros((256, 3))
    for ch in range(3):
        lut[:, ch] = np.interp(xs, pos, cols[:, ch])
    return lut.astype(np.uint8)


def build_phase_lut():
    hue = np.linspace(0.0, 1.0, 256)
    one = np.ones(256)
    r, g, b = hsv_to_rgb(hue, one, one)
    return (np.stack([r, g, b], axis=1) * 255).astype(np.uint8)


def build_gray():
    g = np.linspace(0, 255, 256).astype(np.uint8)
    return np.stack([g, g, g], axis=1)


INFERNO = build_inferno()
PHASE_LUT = build_phase_lut()
GRAY = build_gray()


def apply_lut(values01, lut):
    idx = np.clip((values01 * 255.0).round().astype(np.int32), 0, 255)
    return lut[idx]


# ---------------- fontes sinteticas ----------------

def make_synthetic(name):
    x = np.arange(N)
    X, Y = np.meshgrid(x, x)
    xn, yn = X / N, Y / N
    cx, cy = N / 2.0, N / 2.0
    r2 = (X - cx) ** 2 + (Y - cy) ** 2
    if name == "sine H":
        return 0.5 + 0.5 * np.cos(2 * np.pi * 16 * xn)
    if name == "sine V":
        return 0.5 + 0.5 * np.cos(2 * np.pi * 16 * yn)
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
    # impulse
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
    """Imagem 1x256 com o colormap (topo = valor alto) para usar como legenda."""
    bar = create_image(1, 256)
    bar.loadPixels()
    rgba = np.empty((256, 1, 4), dtype=np.uint8)
    rgba[:, 0, :3] = lut[::-1]   # linha 0 (topo) = lut[255]
    rgba[:, :, 3] = 255
    bar.pixels.set(to_js(rgba.tobytes()))
    bar.updatePixels()
    return bar


def setup():
    createCanvas(windowWidth, windowHeight)
    pixelDensity(1)
    noSmooth()

    # Barras de cores (legendas) como imagens.
    global INFERNO_BAR, PHASE_BAR, GRAY_BAR
    INFERNO_BAR = make_bar(INFERNO)
    PHASE_BAR = make_bar(PHASE_LUT)
    GRAY_BAR = make_bar(GRAY)

    # Fontes: sinteticas + luminancia das fotos.
    global sources
    sources = {name: make_synthetic(name) for name in synthetic}
    for name, img in images.items():
        img.resize(N, N)
        img.loadPixels()
        arr = np.asarray(img.pixels.to_py(), dtype=np.uint8)
        rgb = arr.reshape((N, N, 4))[:, :, :3].astype(np.float64) / 255.0
        sources[name] = rgb @ LUMA

    global gui
    gui = GuiBlock("Fourier 2D")
    gui.addSelect("imagem", synthetic + list(image_files.keys()), "sine diagonal")
    gui.change(compute)
    gui.position(10, 10)

    global input_img, mag_img, phase_img
    input_img = mag_img = phase_img = None
    compute()


def compute():
    """Recalcula a FFT e os tres mapas de calor (so quando a imagem muda)."""
    global input_img, mag_img, phase_img
    f = sources[gui.imagem]

    input_img = make_image(apply_lut(np.clip(f, 0, 1), GRAY))

    fshift = np.fft.fftshift(np.fft.fft2(f))
    mag = np.log1p(np.abs(fshift))
    mx = mag.max()
    if mx > 0:
        mag = mag / mx
    mag_img = make_image(apply_lut(mag, INFERNO))

    phase = np.angle(fshift)            # -pi..pi
    hue = (phase + np.pi) / (2 * np.pi)
    one = np.ones((N, N))
    r, g, b = hsv_to_rgb(hue, one, one)
    phase_img = make_image((np.stack([r, g, b], axis=2) * 255).astype(np.uint8))


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

    tick_fz = fz * 0.85  # numeros dos ticks um pouco menores que os titulos

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
        (input_img, "imagem  (intensidade)", "spatial", GRAY_BAR,
         [(1.0, "1"), (0.0, "0")], "I"),
        (mag_img, "magnitude  log|F|", "freq", INFERNO_BAR,
         [(1.0, "max"), (0.0, "0")], "log|F|"),
        (phase_img, "fase  ∠F", "freq", PHASE_BAR,
         [(1.0, "+π"), (0.5, "0"), (0.0, "-π")], "rad"),
    ]

    # Fonte das legendas proporcional a largura (com limites).
    fz = width * 0.0095
    if fz < 12:
        fz = 12
    if fz > 20:
        fz = 20

    # 3 celulas (margem-eixo + grafico + barra/rotulos) agrupadas e
    # centralizadas; o grafico cresce com a largura, limitado pela altura.
    # As margens acompanham a fonte para caber rotulos maiores.
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

    for i, (img, title, mode, lut, ticks, unit) in enumerate(plots):
        px = start + i * (cell_w + GAP) + ML
        draw_plot(px, py, s, img, title, mode, lut, ticks, unit, fz)

    no_stroke()
    fill(170)
    text_size(fz)
    text_align(CENTER, BOTTOM)
    text("FFT 2D com fftshift (DC no centro). Magnitude em escala log; "
         "fase via matiz ciclica.", width / 2, height - 10)


def window_resized():
    resizeCanvas(windowWidth, windowHeight)
