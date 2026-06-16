#!/usr/bin/env python3
"""
Gera o indice da galeria de sketches Py5Script.

Varre as subpastas do repo que contem `sketch.py`, extrai o docstring de modulo
de cada uma e (opcionalmente) renderiza um thumbnail 800x800 do canvas usando
Chromium headless (Playwright). Produz:

  - index.json          : [{name, title, description, thumb}, ...]
  - thumbs/<nome>.png   : miniatura 400x400 de cada sketch

Uso:
  python3 build_index.py                 # tudo (texto + thumbnails)
  python3 build_index.py --no-thumbs     # so o index.json (rapido)
  python3 build_index.py --only fourier  # regerar um sketch
  python3 build_index.py --settle 8 --timeout 120

Dependencias (so para thumbnails):
  pip install playwright pillow
  python -m playwright install chromium
"""
import argparse
import ast
import functools
import http.server
import json
import os
import socket
import socketserver
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
THUMBS_DIR = ROOT / "thumbs"
INDEX_JSON = ROOT / "index.json"
THUMB_SIZE = 400          # tamanho final do thumbnail (quadrado)
VIEWPORT = 800            # janela de renderizacao (800x800, conforme pedido)


def find_sketches():
    """Subpastas (ordenadas) que contem sketch.py."""
    names = []
    for entry in sorted(os.listdir(ROOT)):
        d = ROOT / entry
        if d.is_dir() and (d / "sketch.py").is_file():
            names.append(entry)
    return names


def read_docstring(name):
    """Docstring de modulo do sketch.py, ou None."""
    src = (ROOT / name / "sketch.py").read_text(encoding="utf-8", errors="replace")
    try:
        return ast.get_docstring(ast.parse(src))
    except SyntaxError:
        return None


def make_entry(name):
    doc = read_docstring(name)
    if doc:
        doc = doc.strip()
        title = next((ln.strip() for ln in doc.splitlines() if ln.strip()), name)
    else:
        doc = ""
        title = name
    return {"name": name, "title": title, "description": doc, "thumb": None}


def uses_numpy(name):
    req = ROOT / name / "requirements.txt"
    return req.is_file() and "numpy" in req.read_text(errors="replace").lower()


# ---------------- servidor local temporario ----------------

class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def start_server():
    port = _free_port()
    handler = functools.partial(_QuietHandler, directory=str(ROOT))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ---------------- thumbnails (Playwright + Pillow) ----------------

def capture_thumbnails(entries, port, settle, timeout):
    from playwright.sync_api import sync_playwright
    from PIL import Image

    THUMBS_DIR.mkdir(exist_ok=True)
    tmo = timeout * 1000

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for e in entries:
            name = e["name"]
            page = browser.new_page(viewport={"width": VIEWPORT, "height": VIEWPORT})
            wait = settle + (30 if uses_numpy(name) else 0)
            url = f"http://127.0.0.1:{port}/index.html?folder={name}"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=tmo)
                page.wait_for_selector("canvas", timeout=tmo)
                page.wait_for_timeout(wait * 1000)
                tmp = THUMBS_DIR / f"{name}.raw.png"
                page.locator("canvas").first.screenshot(path=str(tmp), timeout=tmo)
                _finish_thumb(tmp, THUMBS_DIR / f"{name}.png", Image)
                e["thumb"] = f"thumbs/{name}.png"
                print(f"  [ok]   {name}")
            except Exception as ex:
                print(f"  [FAIL] {name}: {type(ex).__name__}: {ex}")
            finally:
                page.close()
        browser.close()


def _finish_thumb(src, dst, Image):
    """Reduz mantendo proporcao (contain) num quadrado THUMB_SIZE sobre fundo escuro."""
    img = Image.open(src).convert("RGB")
    img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
    bg = Image.new("RGB", (THUMB_SIZE, THUMB_SIZE), (24, 24, 24))
    bg.paste(img, ((THUMB_SIZE - img.width) // 2, (THUMB_SIZE - img.height) // 2))
    bg.save(dst)
    src.unlink(missing_ok=True)


# ---------------- main ----------------

def main():
    ap = argparse.ArgumentParser(description="Gera index.json + thumbnails dos sketches.")
    ap.add_argument("--no-thumbs", action="store_true", help="so o index.json (sem renderizar)")
    ap.add_argument("--only", metavar="NOME", help="processar apenas este sketch")
    ap.add_argument("--settle", type=float, default=5.0, help="espera (s) apos o canvas surgir")
    ap.add_argument("--timeout", type=float, default=120.0, help="timeout (s) de navegacao/seletor")
    args = ap.parse_args()

    names = find_sketches()
    if args.only:
        if args.only not in names:
            raise SystemExit(f"sketch '{args.only}' nao encontrado. Disponiveis: {', '.join(names)}")
        names = [args.only]

    entries = [make_entry(n) for n in names]
    print(f"{len(entries)} sketches encontrados.")

    # preserva thumbs ja gerados (ex.: ao usar --only) lendo o index atual
    prev = {}
    if INDEX_JSON.is_file():
        try:
            for e in json.loads(INDEX_JSON.read_text()):
                prev[e["name"]] = e.get("thumb")
        except Exception:
            pass
    for e in entries:
        if prev.get(e["name"]) and (ROOT / prev[e["name"]]).is_file():
            e["thumb"] = prev[e["name"]]

    if not args.no_thumbs:
        httpd, port = start_server()
        print(f"servidor local em http://127.0.0.1:{port}  (renderizando thumbnails...)")
        try:
            capture_thumbnails(entries, port, args.settle, args.timeout)
        finally:
            httpd.shutdown()

    # ao usar --only, mesclar com o index existente para nao perder os demais
    if args.only and INDEX_JSON.is_file():
        try:
            full = json.loads(INDEX_JSON.read_text())
            by_name = {e["name"]: e for e in full}
            for e in entries:
                by_name[e["name"]] = e
            entries = [by_name[n] for n in find_sketches() if n in by_name]
        except Exception:
            pass

    INDEX_JSON.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"escrito {INDEX_JSON.name} ({len(entries)} entradas).")


if __name__ == "__main__":
    main()
