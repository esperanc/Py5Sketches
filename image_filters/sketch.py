"""
Image filters — varição do image_convolution focada em operacoes COMPOSTAS,
que exigem varias passadas.

O shader filter.glsl implementa uma operacao por passada (COPY, GRAY, CONV3,
BLUR1D, GRADMAG, NMS, THRESH, HYST, FINALIZE, COMBINE). Aqui em Python cada
filtro e montado encadeando essas passadas entre framebuffers de rascunho.

Cada filtro e descrito por uma lista de PASSOS nomeados. Para os filtros
multi-passo, um grupo de radio buttons (reconstruido ao trocar de filtro,
default no ultimo passo) permite executar/exibir ate um passo intermediario.
Ex.: DoG -> [Gauss small, Gauss large, Combine].

Filtros:
  - grayscale
  - gaussian blur     : blur separavel  (H, depois V)
  - box blur 3x3      : convolucao unica
  - sharpen           : convolucao unica
  - unsharp masking   : blur (H, V) + combine (orig + amount*(orig-blur))
  - sobel / prewitt   : magnitude do gradiente
  - emboss            : convolucao unica
  - DoG               : difference of gaussians (Gauss small, Gauss large, Combine)
  - canny             : grayscale -> blur -> gradiente -> supressao nao-maxima ->
                        duplo limiar -> histerese
"""
from gui import GuiBlock

SRC = 320  # resolucao de trabalho

image_files = {
    "cameraman": "cameraman.bmp",
    "lenna": "lenna.bmp",
    "baboon": "baboon.bmp",
}

# Constantes de passada (espelham filter.glsl)
COPY, GRAY, CONV3, BLUR1D, GRADMAG, MAGVIEW, NMS, THRESH, HYST, FINALIZE, COMBINE = range(11)

filters = ["grayscale", "gaussian blur", "box blur", "sharpen",
           "unsharp masking", "sobel", "prewitt", "emboss", "DoG", "canny"]


def preload():
    global vert_src, filter_src, images
    vert_src = loadStrings("vert.glsl")
    filter_src = loadStrings("filter.glsl")
    # Imagens carregadas da pasta image_convolution (sem copias locais).
    prefix = "https://esperanc.github.io/Py5Sketches/image_convolution/"
    images = {name: loadImage(prefix + f) for name, f in image_files.items()}


def _join(lines):
    return "\n".join(str(s) for s in lines)


def setup():
    createCanvas(windowWidth, windowHeight, WEBGL)
    pixelDensity(1)

    global fshader
    fshader = createShader(_join(vert_src), _join(filter_src))

    for img in images.values():
        img.resize(SRC, SRC)

    # Pool de framebuffers de rascunho (ping-pong).
    global fbs
    fbs = [create_framebuffer(js_object(
        {"width": SRC, "height": SRC, "density": 1})) for _ in range(4)]

    # GuiBlock MESTRE: imagem + algoritmo.
    global master
    master = GuiBlock("Filtro")
    master.addSelect("image", image_files.keys(), "cameraman")
    master.addSelect("algorithm", filters, "DoG")
    master.change(select_filter)
    master.position(10, 10)

    # Um GuiBlock de parametros por algoritmo, todos na mesma posicao.
    global param_blocks
    param_blocks = {}

    def add_block(name, builder=None):
        title = name if builder else name + " (sem parametros)"
        g = GuiBlock(title)
        if builder:
            builder(g)
            g.position(10, 120)
        else:
            g.position(0, -200)
        param_blocks[name] = g

    add_block("grayscale")
    add_block("gaussian blur", lambda g: g.addNumber("raio", 1, 12, 3, 1))
    add_block("box blur")
    add_block("sharpen")
    add_block("unsharp masking", lambda g: (
        g.addNumber("raio", 1, 12, 3, 1),
        g.addNumber("amount", 0.0, 4.0, 1.5, 0.1)))
    add_block("sobel", lambda g: g.addNumber("ganho", 0.5, 5.0, 1.5, 0.1))
    add_block("prewitt", lambda g: g.addNumber("ganho", 0.5, 5.0, 1.5, 0.1))
    add_block("emboss")
    add_block("DoG", lambda g: (
        g.addNumber("raio", 1, 12, 3, 1),
        g.addNumber("ganho", 0.5, 5.0, 1.5, 0.1)))
    add_block("canny", lambda g: (
        g.addNumber("raio", 1, 12, 2, 1),
        g.addNumber("ganho", 0.5, 5.0, 1.5, 0.1),
        g.addNumber("limiar_alto", 0.0, 1.0, 0.30, 0.01),
        g.addNumber("limiar_baixo", 0.0, 1.0, 0.10, 0.01)))

    # Controle de passos: radio buttons em HTML simples dentro de um div
    # (reconstruido por filtro via innerHTML; leitura por querySelector).
    global step_box
    step_box = create_div("")
    step_box.style("position", "absolute")
    step_box.style("color", "white")
    step_box.style("font", GuiBlock.font)
    step_box.style("background", "rgba(0,0,0,0.5)")
    step_box.style("padding", "6px 10px")
    step_box.style("border-radius", "4px")
    step_box.position(10, 290)

    select_filter()

    global label
    label = create_div("")
    label.style("position", "absolute")
    label.style("color", "white")
    label.style("font", GuiBlock.font)
    label.style("text-align", "center")
    label.style("transform", "translateX(-50%)")
    label.style("text-shadow", "0 1px 3px black")
    label.style("pointer-events", "none")


