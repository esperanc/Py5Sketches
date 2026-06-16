"""
Py5Sketches — galeria/indice de todos os sketches do repositorio.

Le index.json (gerado por build_index.py) e monta uma grade de cards clicaveis,
cada um com thumbnail + docstring do sketch. Clicar abre o sketch em nova aba
(index.html?folder=<nome>). Esta e a pagina inicial: abrir index.html sem
?folder cai aqui.
"""
import json
import html as _html
from pyodide.ffi import create_proxy

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
.card { display:block; text-decoration:none; color:inherit; background:#1d1d1d;
        border:1px solid #2c2c2c; border-radius:10px; overflow:hidden;
        transition:transform .08s, border-color .08s; }
.card:hover { transform:translateY(-2px); border-color:#5aa77f; }
.thumb { width:100%; aspect-ratio:1/1; object-fit:cover; display:block;
         background:#181818; }
.ph { display:flex; align-items:center; justify-content:center; color:#555;
      font-size:13px; }
.card h3 { margin:10px 12px 4px; font-size:15px; }
.name { margin:0 12px; color:#5aa77f; font-size:11px; font-family:monospace; }
.desc { margin:6px 12px 12px; color:#a9a9a9; font-size:12px; line-height:1.4;
        white-space:pre-wrap; max-height:8.4em; overflow:hidden;
        -webkit-mask-image:linear-gradient(#000 75%, transparent); }
.empty { padding:22px; color:#777; }
"""


def preload():
    global index_lines
    index_lines = loadStrings("index.json")


def setup():
    no_canvas()
    create_element("style", CSS)

    global entries
    entries = json.loads("\n".join(str(s) for s in index_lines))

    root = create_div("")
    root.addClass("galroot")

    header = create_div(
        "<h1>Py5Sketches</h1>"
        f"<p>{len(entries)} sketches — clique para abrir (nova aba)</p>")
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

    render("")


def _card(e):
    name = _html.escape(e["name"])
    title = _html.escape(e.get("title") or e["name"])
    desc = _html.escape(e.get("description") or "")
    if e.get("thumb"):
        media = f'<img class="thumb" loading="lazy" src="{_html.escape(e["thumb"])}">'
    else:
        media = '<div class="thumb ph">sem preview</div>'
    return (f'<a class="card" href="index.html?folder={name}" target="_blank">'
            f'{media}<h3>{title}</h3><div class="name">{name}/</div>'
            f'<div class="desc">{desc}</div></a>')


def render(query):
    q = (query or "").lower().strip()
    cards = [_card(e) for e in entries
             if q in (e["name"] + " " + e.get("title", "") + " "
                      + e.get("description", "")).lower()]
    grid.html("".join(cards) if cards else '<p class="empty">nada encontrado</p>')
