"""
Curvas de Hermite cúbicas interativas.

Cada segmento é definido por dois pontos de interpolação (círculos brancos)
e duas tangentes controladas por alças (círculos vermelhos).

Clique num ponto ou alça para selecioná-lo e arraste.
Enter / A     : adicionar novo segmento no final
Delete / X    : remover último segmento (mínimo: 1)
C             : alternar modo de continuidade C0 / C1
                (C1 espelha automaticamente a alça de saída)
B             : mostrar / ocultar pontos de Bézier equivalentes
"""

from gui import GuiBlock

# ── representação ──────────────────────────────────────────────────────────
# Cada segmento: { 'p0', 'p1', 't0', 't1' }
# p0,p1 : [x,y]   pontos de interpolação
# t0,t1 : [dx,dy] tangentes (vetores, não pontos absolutos)

HANDLE_SCALE = 1.0   # fator visual para exibir as alças

def hermite_point(p0, p1, t0, t1, t):
    t2 = t*t; t3 = t2*t
    h00 =  2*t3 - 3*t2 + 1
    h10 =    t3 - 2*t2 + t
    h01 = -2*t3 + 3*t2
    h11 =    t3 -   t2
    return [h00*p0[i] + h10*t0[i] + h01*p1[i] + h11*t1[i] for i in range(2)]

def bezier_handles(p0, p1, t0, t1):
    """Pontos de Bézier equivalentes."""
    q1 = [p0[i] + t0[i]/3.0 for i in range(2)]
    q2 = [p1[i] - t1[i]/3.0 for i in range(2)]
    return p0, q1, q2, p1

def default_tangent(a, b, scale=0.4):
    return [(b[i]-a[i])*scale for i in range(2)]

# ── estado global ──────────────────────────────────────────────────────────
segs     = []
selected = None   # ('p0'|'p1'|'t0'|'t1', seg_index)


def setup():
    global segs, selected
    create_canvas(window_width, window_height)
    w, h = width, height
    p0 = [w*0.2, h*0.5]
    p1 = [w*0.5, h*0.3]
    p2 = [w*0.8, h*0.5]
    segs.append({'p0': p0[:], 'p1': p1[:],
                 't0': default_tangent(p0, p1),
                 't1': default_tangent(p0, p1)})
    segs.append({'p0': p1[:], 'p1': p2[:],
                 't0': default_tangent(p1, p2),
                 't1': default_tangent(p1, p2)})
    
    
    global gui
    gui = GuiBlock()
    gui.addCheckbox("show_bezier")
    gui.addCheckbox("c1", True)

    enforce_c1_after(1, 'p0')
    
# ── helpers de hit-test ────────────────────────────────────────────────────
def handle_pos(s, role):
    """Posição absoluta de uma alça."""
    if role == 't0':
        return [s['p0'][i] + s['t0'][i] for i in range(2)]
    else:
        return [s['p1'][i] + s['t1'][i] for i in range(2)]

def hit(px, py, x, y, r=10):
    return (px-x)**2 + (py-y)**2 < r*r

def find_target(mx, my):
    """Retorna (role, idx) do elemento mais próximo do mouse, ou None."""
    for idx, s in enumerate(segs):
        if hit(mx, my, *s['p0']): return ('p0', idx)
        if hit(mx, my, *s['p1']): return ('p1', idx)
        hp = handle_pos(s, 't0')
        if hit(mx, my, *hp):      return ('t0', idx)
        hp = handle_pos(s, 't1')
        if hit(mx, my, *hp):      return ('t1', idx)
    return None

# ── continuidade C1 ────────────────────────────────────────────────────────
def enforce_c1_after(idx, moved_role):
    """
    Após mover uma tangente ou ponto, propaga C1 nas junções.
    moved_role: qual elemento foi alterado no segmento idx.
    """
    if not gui.c1:
        return
    n = len(segs)
    # junção direita do segmento idx  →  t0 do próximo
    if moved_role in ('t1', 'p1') and idx < n-1:
        s_next = segs[idx+1]
        segs[idx+1]['p0'] = segs[idx]['p1'][:]
        segs[idx+1]['t0'] = segs[idx]['t1'][:]
    # junção esquerda do segmento idx  →  t1 do anterior
    if moved_role in ('t0', 'p0') and idx > 0:
        segs[idx-1]['p1'] = segs[idx]['p0'][:]
        segs[idx-1]['t1'] = segs[idx]['t0'][:]

