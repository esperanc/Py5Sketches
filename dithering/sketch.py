"""
Dithering — reduz o numero de cores de uma imagem para uma PALETA fixa,
espalhando o erro de quantizacao para enganar o olho.

Mostra UM metodo por vez (seletor "method"):
  - original
  - ordered 4x4     (mascara de Bayer)              -> shader
  - ordered 16x16   (mascara de Bayer)              -> shader
  - blue noise      (textura de ruido azul)         -> shader, animavel
  - IGN             (Interleaved Gradient Noise)     -> shader, animavel
  - Floyd-Steinberg (difusao de erro, sequencial)    -> CPU

Sobre os dois ruidos que substituem o ruido branco:
  * Blue noise: mesmo algoritmo dos ordered dithers, mas o limiar vem de uma
    textura de ruido azul (energia nas altas frequencias, sem aglomerados de
    baixa frequencia). O padrao e bem menos perceptivel que Bayer; e o padrao
    moderno em tempo real e pode ser animado no tempo (casa com TAA).
  * IGN (Jorge Jimenez): hash analitico, sem textura, baratissimo e com
    qualidade proxima a blue noise.
  A animacao temporal (checkbox) desloca o limiar a cada frame.

PALETA (controle explicito, com amostras na legenda):
  - "P&B (1-bit)"        : {preto, branco}
  - "Cinza (4 niveis)"   : 4 tons de cinza
  - "Impressora 8 cores" : {Branco, Preto, C, M, Y, R, G, B}  (modelo subtrativo)
  - "RGB (27 cores)"     : cubo 3x3x3
Paletas em tons de cinza ditheram a LUMINOSIDADE; as demais ditheram em RGB.

Fonte: gradientes procedurais ou fotos reais (lenna, baboon).
"""
import numpy as np
from gui import GuiBlock
from pyodide.ffi import to_js

SRC = 256       # resolucao de trabalho (shader e Floyd-Steinberg)
BLUE_N = 64     # tamanho da textura de blue noise (tileavel)

synthetic_sources = {"gray_ramp": 0, "color": 1, "radial": 2}
image_files = {
    "cameraman": "cameraman.bmp", 
    "lenna": "lenna.bmp",
    "baboon": "baboon.bmp"}

method_codes = {
    "original": 0,
    "ordered 4x4": 1,
    "ordered 16x16": 2,
    "blue noise": 3,
    "IGN": 4,
    "Floyd-Steinberg": -1,  # CPU
}


def gray_levels(n):
    return [(i / (n - 1),) * 3 for i in range(n)]


def rgb_cube(n):
    f = lambda i: i / (n - 1)
    return [(f(r), f(g), f(b))
            for r in range(n) for g in range(n) for b in range(n)]


