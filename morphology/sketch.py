"""
Limiarização (threshold) + operações morfológicas.

  - Um slider 'limiar' separa a imagem (em tons de cinza) em duas classes.
  - 'ruido' adiciona ruido branco antes da limiarizacao (gera respingos).
  - Botoes aplicam morfologia a imagem binaria CORRENTE (acumulativo):
      Erosao, Dilatacao, Abertura (erosao+dilatacao), Fechamento (dilatacao+erosao)
  - 'Restaurar' volta a imagem binaria recem-limiarizada.

O elemento estruturante e um quadrado (2r+1) com raio configuravel.

Esquerda: imagem em tons de cinza (com ruido). Direita: imagem binaria atual.
"""
import numpy as np
from gui import GuiBlock
from pyodide.ffi import to_js, create_proxy

SRC = 256

# formas de elemento estruturante
SHAPES = ["quadrado", "disco", "cruz", "linha H", "linha V"]


def make_shapes():
    """Disco com furos pequenos (fechamento preenche), um furo grande (resiste)
    e respingos de 1px (abertura remove)."""
    x = np.arange(SRC)
    X, Y = np.meshgrid(x, x)
    a = np.zeros((SRC, SRC))
    cx, cy = SRC * 0.42, SRC * 0.5
    a[(X - cx) ** 2 + (Y - cy) ** 2 < (SRC * 0.30) ** 2] = 1.0   # disco
    # furos pequenos (~2px de raio) que o fechamento preenche
    for (hx, hy) in [(0.34, 0.42), (0.48, 0.40), (0.44, 0.58),
                     (0.34, 0.56), (0.52, 0.54)]:
        a[(X - SRC * hx) ** 2 + (Y - SRC * hy) ** 2 < (SRC * 0.009) ** 2] = 0.0
    # um furo grande, que resiste ao fechamento
    a[(X - SRC * 0.42) ** 2 + (Y - SRC * 0.50) ** 2 < (SRC * 0.05) ** 2] = 0.0
    # respingos de 1px (a abertura remove)
    rng = np.random.default_rng(2)
    for _ in range(70):
        sx = rng.integers(2, SRC - 2)   # indice numpy: usar direto na fatia
        sy = rng.integers(2, SRC - 2)
        a[sy, sx] = 1.0
    return a


def preload():
    global images
    # Imagens carregadas da pasta image_convolution (sem copias locais).
    prefix = "https://esperanc.github.io/Py5Sketches/image_convolution/"
    images = {"cameraman": loadImage(prefix + "cameraman.bmp"),
              "lenna": loadImage(prefix + "lenna.bmp")}


LUMA = np.array([0.2126, 0.7152, 0.0722])


def make_image(a):
    """p5.Image em tons de cinza a partir de array (H, W) em [0,1]."""
    img = create_image(SRC, SRC)
    img.loadPixels()
    g = np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)
    rgba = np.empty((SRC, SRC, 4), dtype=np.uint8)
    rgba[:, :, 0] = g
    rgba[:, :, 1] = g
    rgba[:, :, 2] = g
    rgba[:, :, 3] = 255
    img.pixels.set(to_js(rgba.tobytes()))
    img.updatePixels()
    return img


def setup():
    createCanvas(windowWidth, windowHeight)
    pixelDensity(1)
    noSmooth()

    global sources
    sources = {"formas": make_shapes()}
    for name, img in images.items():
        img.resize(SRC, SRC)
        img.loadPixels()
        arr = np.asarray(img.pixels.to_py(), dtype=np.uint8)
        rgb = arr.reshape((SRC, SRC, 4))[:, :, :3].astype(np.float64) / 255.0
        sources[name] = rgb @ LUMA

    global master
    master = GuiBlock("Morfologia")
    master.addSelect("imagem", list(sources.keys()), "formas")
    master.addNumber("limiar", 0.0, 1.0, 0.5, 0.01)
    master.addNumber("ruido", 0.0, 0.3, 0.0, 0.01)
    master.addNumber("elemento", 1, 4, 1, 1)
    master.addSelect("forma", SHAPES, "quadrado")
    master.change(reset_work)

    # Botoes de morfologia (createButton) empilhados.
    global buttons
    buttons = []
    ops = [("Erosao", "erosao"), ("Dilatacao", "dilatacao"),
           ("Abertura", "abertura"), ("Fechamento", "fechamento"),
           ("Gradiente", "gradiente")]
    y0 = 200
    # p5 passa o evento como argumento -> aceitar *a e ignorar.
    for i, (label, op) in enumerate(ops):
        buttons.append(_button(label, lambda *a, o=op: apply_op(o), 10, y0 + i * 30))
    buttons.append(_button("Restaurar", lambda *a: restore(), 10, y0 + len(ops) * 30 + 8))

    global gray_cur, base, work, history, input_img, work_img
    gray_cur = base = work = None
    history = []
    input_img = work_img = None

    reset_work()


