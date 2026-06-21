"""
Histogram / processamento de imagem ponto-a-ponto.

Demonstra tres algoritmos classicos:
  - Brilho e Contraste : out = (in - 0.5) * contraste + 0.5 + brilho
  - Equalizacao de Histograma : remapeia os valores pela CDF do histograma
  - Correcao Gama : out = in ** gama

Arquitetura de interface pedida:
  * Um GuiBlock MESTRE escolhe a imagem de teste e o algoritmo.
  * Cada algoritmo tem o SEU proprio GuiBlock com os parametros especificos.
  * Ao trocar de algoritmo, mostramos/escondemos os GuiBlocks alterando a
    propriedade `display` da div que contem cada um (block.div.style("display", ...)).

Mostra, lado a lado, a imagem original e a processada, cada uma com o seu
histograma de luminosidade.
"""
import numpy as np
from gui import GuiBlock
from pyodide.ffi import to_js

SRC = 256  # resolucao de trabalho

image_files = {
    "cameraman": "cameraman.bmp",
    "lenna": "lenna.bmp",
    "baboon": "baboon.bmp",
}

# nomes dos algoritmos (chaves dos GuiBlocks)
BRILHO = "Brilho e Contraste"
EQ = "Equalizacao de Histograma"
GAMA = "Correcao Gama"

LUMA = np.array([0.2126, 0.7152, 0.0722])


def preload():
    global images
    # Imagens carregadas da pasta image_convolution (sem copias locais).
    prefix = "https://esperanc.github.io/Py5Sketches/image_convolution/"
    images = {name: loadImage(prefix + f) for name, f in image_files.items()}


def setup():
    createCanvas(windowWidth, windowHeight, WEBGL)
    pixelDensity(1)

    # Imagens -> resolucao de trabalho + arrays numpy (float, 0..1).
    global arrays
    arrays = {}
    for name, img in images.items():
        img.resize(SRC, SRC)
        img.loadPixels()
        flat = np.asarray(img.pixels.to_py(), dtype=np.uint8)
        arrays[name] = flat.reshape((SRC, SRC, 4))[:, :, :3].astype(np.float64) / 255.0

    # ---- GuiBlock MESTRE ----
    global master
    master = GuiBlock("Mestre")
    master.addSelect("image", image_files.keys(), "cameraman")
    master.addSelect("algorithm", [BRILHO, EQ, GAMA], BRILHO)
    master.change(select_algorithm)
    master.position(10, 10)

    # ---- GuiBlocks de cada algoritmo ----
    global gui_bc, gui_eq, gui_gamma, algo_blocks
    gui_bc = GuiBlock(BRILHO)
    gui_bc.addNumber("brilho", -1.0, 1.0, 0.0, 0.02)
    gui_bc.addNumber("contraste", 0.0, 3.0, 1.0, 0.05)
    gui_bc.change(process)

    gui_eq = GuiBlock(EQ)
    gui_eq.addSelect("modo", ["luminancia", "por canal"], "luminancia")
    gui_eq.addNumber("intensidade", 0.0, 1.0, 1.0, 0.05)
    gui_eq.change(process)

    gui_gamma = GuiBlock(GAMA)
    gui_gamma.addNumber("gama", 0.1, 3.0, 1.0, 0.05)
    gui_gamma.change(process)

    algo_blocks = {BRILHO: gui_bc, EQ: gui_eq, GAMA: gui_gamma}
    for block in algo_blocks.values():
        block.position(10, 170)  # todos no mesmo lugar; so um fica visivel

    # ---- Saidas (imagem processada + histogramas) ----
    global proc_img, hist_orig_g, hist_proc_g
    proc_img = create_image(SRC, SRC)
    hist_orig_g = createGraphics(256, 130)
    hist_proc_g = createGraphics(256, 130)

    # Rotulos das colunas.
    global label_orig, label_proc
    label_orig = _label_div()
    label_proc = _label_div()

    select_algorithm()


def _label_div():
    d = create_div("")
    d.style("position", "absolute")
    d.style("color", "white")
    d.style("font", GuiBlock.font)
    d.style("text-align", "center")
    d.style("transform", "translateX(-50%)")
    d.style("text-shadow", "0 1px 3px black")
    d.style("pointer-events", "none")
    return d