PALETTES = [
    {"name": "P&B (1-bit)",        "levels": 2, "gray": True,
     "colors": [(0, 0, 0), (1, 1, 1)]},
    {"name": "Cinza (4 niveis)",   "levels": 4, "gray": True,
     "colors": gray_levels(4)},
    {"name": "Impressora 8 cores", "levels": 2, "gray": False,
     "colors": [(1, 1, 1), (0, 0, 0), (0, 1, 1), (1, 0, 1),
                (1, 1, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]},
    {"name": "RGB (27 cores)",     "levels": 3, "gray": False,
     "colors": rgb_cube(3)},
]
palette_by_name = {p["name"]: p for p in PALETTES}


def source_rgb(u, v):
    """Fonte procedural — DEVE casar com source() em dither.glsl."""
    s = gui.source
    if s == "gray_ramp":
        return (u, u, u)
    elif s == "color":
        return (u, v, (u + v) * 0.5)
    else:  # radial
        dx = u - 0.5
        dy = v - 0.5
        d = min(1.0, (dx * dx + dy * dy) ** 0.5 * 2.0)
        return (1.0 - d, 1.0 - d, 1.0 - d)


def generate_blue_noise(n=BLUE_N, iters=50, sigma=1.5):
    """Gera um tile de blue noise por filtragem passa-alta iterativa + rank.

    Cada iteracao remove as baixas frequencias (subtraindo uma versao
    suavizada por Gaussiana) e re-normaliza os valores por ranking para uma
    distribuicao uniforme. Converge para um padrao com espectro 'azul'.
    """
    rng = np.random.default_rng(1)
    v = rng.random((n, n))

    fx = np.fft.fftfreq(n)
    kx, ky = np.meshgrid(fx, fx)
    r2 = kx * kx + ky * ky
    lowpass = np.exp(-2.0 * (np.pi ** 2) * (sigma ** 2) * r2)  # Gaussiana no dominio da frequencia

    for _ in range(iters):
        low = np.real(np.fft.ifft2(np.fft.fft2(v) * lowpass))
        high = v - low
        ranks = np.argsort(np.argsort(high.ravel(), kind="stable"))
        v = (ranks.reshape(n, n).astype(np.float64) + 0.5) / (n * n)
    return v


def preload():
    global vert_src, dither_src, images
    vert_src = loadStrings("vert.glsl")
    dither_src = loadStrings("dither.glsl")
    images = {name: loadImage(f) for name, f in image_files.items()}


def _join(lines):
    return "\n".join(str(s) for s in lines)


def setup():
    createCanvas(windowWidth, windowHeight, WEBGL)
    pixelDensity(1)

    global dither_shader
    dither_shader = createShader(_join(vert_src), _join(dither_src))

    # Imagens -> resolucao de trabalho + leitura de pixels (para o FS).
    global image_px
    image_px = {}
    for name, img in images.items():
        img.resize(SRC, SRC)
        img.loadPixels()
        image_px[name] = img.pixels.to_py()

    # Textura de blue noise.
    global blue_img
    bn = generate_blue_noise()
    blue_img = create_image(BLUE_N, BLUE_N)
    blue_img.loadPixels()
    buf = bytearray(BLUE_N * BLUE_N * 4)
    k = 0
    for y in range(BLUE_N):
        for x in range(BLUE_N):
            val = int(bn[y, x] * 255.0 + 0.5)
            buf[k] = val
            buf[k + 1] = val
            buf[k + 2] = val
            buf[k + 3] = 255
            k += 4
    blue_img.pixels.set(to_js(buf))
    blue_img.updatePixels()

    global gui
    gui = GuiBlock()
    gui.addSelect("source", list(synthetic_sources.keys()) + list(image_files.keys()), "lenna")
    gui.addSelect("palette", [p["name"] for p in PALETTES], "Impressora 8 cores")
    gui.addSelect("method", list(method_codes.keys()), "blue noise")
    gui.addCheckbox("animate", False)
    gui.change(rebuild)

    # Framebuffer com o resultado de um metodo de shader (resolucao da imagem).
    global result_fb
    result_fb = create_framebuffer(js_object(
        {"width": SRC, "height": SRC, "density": 1}))

    # Imagem com o resultado (CPU) de Floyd-Steinberg.
    global fs_img
    fs_img = create_image(SRC, SRC)

    global legend, label
    legend = _info_div()
    label = _info_div()
    label.style("text-align", "center")
    label.style("transform", "translateX(-50%)")

    rebuild()


def _info_div():
    d = create_div("")
    d.style("position", "absolute")
    d.style("color", "white")
    d.style("font", GuiBlock.font)
    d.style("text-shadow", "0 1px 3px black")
    d.style("pointer-events", "none")
    return d


def update_legend(pal):
    swatches = ""
    for (r, g, b) in pal["colors"]:
        css = f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})"
        swatches += (f'<span style="display:inline-block;width:16px;height:16px;'
                     f'background:{css};border:1px solid #999;margin:0 2px;'
                     f'vertical-align:middle"></span>')
    legend.style("background", "rgba(0,0,0,0.45)")
    legend.style("padding", "6px 10px")
    legend.style("border-radius", "4px")
    legend.html(f'<b>paleta:</b> {pal["name"]} ({len(pal["colors"])} cores)<br>{swatches}')


