"""
Campos escalares implícitos f(x,y,z) para extração de iso-superfície.

Convenção: o «interior» do sólido é a região onde f < nível (por omissão
nível = 0); a superfície é a iso-superfície f = nível. Todos os campos estão
normalizados para serem adimensionais e de ordem ~1 junto da superfície, de
modo a que o controlo «nível» varra um intervalo útil [-0.9, 0.9] em todos.

Cada entrada de FIELDS é (função, B), onde B é a meia-extensão recomendada da
caixa de amostragem [-B, B]^3 em coordenadas de mundo.
"""

import math


# ── Esfera ──────────────────────────────────────────────────────────────────
def _sphere(x, y, z):
    r = 150.0
    return (x * x + y * y + z * z) / (r * r) - 1.0


# ── Toro ────────────────────────────────────────────────────────────────────
def _torus(x, y, z):
    R0, r = 112.0, 46.0
    q = math.sqrt(x * x + y * y) - R0
    return (q * q + z * z) / (r * r) - 1.0


# ── Giroide (superfície mínima triplamente periódica) ───────────────────────
_GK = 2.0 * math.pi / 150.0
def _gyroid(x, y, z):
    return (math.sin(_GK * x) * math.cos(_GK * y) +
            math.sin(_GK * y) * math.cos(_GK * z) +
            math.sin(_GK * z) * math.cos(_GK * x))


# ── Metaballs (soma de núcleos suaves) ──────────────────────────────────────
_MB = [(-72.0, 0.0, 40.0, 78.0),
       (72.0, 14.0, -34.0, 86.0),
       (0.0, -64.0, -54.0, 66.0),
       (12.0, 74.0, 30.0, 60.0)]
def _metaballs(x, y, z):
    s = 0.0
    for (cx, cy, cz, rr) in _MB:
        dx, dy, dz = x - cx, y - cy, z - cz
        s += rr * rr / (dx * dx + dy * dy + dz * dz + 1.0)
    return 1.0 - s


# ── Cubo arredondado (superquádrica de grau 4) ──────────────────────────────
def _goursat(x, y, z):
    r = 142.0
    return (x ** 4 + y ** 4 + z ** 4) / (r ** 4) - 1.0


# ── Coração (superfície algébrica de Taubin) ────────────────────────────────
def _heart(x, y, z):
    s = 90.0
    X = x / s        # largura dos lóbulos
    Zup = y / s      # eixo vertical do coração ↑ (y de mundo é para cima)
    Yd = z / s       # profundidade
    a = X * X + (9.0 / 4.0) * Yd * Yd + Zup * Zup - 1.0
    return a * a * a - X * X * Zup ** 3 - (9.0 / 80.0) * Yd * Yd * Zup ** 3


FIELDS = {
    "Esfera":           (_sphere,    185.0),
    "Toro":             (_torus,     185.0),
    "Giroide":          (_gyroid,    170.0),
    "Metaballs":        (_metaballs, 200.0),
    "Cubo arredondado": (_goursat,   185.0),
    "Coração":          (_heart,     150.0),
}

FIELD_NAMES = ["Esfera", "Toro", "Giroide", "Metaballs",
               "Cubo arredondado", "Coração"]