def select_filter():
    """Mapeia/desmapeia os GuiBlocks de parametros e reconstroi os radios."""
    active = master.algorithm
    for name, blk in param_blocks.items():
        blk.div.style("display", "block" if name == active else "none")
    build_step_radio()


def build_step_radio():
    """(Re)cria os radio buttons dos passos do filtro ativo; default no ultimo."""
    labels = filter_steps[master.algorithm][0]
    if len(labels) <= 1:
        step_box.style("display", "none")
        return
    step_box.style("display", "block")
    last = len(labels) - 1
    html = '<b>passo:</b><br>'
    for i, lab in enumerate(labels):
        checked = "checked" if i == last else ""
        html += (f'<label style="display:block;white-space:nowrap">'
                 f'<input type="radio" name="step" value="{i}" {checked}> {lab}'
                 f'</label>')
    step_box.html(html)


def selected_step(last):
    """Le o passo selecionado nos radios (ou o ultimo, se nao houver)."""
    sel = step_box.elt.querySelector("input[name=step]:checked")
    return int(sel.value) if sel is not None else last


def run(dst, p, tex0, tex1=None, kernel=None, div=1.0, bias=0.0, gray=0,
        dir=(1, 0), sigma=1.0, radius=1, op=0, scale=1.0, a=1.0, b=0.0, c=0.0,
        hi=0.3, lo=0.1):
    """Executa uma passada do shader, escrevendo em dst."""
    dst.begin()
    clear()
    shader(fshader)
    fshader.setUniform("u_pass", p)
    fshader.setUniform("u_tex0", tex0)
    fshader.setUniform("u_tex1", tex1 if tex1 is not None else tex0)
    fshader.setUniform("u_kernel", js_array(kernel if kernel else [0.0] * 9))
    fshader.setUniform("u_div", float(div))
    fshader.setUniform("u_bias", float(bias))
    fshader.setUniform("u_gray", int(gray))
    fshader.setUniform("u_dir", js_array([float(dir[0]), float(dir[1])]))
    fshader.setUniform("u_sigma", float(sigma))
    fshader.setUniform("u_radius", int(radius))
    fshader.setUniform("u_op", int(op))
    fshader.setUniform("u_scale", float(scale))
    fshader.setUniform("u_a", float(a))
    fshader.setUniform("u_b", float(b))
    fshader.setUniform("u_c", float(c))
    fshader.setUniform("u_hi", float(hi))
    fshader.setUniform("u_lo", float(lo))
    no_stroke()
    plane(dst.width, dst.height)
    dst.end()
    reset_shader()


def gaussian(src, dst, tmp, radius):
    """Blur gaussiano separavel: horizontal (-> tmp) e vertical (-> dst)."""
    s = max(radius / 2.0, 0.5)
    run(tmp, BLUR1D, src, dir=(1, 0), radius=radius, sigma=s)
    run(dst, BLUR1D, tmp, dir=(0, 1), radius=radius, sigma=s)


# ---------------- filtros: cada um produz o FB de exibicao ate o passo `upto` ----

def c_grayscale(src, upto):
    run(fbs[0], GRAY, src)
    return fbs[0]


def c_box(src, upto):
    run(fbs[0], CONV3, src, kernel=[1, 1, 1, 1, 1, 1, 1, 1, 1], div=9.0)
    return fbs[0]


def c_sharpen(src, upto):
    run(fbs[0], CONV3, src, kernel=[0, -1, 0, -1, 5, -1, 0, -1, 0], div=1.0)
    return fbs[0]


def c_emboss(src, upto):
    run(fbs[0], CONV3, src, kernel=[-2, -1, 0, -1, 1, 1, 0, 1, 2], div=1.0,
        bias=0.0, gray=1)
    return fbs[0]