def rebuild():
    """Chamado a cada mudanca na GUI. So o Floyd-Steinberg precisa de pre-calculo."""
    pal = palette_by_name[gui.palette]
    update_legend(pal)
    if method_codes[gui.method] == -1:  # Floyd-Steinberg
        floyd_steinberg(pal, gui.source in image_files)


def render_shader(method, pal, is_image):
    """Renderiza um metodo de shader no framebuffer (resolucao da imagem)."""
    animate = gui.animate and method in (3, 4)
    bound = images[gui.source] if is_image else images[next(iter(image_files))]

    result_fb.begin()
    clear()
    shader(dither_shader)
    dither_shader.setUniform("u_source", synthetic_sources.get(gui.source, 0))
    dither_shader.setUniform("u_useImage", 1 if is_image else 0)
    dither_shader.setUniform("u_image", bound)
    dither_shader.setUniform("u_method", method)
    dither_shader.setUniform("u_mode", 1 if pal["gray"] else 0)
    dither_shader.setUniform("u_levels", float(pal["levels"]))
    dither_shader.setUniform("u_blue", blue_img)
    dither_shader.setUniform("u_blueSize", float(BLUE_N))
    dither_shader.setUniform("u_frame", float(frameCount) if animate else 0.0)
    no_stroke()
    plane(result_fb.width, result_fb.height)
    result_fb.end()
    reset_shader()


def floyd_steinberg(pal, is_image):
    """Difusao de erro de Floyd-Steinberg (sequencial) na CPU."""
    W = H = SRC
    lum = pal["gray"]
    L = pal["levels"]
    maxlv = float(L - 1)
    ch = 1 if lum else 3
    px = image_px[gui.source] if is_image else None

    buf = [0.0] * (W * H * ch)
    for y in range(H):
        v = (y + 0.5) / H
        for x in range(W):
            if is_image:
                i = (y * W + x) * 4
                r = px[i] / 255.0
                g = px[i + 1] / 255.0
                b = px[i + 2] / 255.0
            else:
                r, g, b = source_rgb((x + 0.5) / W, v)
            base = (y * W + x) * ch
            if lum:
                buf[base] = 0.2126 * r + 0.7152 * g + 0.0722 * b
            else:
                buf[base] = r
                buf[base + 1] = g
                buf[base + 2] = b

    out = bytearray(W * H * 4)
    for y in range(H):
        last_y = (y + 1 < H)
        nrow = (y + 1) * W
        for x in range(W):
            base = (y * W + x) * ch
            o4 = (y * W + x) * 4
            for c in range(ch):
                old = buf[base + c]
                if old < 0.0:
                    old = 0.0
                elif old > 1.0:
                    old = 1.0
                q = round(old * maxlv) / maxlv
                err = old - q
                val = int(q * 255.0 + 0.5)
                if lum:
                    out[o4] = val
                    out[o4 + 1] = val
                    out[o4 + 2] = val
                else:
                    out[o4 + c] = val
                if x + 1 < W:
                    buf[base + ch + c] += err * 0.4375
                if last_y:
                    nb = (nrow + x) * ch + c
                    if x > 0:
                        buf[nb - ch] += err * 0.1875
                    buf[nb] += err * 0.3125
                    if x + 1 < W:
                        buf[nb + ch] += err * 0.0625
            out[o4 + 3] = 255

    fs_img.loadPixels()
    fs_img.pixels.set(to_js(out))
    fs_img.updatePixels()


def draw():
    background(30)

    pal = palette_by_name[gui.palette]
    is_image = gui.source in image_files
    method = method_codes[gui.method]

    size = min(width, height) * 0.7

    if method == -1:
        src = fs_img
    else:
        render_shader(method, pal, is_image)
        src = result_fb

    image(src, -size / 2, -size / 2, size, size)

    # Rotulo do metodo + legenda da paleta.
    extra = "  (animado)" if (gui.animate and method in (3, 4)) else ""
    label.html(gui.method + extra)
    label.style("width", f"{int(size)}px")
    label.position(int(width / 2), int(height / 2 + size / 2 + 12))
    legend.position(10, int(height) - 70)


def window_resized():
    resizeCanvas(windowWidth, windowHeight)
