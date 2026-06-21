#!/usr/bin/env python3
"""
Gera o indice da galeria de sketches Py5Script.

Varre as subpastas do repo que contem `sketch.py`, extrai o docstring de modulo
de cada uma e (opcionalmente) renderiza um thumbnail 800x800 do canvas usando
Chromium headless (Playwright). Produz:

  - index.json          : [{name, title, description, thumb, files}, ...]
  - thumbs/<nome>.png   : miniatura 400x400 de cada sketch

A galeria (sketch.py na raiz) usa a lista `files` para montar o zip de cada
sketch on-the-fly (no navegador) quando o usuario clica em baixar.

Uso:
  python3 build_index.py                 # tudo; thumbnails so de pastas alteradas
  python3 build_index.py --new-only      # so as pastas ainda ausentes do index.json
  python3 build_index.py --force-thumbs  # recaptura todos os thumbnails
  python3 build_index.py --no-thumbs     # so o index.json (rapido)
  python3 build_index.py --only fourier  # regerar um sketch
  python3 build_index.py --settle 8 --timeout 120

Por default, um thumbnail so e recapturado se estiver ausente ou mais antigo que
algum arquivo da pasta do sketch.

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
SKIP_FILES = {".DS_Store"}  # arquivos ignorados na listagem da pasta


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
    doc = doc.strip() if doc else ""
    # titulo = primeiro paragrafo (todas as linhas ate a primeira linha em branco)
    title_lines = []
    for ln in doc.splitlines():
        if not ln.strip():
            break
        title_lines.append(ln.strip())
    title = " ".join(title_lines) if title_lines else name
    return {"name": name, "title": title, "description": doc, "thumb": None}


def uses_numpy(name):
    req = ROOT / name / "requirements.txt"
    return req.is_file() and "numpy" in req.read_text(errors="replace").lower()


def list_files(name):
    """Nomes dos arquivos da pasta do sketch (a galeria zipa on-the-fly)."""
    folder = ROOT / name
    return sorted(p.name for p in folder.iterdir()
                  if p.is_file() and p.name not in SKIP_FILES and p.suffix != ".zip")


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

# Forca o canvas WEBGL a ser opaco (alpha:false). Sem isso, no Chromium headless
# as regioes do canvas com alpha<1 (fundo dos sketches 3D) compoem com o fundo
# branco da pagina e aparecem como um retangulo branco no thumbnail.
_OPAQUE_WEBGL_JS = """
  const orig = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, a){
    if(type==='webgl'||type==='webgl2'||type==='experimental-webgl'){
      a = Object.assign({}, a||{}, {alpha:false});
    }
    return orig.call(this, type, a);
  };
"""


def thumb_is_fresh(name):
    """True se o thumbnail existe e e mais recente que todos os arquivos da pasta."""
    t = THUMBS_DIR / f"{name}.png"
    if not t.is_file():
        return False
    tmt = t.stat().st_mtime
    folder = ROOT / name
    for p in folder.iterdir():
        if p.is_file() and p.name not in SKIP_FILES and p.suffix != ".zip":
            if p.stat().st_mtime > tmt:
                return False
    return True


def capture_thumbnails(entries, port, settle, timeout, force=False):
    from playwright.sync_api import sync_playwright
    from PIL import Image

    THUMBS_DIR.mkdir(exist_ok=True)
    tmo = timeout * 1000

    # por default, so (re)captura thumbnails ausentes ou desatualizados
    todo = entries if force else [e for e in entries if not thumb_is_fresh(e["name"])]
    for e in entries:
        if (THUMBS_DIR / f"{e['name']}.png").is_file():
            e["thumb"] = f"thumbs/{e['name']}.png"
    skipped = len(entries) - len(todo)
    if skipped:
        print(f"  {skipped} thumbnail(s) ja atualizados (pulados).")
    if not todo:
        return

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for e in todo:
            name = e["name"]
            page = browser.new_page(viewport={"width": VIEWPORT, "height": VIEWPORT})
            page.add_init_script(_OPAQUE_WEBGL_JS)
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
    ap.add_argument("--new-only", action="store_true",
                    help="processar so as pastas que ainda nao constam de index.json")
    ap.add_argument("--force-thumbs", action="store_true",
                    help="recapturar thumbnails mesmo que ja estejam atualizados "
                         "(default: pula os mais recentes que os arquivos da pasta)")
    ap.add_argument("--settle", type=float, default=5.0, help="espera (s) apos o canvas surgir")
    ap.add_argument("--timeout", type=float, default=120.0, help="timeout (s) de navegacao/seletor")
    args = ap.parse_args()

    # index existente (para preservar entradas nao reprocessadas e detectar pastas novas)
    existing = {}
    if INDEX_JSON.is_file():
        try:
            for e in json.loads(INDEX_JSON.read_text()):
                existing[e["name"]] = e
        except Exception:
            pass

    all_names = find_sketches()
    if args.only:
        if args.only not in all_names:
            raise SystemExit(f"sketch '{args.only}' nao encontrado. Disponiveis: {', '.join(all_names)}")
        names = [args.only]
    elif args.new_only:
        names = [n for n in all_names if n not in existing]
    else:
        names = all_names

    print(f"{len(all_names)} sketches no repo; processando {len(names)}.")

    entries = [make_entry(n) for n in names]
    # lista de arquivos de cada pasta (a galeria gera o zip on-the-fly no clique)
    for e in entries:
        e["files"] = list_files(e["name"])
        tp = f"thumbs/{e['name']}.png"
        if (ROOT / tp).is_file():
            e["thumb"] = tp

    if not args.no_thumbs and entries:
        httpd, port = start_server()
        print(f"servidor local em http://127.0.0.1:{port}  (renderizando thumbnails...)")
        try:
            capture_thumbnails(entries, port, args.settle, args.timeout,
                               force=args.force_thumbs)
        finally:
            httpd.shutdown()

    # mescla: entradas reprocessadas sobrescrevem; as demais ficam como estavam
    merged = dict(existing)
    for e in entries:
        merged[e["name"]] = e
    out = [merged[n] for n in all_names if n in merged]

    INDEX_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"escrito {INDEX_JSON.name} ({len(out)} entradas).")


if __name__ == "__main__":
    main()