def c_sobel(src, upto):
    run(fbs[0], GRADMAG, src, op=0, scale=param_blocks["sobel"].ganho)
    run(fbs[1], MAGVIEW, fbs[0])
    return fbs[1]


def c_prewitt(src, upto):
    run(fbs[0], GRADMAG, src, op=1, scale=param_blocks["prewitt"].ganho)
    run(fbs[1], MAGVIEW, fbs[0])
    return fbs[1]


def c_gaussian(src, upto):
    p = param_blocks["gaussian blur"]
    r = int(p.raio)
    s = max(r / 2.0, 0.5)
    run(fbs[0], BLUR1D, src, dir=(1, 0), radius=r, sigma=s)     # blur H
    if upto == 0:
        return fbs[0]
    run(fbs[1], BLUR1D, fbs[0], dir=(0, 1), radius=r, sigma=s)  # blur V
    return fbs[1]


def c_unsharp(src, upto):
    p = param_blocks["unsharp masking"]
    r = int(p.raio)
    s = max(r / 2.0, 0.5)
    run(fbs[0], BLUR1D, src, dir=(1, 0), radius=r, sigma=s)     # blur H
    if upto == 0:
        return fbs[0]
    run(fbs[1], BLUR1D, fbs[0], dir=(0, 1), radius=r, sigma=s)  # blur V
    if upto == 1:
        return fbs[1]
    amt = p.amount
    run(fbs[2], COMBINE, src, fbs[1], a=1.0 + amt, b=-amt)      # combine
    return fbs[2]


def c_dog(src, upto):
    p = param_blocks["DoG"]
    r = int(p.raio)
    gain = p.ganho
    f0, f1, f2, f3 = fbs
    gaussian(src, f1, f0, r)                              # Gauss small -> f1
    if upto == 0:
        return f1
    gaussian(src, f3, f2, r * 2)                         # Gauss large -> f3
    if upto == 1:
        return f3
    run(f0, COMBINE, f1, f3, a=gain, b=-gain, c=0.5)     # Combine
    return f0


def c_canny(src, upto):
    p = param_blocks["canny"]
    r = int(p.raio)
    gain = p.ganho
    f0, f1, f2, f3 = fbs
    run(f0, GRAY, src)                                    # grayscale
    if upto == 0:
        return f0
    gaussian(f0, f0, f1, r)                               # blur (f0 -> f1 -> f0)
    if upto == 1:
        return f0
    run(f1, GRADMAG, f0, op=0, scale=gain)               # gradiente (empacotado)
    if upto == 2:
        run(f2, MAGVIEW, f1)                             # exibe a magnitude
        return f2
    run(f0, NMS, f1)                                      # supressao nao-maxima
    if upto == 3:
        return f0
    run(f1, THRESH, f0, hi=p.limiar_alto, lo=p.limiar_baixo)  # duplo limiar
    if upto == 4:
        return f1
    cur, other = f1, f0
    for _ in range(6):                                   # histerese iterativa
        run(other, HYST, cur)
        cur, other = other, cur
    run(other, FINALIZE, cur)
    return other


# nome -> (labels dos passos, funcao de calculo)
filter_steps = {
    "grayscale":       (["grayscale"], c_grayscale),
    "gaussian blur":   (["blur H", "blur V"], c_gaussian),
    "box blur":        (["box blur"], c_box),
    "sharpen":         (["sharpen"], c_sharpen),
    "unsharp masking": (["blur H", "blur V", "combine"], c_unsharp),
    "sobel":           (["sobel"], c_sobel),
    "prewitt":         (["prewitt"], c_prewitt),
    "emboss":          (["emboss"], c_emboss),
    "DoG":             (["Gauss small", "Gauss large", "Combine"], c_dog),
    "canny":           (["grayscale", "blur", "gradiente", "supr. nao-maxima",
                         "duplo limiar", "histerese"], c_canny),
}


def draw():
    background(30)

    name = master.algorithm
    labels, compute = filter_steps[name]
    last = len(labels) - 1
    upto = selected_step(last) if last > 0 else 0
    if upto > last:
        upto = last

    src = images[master.image]
    result = compute(src, upto)

    a = width * 0.42
    b = height * 0.72
    size = a if a < b else b
    gap = 24
    cdx = size / 2 + gap / 2

    image(src, -cdx - size / 2, -size / 2, size, size)
    image(result, cdx - size / 2, -size / 2, size, size)

    step_txt = f"  [{labels[upto]}]" if len(labels) > 1 else ""
    label.html(f"{master.image}  →  {name}{step_txt}")
    label.position(int(width / 2 + cdx), int(height / 2 + size / 2 + 10))
    label.style("width", f"{int(size)}px")


def window_resized():
    resizeCanvas(windowWidth, windowHeight)
