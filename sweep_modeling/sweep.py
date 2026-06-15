"""
Modelagem por varredura sobre a estrutura half-edge.

Uma curva 2D (o *perfil*) é varrida ao longo de outra curva (a *trajetória*),
gerando uma malha. Três esquemas:

  • Extrusão linear  — perfil fechado transladado ao longo de uma reta;
  • Revolução        — silhueta girada em torno do eixo y;
  • Lofting          — interpolação entre dois perfis ao longo da reta.

Internamente tudo vira uma grade paramétrica de vértices V[s][i] (s = estação
ao longo da varredura, i = ponto do perfil). `_grid_mesh` costura essa grade em
quadriláteros (e tampas, se preciso), solda vértices coincidentes — o que faz
os polos da revolução colapsarem num único vértice — e devolve (posições,
faces) com orientação coerente (normais para fora) para alimentar `Mesh`.
"""

import math
import profiles
import half_edge as he

SCALE = 150.0     # raio do perfil em unidades de mundo
HEIGHT = 2.4      # altura total da extrusão / lofting (× SCALE)


# ── Costura da grade → malha ────────────────────────────────────────────────
def _dedup_ring(ids):
    out = []
    for x in ids:
        if not out or out[-1] != x:
            out.append(x)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out

def _signed_volume(P, faces):
    vol = 0.0
    for ring in faces:
        if len(ring) < 3:
            continue
        a = P[ring[0]]
        for i in range(1, len(ring) - 1):
            b = P[ring[i]]
            c = P[ring[i + 1]]
            vol += (a[0] * (b[1] * c[2] - b[2] * c[1])
                    - a[1] * (b[0] * c[2] - b[2] * c[0])
                    + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return vol / 6.0

def _grid_mesh(rows, wrap_s, wrap_i, cap0=False, cap1=False):
    S = len(rows)
    M = len(rows[0])

    # solda vértices por posição arredondada (funde polos e costuras)
    positions = []
    index = {}
    gid = [[0] * M for _ in range(S)]
    for s in range(S):
        for i in range(M):
            p = rows[s][i]
            k = (round(p[0], 3), round(p[1], 3), round(p[2], 3))
            j = index.get(k)
            if j is None:
                j = len(positions)
                index[k] = j
                positions.append(p)
            gid[s][i] = j

    faces = []
    s_segs = S if wrap_s else S - 1
    i_segs = M if wrap_i else M - 1
    for s in range(s_segs):
        s1 = (s + 1) % S
        for i in range(i_segs):
            i1 = (i + 1) % M
            ring = _dedup_ring([gid[s][i], gid[s][i1], gid[s1][i1], gid[s1][i]])
            if len(ring) >= 3:
                faces.append(ring)

    # tampas nas extremidades da varredura (fecham o anel do perfil)
    if cap0:
        ring = _dedup_ring([gid[0][i] for i in range(M - 1, -1, -1)])
        if len(ring) >= 3:
            faces.append(ring)
    if cap1:
        ring = _dedup_ring([gid[S - 1][i] for i in range(M)])
        if len(ring) >= 3:
            faces.append(ring)

    # orienta para fora (volume positivo); preserva a coerência das normais
    if _signed_volume(positions, faces) < 0.0:
        faces = [list(reversed(r)) for r in faces]

    return positions, faces


def _to_mesh(rows, wrap_s, wrap_i, cap0, cap1):
    pos, faces = _grid_mesh(rows, wrap_s, wrap_i, cap0, cap1)
    return he.Mesh(pos, faces, orient=False)


# ── Esquemas de varredura ───────────────────────────────────────────────────
def extrude(prof, sections, twist_deg, frac):
    """Perfil fechado `prof` extrudado ao longo de +y; `frac` ∈ (0,1] mostra a
    varredura parcial (a base fica fixa e a forma cresce)."""
    Hf = HEIGHT * SCALE
    y0 = -Hf / 2.0
    grow = Hf * frac
    tw = math.radians(twist_deg)
    rows = []
    for s in range(sections + 1):
        t = s / sections
        y = y0 + grow * t
        c, sn = math.cos(tw * t), math.sin(tw * t)
        row = [((x * c - z * sn) * SCALE, y, (x * sn + z * c) * SCALE)
               for (x, z) in prof]
        rows.append(row)
    mesh = _to_mesh(rows, wrap_s=False, wrap_i=True, cap0=True, cap1=True)
    prof_curve = [((x) * SCALE, y0, (z) * SCALE) for (x, z) in prof]
    traj = [(0.0, y0, 0.0), (0.0, y0 + grow, 0.0)]
    return mesh, (prof_curve, True), (traj, False), False


def loft(profA, profB, sections, twist_deg, frac):
    """Interpola entre dois perfis (reamostrados para o mesmo nº de pontos)."""
    N = 72
    A = profiles.resample_closed(profA, N)
    B = profiles.resample_closed(profB, N)
    Hf = HEIGHT * SCALE
    y0 = -Hf / 2.0
    grow = Hf * frac
    tw = math.radians(twist_deg)
    rows = []
    for s in range(sections + 1):
        t = s / sections
        y = y0 + grow * t
        c, sn = math.cos(tw * t), math.sin(tw * t)
        row = []
        for k in range(N):
            x = A[k][0] + (B[k][0] - A[k][0]) * t
            z = A[k][1] + (B[k][1] - A[k][1]) * t
            row.append(((x * c - z * sn) * SCALE, y, (x * sn + z * c) * SCALE))
        rows.append(row)
    mesh = _to_mesh(rows, wrap_s=False, wrap_i=True, cap0=True, cap1=True)
    prof_curve = [(x * SCALE, y0, z * SCALE) for (x, z) in A]
    traj = [(0.0, y0, 0.0), (0.0, y0 + grow, 0.0)]
    return mesh, (prof_curve, True), (traj, False), False


def revolve(sil_pts, closed_profile, sections, angle_deg):
    """Silhueta (rho, y) girada em torno do eixo y por `angle_deg` graus."""
    full = angle_deg >= 359.9
    nst = sections if full else sections + 1
    ang = math.radians(angle_deg)
    rows = []
    for s in range(nst):
        th = ang * s / sections
        c, sn = math.cos(th), math.sin(th)
        row = [(rho * SCALE * c, y * SCALE, rho * SCALE * sn)
               for (rho, y) in sil_pts]
        rows.append(row)
    mesh = _to_mesh(rows, wrap_s=full, wrap_i=closed_profile,
                    cap0=not full, cap1=not full)
    prof_curve = [(rho * SCALE, y * SCALE, 0.0) for (rho, y) in sil_pts]
    # trajetória: círculo descrito pelo ponto de maior rho
    rho_max = max(rho for (rho, _) in sil_pts)
    y_at = next(y for (rho, y) in sil_pts if rho == rho_max)
    K = 64
    traj = [(rho_max * SCALE * math.cos(2 * math.pi * i / K), y_at * SCALE,
             rho_max * SCALE * math.sin(2 * math.pi * i / K)) for i in range(K)]
    return mesh, (prof_curve, closed_profile), (traj, True), True


# ── Despacho ────────────────────────────────────────────────────────────────
TIPOS = ["Extrusão linear", "Revolução", "Lofting"]

def build(tipo, perfil, alvo, silhueta, sections, twist_deg, sweep_pct):
    """Devolve dict com a malha e as curvas geradoras para destaque."""
    sections = max(2, int(sections))
    frac = max(0.02, sweep_pct / 100.0)
    if tipo == "Revolução":
        sil, closed = profiles.SILH[silhueta]()
        angle = 360.0 * frac
        mesh, prof, traj, axis = revolve(sil, closed, sections, angle)
        active = f"silhueta={silhueta}  ângulo={angle:.0f}°"
    elif tipo == "Lofting":
        pA = profiles.CROSS[perfil]()
        pB = profiles.CROSS[alvo]()
        mesh, prof, traj, axis = loft(pA, pB, sections, twist_deg, frac)
        active = f"{perfil} → {alvo}  torção={twist_deg:g}°"
    else:
        p = profiles.CROSS[perfil]()
        mesh, prof, traj, axis = extrude(p, sections, twist_deg, frac)
        active = f"perfil={perfil}  torção={twist_deg:g}°"
    return {
        "mesh": mesh,
        "prof": prof[0], "prof_closed": prof[1],
        "traj": traj[0], "traj_closed": traj[1],
        "axis": axis,
        "active": active,
    }


# ── Auto-teste ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    def info(d, label):
        m = d["mesh"]
        print(f"{label:28s} V={m.n_vertices:4d} E={m.n_edges:4d} "
              f"F={m.n_faces:4d} Euler={m.euler():2d} "
              f"fechada={m.is_closed} bordas={len(m.boundary)}")

    for nm in profiles.CROSS_NAMES:
        info(build("Extrusão linear", nm, "Círculo", "Esfera", 24, 0, 100), f"extrude {nm}")
    info(build("Extrusão linear", "Quadrado", "Círculo", "Esfera", 24, 180, 100), "extrude torção 180")
    for nm in profiles.SILH_NAMES:
        info(build("Revolução", "Círculo", "Círculo", nm, 48, 0, 100), f"revolve {nm}")
    info(build("Revolução", "Círculo", "Círculo", "Esfera", 48, 0, 60), "revolve parcial 60%")
    info(build("Lofting", "Quadrado", "Círculo", "Esfera", 32, 90, 100), "loft quad→círc")
    info(build("Lofting", "Estrela", "Engrenagem", "Esfera", 32, 0, 100), "loft estrela→engr")
    print("OK")
