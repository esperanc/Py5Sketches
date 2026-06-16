"""
Filtros nao-lineares (e ruido).

Mostra a imagem de ENTRADA (opcionalmente com ruido) a esquerda e o RESULTADO
do filtro a direita. Todo o processamento e em CPU (numpy), pois filtros como
mediana e bilateral nao se expressam como uma convolucao linear.

Ruido (adicionado a imagem original):
  - sal e pimenta : fracao 'intensidade' dos pixels vira 0 ou 1
  - gaussiano     : ruido normal de desvio 'intensidade'

Filtros:
  - mediana            : mediana da vizinhanca (otimo p/ sal e pimenta)
  - bilateral          : media ponderada por proximidade espacial E de cor
                         (suaviza preservando bordas)
  - gaussiano (linear) : para comparar (borra ruido E bordas)
  - media (box)        : media simples da vizinhanca
  - minimo / maximo    : erosao / dilatacao (morfologia em tons de cinza)
  - Kuwahara           : media da sub-regiao de menor variancia (preserva bordas)

Interface: GuiBlock MESTRE (imagem, ruido, intensidade, algoritmo) e um
GuiBlock de parametros por filtro (visibilidade alternada via display).
"""
import numpy as np
from gui import GuiBlock
from pyodide.ffi import to_js

SRC = 256
LUMA = np.array([0.2126, 0.7152, 0.0722])

image_files = {
    "lenna": "lenna.bmp",
    "baboon": "baboon.bmp",
    "cameraman": "cameraman.bmp",
}

filters = ["mediana", "bilateral", "gaussiano (linear)", "media (box)",
           "minimo", "maximo", "Kuwahara"]


def preload():
    global images
    # Imagens carregadas da pasta image_convolution (sem copias locais).
    images = {name: loadImage("../image_convolution/" + f) for name, f in image_files.items()}


