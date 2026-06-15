"""
Reamostragem (resampling) — ilustra a interpolacao usada para redimensionar.

  UPSAMPLING (ampliar):  vizinho mais proximo | bilinear | bicubica
  DOWNSAMPLING (reduzir): original | sem pre-filtro (aliasing) | com pre-filtro

As imagens de teste sao sinteticas, em preto e branco, geradas analiticamente
num shader (zone plate, estrela de Siemens, xadrez, chirp). Como a fonte e
"limpa" (band-limited), os artefatos que aparecem vem apenas da reamostragem.

Toda a reamostragem e feita em shaders (pattern.glsl e resample.glsl).
"""
from gui import GuiBlock

HI = 512        # resolucao da fonte usada na demo de downsampling
PANEL_RES = 512  # resolucao interna de cada painel renderizado

patterns = {
    "zone_plate": 0,
    "siemens_star": 1,
    "checker": 2,
    "chirp": 3,
}

# (op, method, prefilter) por painel, e os rotulos exibidos.
panel_setups = {
    "upsample": [(0, 0, 0), (0, 1, 0), (0, 2, 0)],
    "downsample": [(0, 1, 0), (1, 0, 0), (1, 0, 1)],
}
panel_labels = {
    "upsample": ["vizinho mais proximo", "bilinear", "bicubica"],
    "downsample": ["original (alta resolucao)", "sem pre-filtro -> aliasing",
                   "com pre-filtro"],
}


def preload():
    # Carregamos o codigo-fonte dos shaders como texto e compilamos com
    # createShader(). Isso evita o loadShader(), que em modo standalone
    # duplica o prefixo da pasta ao chamar loadStrings internamente.
    global vert_src, pattern_src, resample_src
    vert_src = loadStrings("vert.glsl")
    pattern_src = loadStrings("pattern.glsl")
    resample_src = loadStrings("resample.glsl")


def _join(lines):
    return "\n".join(str(s) for s in lines)


def setup():
    createCanvas(windowWidth, windowHeight, WEBGL)
    pixelDensity(1)

    global pattern_shader, resample_shader
    v = _join(vert_src)
    pattern_shader = createShader(v, _join(pattern_src))
    resample_shader = createShader(v, _join(resample_src))

    global gui
    gui = GuiBlock()
    gui.addSelect("demo", ["upsample", "downsample"], "upsample")
    gui.addSelect("pattern", patterns.keys(), "checker")
    gui.addNumber("resolution", 8, 160, 24, 2)
    gui.change(rebuild)

    # Tres framebuffers de tamanho fixo: um por painel.
    global panel_fbs
    panel_fbs = [
        create_framebuffer(js_object(
            {"width": PANEL_RES, "height": PANEL_RES, "density": 1}))
        for _ in range(3)
    ]

    global src_fb
    src_fb = None

    # Rotulos em HTML sob cada painel.
    global labels
    labels = []
    for _ in range(3):
        d = create_div("")
        d.style("position", "absolute")
        d.style("color", "white")
        d.style("font", GuiBlock.font)
        d.style("text-align", "center")
        d.style("transform", "translateX(-50%)")
        d.style("pointer-events", "none")
        d.style("text-shadow", "0 1px 3px black")
        labels.append(d)

    rebuild()


def source_size():
    # Upsampling parte de uma fonte grosseira; downsampling de uma fonte fina.
    return int(gui.resolution) if gui.demo == "upsample" else HI


def rebuild():
    """Regera a fonte e renderiza os tres paineis. Chamado a cada mudanca."""
    global src_fb
    size = source_size()
    if src_fb is None or src_fb.width != size:
        if src_fb is not None:
            src_fb.remove()
        src_fb = create_framebuffer(js_object(
            {"width": size, "height": size, "density": 1}))

    # 1) Gera o padrao sintetico na fonte.
    src_fb.begin()
    clear()
    shader(pattern_shader)
    pattern_shader.setUniform("u_pattern", patterns[gui.pattern])
    no_stroke()
    plane(src_fb.width, src_fb.height)
    src_fb.end()
    reset_shader()

    # 2) Renderiza cada painel aplicando a estrategia de reamostragem.
    grid = float(int(gui.resolution))
    for fb, (op, method, prefilter) in zip(panel_fbs, panel_setups[gui.demo]):
        fb.begin()
        clear()
        shader(resample_shader)
        resample_shader.setUniform("u_src", src_fb)
        resample_shader.setUniform("u_method", method)
        resample_shader.setUniform("u_op", op)
        resample_shader.setUniform("u_prefilter", prefilter)
        resample_shader.setUniform("u_gridN", grid)
        no_stroke()
        plane(fb.width, fb.height)
        fb.end()
        reset_shader()


def draw():
    background(30)

    n = 3
    gap = 24
    avail = width * 0.92
    panel = min((avail - gap * (n - 1)) / n, height * 0.62)
    total = panel * n + gap * (n - 1)

    texts = panel_labels[gui.demo]
    for i in range(n):
        xoff = -total / 2 + panel / 2 + i * (panel + gap)
        push()
        translate(xoff, 0)
        image(panel_fbs[i], -panel / 2, -panel / 2, panel, panel)
        pop()

        sx = width / 2 + xoff
        sy = height / 2 + panel / 2 + 10
        labels[i].html(texts[i])
        labels[i].position(int(sx), int(sy))
        labels[i].style("width", f"{int(panel)}px")


def window_resized():
    resizeCanvas(windowWidth, windowHeight)