def _button(label, fn, x, y):
    b = create_button(label)
    b.position(x, y)
    b.style("width", "120px")
    b.mousePressed(create_proxy(fn))
    return b


def add_noise(gray):
    amt = master.ruido
    if amt <= 0:
        return gray
    rng = np.random.default_rng(0)  # fixo: estavel ao mexer no limiar
    return np.clip(gray + rng.normal(0.0, amt, (SRC, SRC)), 0.0, 1.0)


def reset_work():
    """Recalcula a imagem em cinza (com ruido) e a binaria limiarizada."""
    global gray_cur, base, work, history, input_img, work_img
    gray_cur = add_noise(sources[master.imagem])
    base = (gray_cur > master.limiar).astype(np.float64)
    work = base.copy()
    history = []
    input_img = make_image(gray_cur)
    work_img = make_image(work)


def restore():
    global work, history, work_img
    work = base.copy()
    history = []
    work_img = make_image(work)


# ---------------- morfologia ----------------

def se_offsets(r, shape):
    """Deslocamentos (dy, dx) pertencentes ao elemento estruturante."""
    offs = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if shape == "disco":
                inc = dx * dx + dy * dy <= r * r
            elif shape == "cruz":
                inc = dx == 0 or dy == 0
            elif shape == "linha H":
                inc = dy == 0
            elif shape == "linha V":
                inc = dx == 0
            else:  # quadrado
                inc = True
            if inc:
                offs.append((dy, dx))
    return offs


def stack_se(a, r, shape):
    pad = np.pad(a, ((r, r), (r, r)), mode="edge")
    offs = [pad[r + dy:r + dy + SRC, r + dx:r + dx + SRC]
            for (dy, dx) in se_offsets(r, shape)]
    return np.stack(offs, axis=0)


def erode(a, r, shape):
    return stack_se(a, r, shape).min(axis=0)


def dilate(a, r, shape):
    return stack_se(a, r, shape).max(axis=0)


def apply_op(op):
    global work, work_img
    r = int(master.elemento)
    sh = master.forma
    if op == "erosao":
        work = erode(work, r, sh)
    elif op == "dilatacao":
        work = dilate(work, r, sh)
    elif op == "abertura":
        work = dilate(erode(work, r, sh), r, sh)
    elif op == "fechamento":
        work = erode(dilate(work, r, sh), r, sh)
    elif op == "gradiente":
        work = np.clip(dilate(work, r, sh) - erode(work, r, sh), 0.0, 1.0)
    history.append(op)
    work_img = make_image(work)


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
    b = height * 0.72
    panel = a if a < b else b
    total = panel * 2 + gap
    startx = (width - total) / 2
    y = (height - panel) / 2

    r = int(master.elemento)
    seq = " → ".join(history) if history else "(sem operacoes)"
    cols = [
        (startx, input_img, f"cinza + ruido   (limiar={master.limiar:.2f})"),
        (startx + panel + gap, work_img,
         f"binaria — elemento: {master.forma} (r={r})"),
    ]

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
    text_size(fz * 0.9)
    text_align(CENTER, BOTTOM)
    text("operacoes aplicadas:  " + seq, width / 2, height - 8)


def window_resized():
    resizeCanvas(windowWidth, windowHeight)
