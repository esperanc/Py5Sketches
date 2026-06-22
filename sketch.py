"""
Py5Sketches — galeria/indice de todos os sketches do repositorio.

Le index.json (gerado por build_index.py) e monta uma grade de cards. Cada card
tem thumbnail + titulo (descricao completa no tooltip) e:
  - clicar no card abre o sketch em nova aba (index.html?folder=<nome>);
  - o botao "baixar .zip" monta, NO NAVEGADOR (on-the-fly), um zip com os
    arquivos da pasta do sketch (lista `files` do index.json) para usar na IDE
    do Py5Script — nada de zips pre-gerados no repo.

Esta e a pagina inicial: abrir index.html sem ?folder cai aqui.
"""
import asyncio
import io
import json
import zipfile
import html as _html
import js
from pyodide.ffi import create_proxy, to_js
from pyodide.http import pyfetch

CSS = """
body { margin:0; background:#141414; color:#e8e8e8;
       font-family:-apple-system,"Helvetica Neue",Helvetica,Arial,sans-serif; }
/* cobre a area do runner: a galeria ocupa a janela inteira e rola sozinha */
.galroot { position:fixed; inset:0; overflow-y:auto; background:#141414; z-index:9999; }
.header { padding:18px 22px; position:sticky; top:0; background:#141414;
          border-bottom:1px solid #2a2a2a; z-index:10; }
.header h1 { margin:0 0 4px; font-size:22px; }
.header p  { margin:0; color:#999; font-size:13px; }
.search { margin-top:10px; width:300px; max-width:60vw; padding:7px 10px;
          border-radius:6px; border:1px solid #3a3a3a; background:#1f1f1f;
          color:#eee; font-size:14px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
        gap:16px; padding:22px; }
.card { background:#1d1d1d; border:1px solid #2c2c2c; border-radius:10px;
        overflow:hidden; transition:transform .08s, border-color .08s; }
.card:hover { transform:translateY(-2px); border-color:#5aa77f; }
.open { display:block; text-decoration:none; color:inherit; }
.dl { display:inline-block; margin:2px 12px 12px; padding:5px 11px; font-size:12px;
      background:#26402f; color:#cfeadb; border:1px solid #3a6b4c; border-radius:6px;
      text-decoration:none; cursor:pointer; }
.dl:hover { background:#2f5640; border-color:#5aa77f; }
.thumb { width:100%; aspect-ratio:1/1; object-fit:cover; display:block;
         background:#181818; }
.ph { display:flex; align-items:center; justify-content:center; color:#555;
      font-size:13px; }
.card h3 { margin:10px 12px 4px; font-size:15px; }
h1 a { color: #aaa; }
.name { margin:0 12px 8px; color:#5aa77f; font-size:11px; font-family:monospace; }
.empty { padding:22px; color:#777; }
"""

DL_LABEL = "⬇ baixar .zip"


def preload():
    global index_lines
    index_lines = loadStrings("index.json")


def setup():
    no_canvas()
    create_element("style", CSS)

    global entries, by_name
    entries = json.loads("\n".join(str(s) for s in index_lines))
    by_name = {e["name"]: e for e in entries}

    root = create_div("")
    root.addClass("galroot")

    header = create_div(
        "<h1>Sketches em "
        "<a href='https://github.com/esperanc/Py5Script'>Py5Script</a>"
        " do <a href='https://esperanc.github.io/CompVis2026'>curso de Computação Visual</a></h1>"
        f"<p>{len(entries)} sketches — clique para abrir (nova aba) "
        "ou baixe o .zip para a IDE</p>")
    header.addClass("header")
    header.parent(root)

    global search
    search = create_input("")
    search.attribute("placeholder", "filtrar por nome ou descricao…")
    search.addClass("search")
    search.parent(header)
    search.input(create_proxy(lambda *a: render(search.value())))

    global grid
    grid = create_div("")
    grid.addClass("grid")
    grid.parent(root)
    # delegacao: um unico listener trata os cliques nos botoes de download
    grid.elt.addEventListener("click", create_proxy(_on_click))

    render("")


def _card(e):
    name = _html.escape(e["name"])
    title = _html.escape(e.get("title") or e["name"])
    desc = _html.escape(e.get("description") or "", quote=True)  # tooltip
    if e.get("thumb"):
        media = f'<img class="thumb" loading="lazy" src="{_html.escape(e["thumb"])}">'
    else:
        media = '<div class="thumb ph">sem preview</div>'
    dl = ""
    if e.get("files"):
        dl = (f'<a class="dl" href="#" data-name="{name}" '
              f'title="baixar .zip para a IDE do Py5Script">{DL_LABEL}</a>')
    return (f'<div class="card">'
            f'<a class="open" href="index.html?folder={name}" target="_blank" '
            f'title="{desc}">{media}<h3>{title}</h3>'
            f'<div class="name">{name}/</div></a>{dl}</div>')


def render(query):
    q = (query or "").lower().strip()
    cards = [_card(e) for e in entries
             if q in (e["name"] + " " + e.get("title", "") + " "
                      + e.get("description", "")).lower()]
    grid.html("".join(cards) if cards else '<p class="empty">nada encontrado</p>')


def _on_click(ev):
    btn = ev.target.closest(".dl")
    if btn is None:
        return
    ev.preventDefault()
    asyncio.ensure_future(_download_zip(btn.getAttribute("data-name"), btn))


async def _download_zip(name, btn):
    e = by_name.get(name)
    if not e:
        return
    btn.textContent = "zipando…"
    try:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in e.get("files", []):
                resp = await pyfetch(f"{name}/{f}")
                if resp.status == 200:
                    z.writestr(f, await resp.bytes())
        _save_blob(f"{name}.zip", buf.getvalue())
    finally:
        btn.textContent = DL_LABEL


def _save_blob(filename, data):
    blob = js.Blob.new(js_array([to_js(data)]), js_object({"type": "application/zip"}))
    url = js.URL.createObjectURL(blob)
    a = js.document.createElement("a")
    a.href = url
    a.download = filename
    js.document.body.appendChild(a)
    a.click()
    a.remove()
    js.URL.revokeObjectURL(url)