def make_image(arr):
    img = create_image(SRC, SRC)
    img.loadPixels()
    rgba = np.empty((SRC, SRC, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = 255
    img.pixels.set(to_js(rgba.tobytes()))
    img.updatePixels()
    return img


def setup():
    createCanvas(windowWidth, windowHeight)
    pixelDensity(1)
    noSmooth()

    global sources
    sources = {}
    for name, img in images.items():
        img.resize(SRC, SRC)
        img.loadPixels()
        arr = np.asarray(img.pixels.to_py(), dtype=np.uint8)
        sources[name] = arr.reshape((SRC, SRC, 4))[:, :, :3].astype(np.float64) / 255.0

    global master
    master = GuiBlock("Filtro nao-linear")
    master.addSelect("imagem", list(image_files.keys()), "lenna")
    master.addSelect("ruido", ["nenhum", "sal e pimenta", "gaussiano"], "sal e pimenta")
    master.addNumber("intensidade", 0.0, 0.3, 0.08, 0.01)
    master.addSelect("algoritmo", filters, "mediana")
    master.change(select_filter)
    master.position(10, 10)

    global param_blocks
    param_blocks = {}

    def add_block(name, builder):
        g = GuiBlock(name)
        builder(g)
        g.position(10, 195)
        param_blocks[name] = g

    add_block("mediana", lambda g: g.addNumber("raio", 1, 3, 1, 1))
    add_block("bilateral", lambda g: (
        g.addNumber("raio", 1, 4, 2, 1),
        g.addNumber("sigma_esp", 0.5, 6.0, 2.0, 0.5),
        g.addNumber("sigma_cor", 0.02, 0.5, 0.1, 0.01)))
    add_block("gaussiano (linear)", lambda g: g.addNumber("raio", 1, 5, 2, 1))
    add_block("media (box)", lambda g: g.addNumber("raio", 1, 3, 1, 1))
    add_block("minimo", lambda g: g.addNumber("raio", 1, 3, 1, 1))
    add_block("maximo", lambda g: g.addNumber("raio", 1, 3, 1, 1))
    add_block("Kuwahara", lambda g: g.addNumber("raio", 1, 3, 2, 1))
    for blk in param_blocks.values():
        blk.change(compute)

    global input_img, output_img
    input_img = output_img = None
    select_filter()


def select_filter():
    active = master.algoritmo
    for name, blk in param_blocks.items():
        blk.div.style("display", "block" if name == active else "none")
    compute()


# ---------------- ruido ----------------

def add_noise(clean):
    typ = master.ruido
    amt = master.intensidade
    if typ == "nenhum" or amt <= 0:
        return clean
    rng = np.random.default_rng(0)  # fixo: ruido estavel ao trocar de filtro
    if typ == "sal e pimenta":
        out = clean.copy()
        m = rng.random((SRC, SRC))
        out[m < amt / 2.0] = 0.0
        out[m > 1.0 - amt / 2.0] = 1.0
        return out
    out = clean + rng.normal(0.0, amt, (SRC, SRC, 3))
    return np.clip(out, 0.0, 1.0)


# ---------------- filtros ----------------

def neighborhood_stack(arr, r):
    """Empilha as (2r+1)^2 versoes deslocadas da vizinhanca: (K, H, W, 3)."""
    pad = np.pad(arr, ((r, r), (r, r), (0, 0)), mode="edge")
    offs = [pad[r + dy:r + dy + SRC, r + dx:r + dx + SRC]
            for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
    return np.stack(offs, axis=0)


def gaussian_filter(arr, r):
    sig = max(r / 2.0, 0.5)
    st = neighborhood_stack(arr, r)
    w = np.array([np.exp(-(dx * dx + dy * dy) / (2.0 * sig * sig))
                  for dy in range(-r, r + 1) for dx in range(-r, r + 1)])
    w = w / w.sum()
    return np.tensordot(w, st, axes=(0, 0))


def bilateral(arr, r, sig_s, sig_r):
    pad = np.pad(arr, ((r, r), (r, r), (0, 0)), mode="edge")
    num = np.zeros_like(arr)
    den = np.zeros_like(arr)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            nb = pad[r + dy:r + dy + SRC, r + dx:r + dx + SRC]
            ws = np.exp(-(dx * dx + dy * dy) / (2.0 * sig_s * sig_s))
            diff = nb - arr
            w = ws * np.exp(-(diff * diff) / (2.0 * sig_r * sig_r))
            num += w * nb
            den += w
    return num / den


def kuwahara(arr, r):
    st = neighborhood_stack(arr, r)
    offs = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
    lum = st @ LUMA  # (K, H, W)
    means, varis = [], []
    for sy, sx in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        idx = [k for k, (dy, dx) in enumerate(offs)
               if dy * sy >= 0 and dx * sx >= 0]
        means.append(st[idx].mean(axis=0))
        varis.append(lum[idx].var(axis=0))
    means = np.stack(means, axis=0)            # (4, H, W, 3)
    sel = np.argmin(np.stack(varis, axis=0), axis=0)  # (H, W)
    sel_b = np.broadcast_to(sel[None, :, :, None], (1, SRC, SRC, 3))
    return np.take_along_axis(means, sel_b, axis=0)[0]


def apply_filter(arr):
    name = master.algoritmo
    pb = param_blocks[name]
    if name == "mediana":
        return np.median(neighborhood_stack(arr, int(pb.raio)), axis=0)
    if name == "media (box)":
        return neighborhood_stack(arr, int(pb.raio)).mean(axis=0)
    if name == "minimo":
        return neighborhood_stack(arr, int(pb.raio)).min(axis=0)
    if name == "maximo":
        return neighborhood_stack(arr, int(pb.raio)).max(axis=0)
    if name == "gaussiano (linear)":
        return gaussian_filter(arr, int(pb.raio))
    if name == "bilateral":
        return bilateral(arr, int(pb.raio), pb.sigma_esp, pb.sigma_cor)
    if name == "Kuwahara":
        return kuwahara(arr, int(pb.raio))
    return arr


def compute():
    global input_img, output_img
    clean = sources[master.imagem]
    noisy = add_noise(clean)
    result = np.clip(apply_filter(noisy), 0.0, 1.0)
    input_img = make_image(noisy)
    output_img = make_image(result)


# ---------------- desenho ----------------

def draw():
    background(28)

    fz = width * 0.011
    if fz < 13:
        fz = 13
    if fz > 22:
        fz = 22

    gap = 30
    a = (width * 0.94 - gap) / 2
    b = height * 0.74
    panel = a if a < b else b
    total = panel * 2 + gap
    startx = (width - total) / 2
    y = (height - panel) / 2

    left_label = f"entrada ({master.ruido})"
    right_label = master.algoritmo
    cols = [(startx, input_img, left_label),
            (startx + panel + gap, output_img, right_label)]

    for cx, img, lab in cols:
        if img is not None:
            image(img, cx, y, panel, panel)
        no_fill()
        stroke(80)
        rect(cx, y, panel, panel)
        no_stroke()
        fill(235)
        text_size(fz)
        text_align(CENTER, TOP)
        text(lab, cx + panel / 2, y + panel + 8)

    fill(165)
    text_size(fz * 0.85)
    text_align(CENTER, BOTTOM)
    text("Filtros nao-lineares na CPU. O ruido e fixo (mesma semente) para "
         "comparar filtros sobre a mesma imagem.", width / 2, height - 8)


def window_resized():
    resizeCanvas(windowWidth, windowHeight)