# ── eventos ────────────────────────────────────────────────────────────────
def mouse_pressed():
    global selected
    if mouse_button != LEFT:
        return
    selected = find_target(mouse_x, mouse_y)
    if not selected:
        # Adicionar segmento: começa no último p1 do último segmento
        last = segs[-1]
        p0 = last['p1'][:]
        t0 = last['t1'][:]
        p1 = [mouse_x, mouse_y]
        t1 = default_tangent(p0, p1)
        segs.append({'p0': p0, 'p1': p1, 't0': t0[:], 't1': t1})
    

def mouse_dragged():
    global selected
    if not selected:
        return
    role, idx = selected
    s = segs[idx]
    dx = mouse_x - pmouse_x
    dy = mouse_y - pmouse_y
    if role == 'p0':
        s['p0'][0] += dx; s['p0'][1] += dy
    elif role == 'p1':
        s['p1'][0] += dx; s['p1'][1] += dy
    elif role == 't0':
        s['t0'][0] += dx; s['t0'][1] += dy
    elif role == 't1':
        s['t1'][0] += dx; s['t1'][1] += dy
    enforce_c1_after(idx, role)

def mouse_released():
    global selected
    selected = None

def key_pressed():
    global segs
    if key in ['Delete', 'X', 'x'] and len(segs) > 1:
        segs.pop()
    

# ── desenho ────────────────────────────────────────────────────────────────
def draw_segment(s, active):
    # Curva de Hermite
    stroke(30, 80, 200)
    stroke_weight(2.5)
    no_fill()
    begin_shape()
    for i in range(60):
        pt = hermite_point(s['p0'], s['p1'], s['t0'], s['t1'], i/59.0)
        vertex(pt[0], pt[1])
    end_shape()

    # Pontos de Bézier equivalentes
    if gui.show_bezier:
        q0, q1, q2, q3 = bezier_handles(s['p0'], s['p1'], s['t0'], s['t1'])
        push()
        stroke(200, 120, 30)
        stroke_weight(1)
        no_fill()
        drawingContext.setLineDash([2, 4])
        line(q0[0],q0[1], q1[0],q1[1])
        line(q2[0],q2[1], q3[0],q3[1])
        drawingContext.setLineDash([])
        pop()
        for q, lbl in [(q1,'Q₁'),(q2,'Q₂')]:
            fill(200, 120, 30)
            no_stroke()
            circle(q[0], q[1], 7, 7)
            text(lbl, q[0]+6, q[1]-4)

    # Alças de tangente
    for role, col in [('t0',(180,50,50)), ('t1',(50,150,80))]:
        hp = handle_pos(s, role)
        anchor = s['p0'] if role=='t0' else s['p1']
        stroke(*col)
        stroke_weight(1.5)
        line(anchor[0], anchor[1], hp[0], hp[1])
        r,g,b = col
        sel = selected and selected == (role, segs.index(s))
        fill(r,g,b) if sel else fill(255,255,255)
        stroke(*col)
        stroke_weight(1.5)
        circle(hp[0], hp[1], 10, 10)

def draw():
    background(245)

    # Polígono guia (tracejado)
    push()
    stroke(200)
    stroke_weight(1)
    no_fill()
    drawingContext.setLineDash([3,6])
    begin_shape()
    for s in segs:
        vertex(s['p0'][0], s['p0'][1])
    vertex(segs[-1]['p1'][0], segs[-1]['p1'][1])
    end_shape()
    drawingContext.setLineDash([])
    pop()

    # Segmentos
    for s in segs:
        draw_segment(s, False)

    # Pontos de interpolação
    for idx, s in enumerate(segs):
        for role, pt in [('p0', s['p0']), ('p1', s['p1'])]:
            sel = selected == (role, idx)
            fill(220,60,60) if sel else fill(255)
            stroke(40)
            stroke_weight(1.5)
            circle(pt[0], pt[1], 12, 12)

    # Legenda
    # cont = "C¹" if c1_mode else "C⁰"
    # bez  = "ON" if show_bez else "OFF"
    # fill(30); no_stroke(); text_size(13)
    # text(f"Hermite  |  continuidade: {cont}  (C: alternar)  |  "
    #      f"Bézier equiv.: {bez}  (B)  |  A: add segmento  |  Delete: remover",
    #      10, 22)
    # fill(180,50,50);  text("● tangente entrada (T₀)", 10, height-28)
    # fill(50,150,80);  text("● tangente saída  (T₁)", 10, height-12)