def select_algorithm():
    """Mapeia/desmapeia os GuiBlocks via display, conforme o algoritmo ativo."""
    active = master.algorithm
    for name, block in algo_blocks.items():
        block.div.style("display", "block" if name == active else "none")
    process()


# ----------------------- algoritmos (numpy) -----------------------

def equalize(channel):
    """Equalizacao de histograma de um canal (valores em 0..1)."""
    hist, _ = np.histogram(channel, bins=256, range=(0.0, 1.0))
    cdf = np.cumsum(hist).astype(np.float64)
    cdf /= cdf[-1]  # CDF normalizada -> 0..1
    idx = np.clip((channel * 255.0).astype(np.int32), 0, 255)
    return cdf[idx]


def apply_algorithm(base):
    algo = master.algorithm
    if algo == BRILHO:
        out = (base - 0.5) * gui_bc.contraste + 0.5 + gui_bc.brilho
    elif algo == GAMA:
        out = np.power(np.clip(base, 0.0, 1.0), gui_gamma.gama)
    else:  # equalizacao
        if gui_eq.modo == "por canal":
            out = np.stack([equalize(base[:, :, c]) for c in range(3)], axis=2)
        else:  # luminancia: equaliza Y e preserva a cor pela razao
            y = base @ LUMA
            y_eq = equalize(y)
            ratio = (y_eq / np.maximum(y, 1e-4))[:, :, None]
            out = base * ratio
        amt = gui_eq.intensidade
        out = base * (1.0 - amt) + out * amt
    return np.clip(out, 0.0, 1.0)


def lum_hist(arr):
    y = arr @ LUMA
    hist, _ = np.histogram(y, bins=256, range=(0.0, 1.0))
    return hist


def write_image(img, out):
    h, w = out.shape[:2]
    rgba = np.empty((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = 255
    img.loadPixels()
    img.pixels.set(to_js(rgba.tobytes()))
    img.updatePixels()


def draw_hist(g, counts, col, title):
    g.background(25)
    g.fill(200)
    g.noStroke()
    g.textSize(11)
    g.text(title, 4, 13)
    mx = float(counts.max())
    if mx < 1.0:
        mx = 1.0
    top = 18.0
    usable = g.height - top - 2.0
    g.fill(col[0], col[1], col[2])
    for i in range(256):
        bh = counts[i] / mx * usable
        g.rect(i, g.height - bh, 1.0, bh)


def process():
    name = master.image
    base = arrays[name]
    out = apply_algorithm(base)
    write_image(proc_img, out)
    draw_hist(hist_orig_g, lum_hist(base), (120, 170, 255), "histograma original")
    draw_hist(hist_proc_g, lum_hist(out), (255, 170, 120), "histograma resultado")


# ----------------------- desenho -----------------------

def draw():
    background(30)

    a = width * 0.40
    b = height * 0.55
    img_size = a if a < b else b
    hist_h = img_size * 0.42
    gap = 22
    col_dx = img_size / 2 + gap / 2
    col_h = img_size + gap + hist_h
    top_y = -col_h / 2

    img_cy = top_y + img_size / 2
    hist_cy = top_y + img_size + gap + hist_h / 2

    # coluna esquerda (original) e direita (resultado)
    _panel(-col_dx, img_cy, hist_cy, img_size, hist_h, images[master.image], hist_orig_g)
    _panel(col_dx, img_cy, hist_cy, img_size, hist_h, proc_img, hist_proc_g)

    # rotulos
    label_orig.html("original")
    label_proc.html(f"resultado — {master.algorithm}")
    ly = int(height / 2 + img_cy + img_size / 2 + 6)
    label_orig.position(int(width / 2 - col_dx), ly)
    label_proc.position(int(width / 2 + col_dx), ly)
    for lab in (label_orig, label_proc):
        lab.style("width", f"{int(img_size)}px")


def _panel(cx, img_cy, hist_cy, img_size, hist_h, img, hist_g):
    image(img, cx - img_size / 2, img_cy - img_size / 2, img_size, img_size)
    image(hist_g, cx - img_size / 2, hist_cy - hist_h / 2, img_size, hist_h)


def window_resized():
    resizeCanvas(windowWidth, windowHeight)
