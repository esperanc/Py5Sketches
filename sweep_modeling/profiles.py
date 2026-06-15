"""
Curvas 2D usadas como perfis de varredura.

Dois tipos:
  • seções fechadas (cross-sections) — polígonos fechados no plano, usados
    pela extrusão linear e pelo lofting; raio ~1, centrados na origem;
  • silhuetas de revolução — polilinhas no semiplano (rho ≥ 0, y), giradas em
    torno do eixo y; as extremidades em rho = 0 fecham o sólido nos polos.
    Uma silhueta pode ser fechada (anel — caso do toro) ou aberta.
"""

import math


# ── Seções fechadas (perfil da extrusão / lofting) ──────────────────────────
def _circle(n=48, r=1.0):
    return [(r * math.cos(2 * math.pi * i / n),
             r * math.sin(2 * math.pi * i / n)) for i in range(n)]

def _square(r=0.95):
    return [(-r, -r), (r, -r), (r, r), (-r, r)]

def _triangle(r=1.0):
    return [(r * math.cos(a), r * math.sin(a))
            for a in (math.radians(90), math.radians(210), math.radians(330))]

def _star(points=5, ro=1.0, ri=0.45):
    pts = []
    for i in range(points * 2):
        r = ro if i % 2 == 0 else ri
        a = math.pi / 2 + math.pi * i / points
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts

def _gear(teeth=12, ro=1.0, ri=0.78):
    pts = []
    for i in range(teeth):
        base = 2 * math.pi * i / teeth
        step = 2 * math.pi / teeth
        a_lo, a_mid, a_hi = base, base + step * 0.5, base + step
        eps = step * 0.04
        pts.append((ro * math.cos(a_lo), ro * math.sin(a_lo)))
        pts.append((ro * math.cos(a_mid - eps), ro * math.sin(a_mid - eps)))
        pts.append((ri * math.cos(a_mid + eps), ri * math.sin(a_mid + eps)))
        pts.append((ri * math.cos(a_hi - eps), ri * math.sin(a_hi - eps)))
    return pts

def _cross(t=0.40, r=1.0):
    a = t * r
    return [(-a, -r), (a, -r), (a, -a), (r, -a), (r, a), (a, a),
            (a, r), (-a, r), (-a, a), (-r, a), (-r, -a), (-a, -a)]


CROSS = {
    "Círculo":     _circle,
    "Quadrado":    _square,
    "Triângulo":   _triangle,
    "Estrela":     _star,
    "Engrenagem":  _gear,
    "Cruz":        _cross,
}
CROSS_NAMES = ["Círculo", "Quadrado", "Triângulo", "Estrela", "Engrenagem", "Cruz"]


# ── Silhuetas de revolução: (lista de (rho, y), fechada?) ───────────────────
def _sphere_sil(n=24, R=1.0):
    pts = [(R * math.sin(math.pi * i / n), -R * math.cos(math.pi * i / n))
           for i in range(n + 1)]
    return pts, False

def _top_sil():
    # pião: ponta embaixo, equador largo, haste curta no topo
    raw = [(0.00, -1.05), (0.34, -0.62), (0.92, -0.05), (0.66, 0.18),
           (0.20, 0.34), (0.20, 0.78), (0.10, 0.92), (0.00, 0.96)]
    return raw, False

def _vase_sil():
    raw = [(0.00, -1.00), (0.52, -1.00), (0.56, -0.86), (0.30, -0.42),
           (0.40, 0.02), (0.62, 0.46), (0.66, 0.74), (0.50, 0.92),
           (0.30, 0.99), (0.00, 1.00)]
    return raw, False

def _torus_sil(n=28, Rc=0.62, rt=0.32):
    pts = [(Rc + rt * math.cos(2 * math.pi * i / n),
            rt * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return pts, True


SILH = {
    "Esfera":  _sphere_sil,
    "Pião":    _top_sil,
    "Vaso":    _vase_sil,
    "Toro":    _torus_sil,
}
SILH_NAMES = ["Esfera", "Pião", "Vaso", "Toro"]


# ── Reamostragem por comprimento de arco (para o lofting) ───────────────────
def resample_closed(poly, N):
    """Reamostra um polígono fechado em N pontos equiespaçados por arco."""
    m = len(poly)
    seg = []
    total = 0.0
    for i in range(m):
        a = poly[i]
        b = poly[(i + 1) % m]
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        seg.append(d)
        total += d
    if total < 1e-12:
        return [poly[0]] * N
    step = total / N
    out = []
    i = 0
    acc = 0.0
    for k in range(N):
        target = k * step
        while i < m - 1 and acc + seg[i] < target:
            acc += seg[i]
            i += 1
        a = poly[i]
        b = poly[(i + 1) % m]
        local = (target - acc) / seg[i] if seg[i] > 1e-12 else 0.0
        out.append((a[0] + (b[0] - a[0]) * local,
                    a[1] + (b[1] - a[1]) * local))
    return out
