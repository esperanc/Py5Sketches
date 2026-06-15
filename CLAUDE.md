# Py5Script — Guia para o Claude Code

Este projeto usa **Py5Script**: um ambiente web que combina **p5.js** (JavaScript) com **Python via PyScript/Pyodide**. Leia este arquivo inteiro antes de escrever qualquer código.

---

## Estrutura do projeto (modo standalone)

```
projeto/
├── index.html        # Cópia de runner.html do Py5Script (não editar)
├── sketch.py         # Entry point principal — sempre presente
├── requirements.txt  # Pacotes Python opcionais (numpy, pandas, etc.)
├── js_modules.txt    # Bibliotecas JS externas opcionais
└── *.py              # Módulos auxiliares importáveis
```

Para rodar: `python3 -m http.server 8000` e abrir `localhost:8000`.

---

## Como o ambiente funciona

- O sketch é executado em **PyScript/Pyodide** dentro do browser.
- O p5.js roda em **instance mode**; a instância se chama `P5` (maiúsculo).
- O objeto estático global é `p5` (minúsculo), usado para `p5.Vector`, `p5.TWO_PI`, etc.
- **AST auto-prefixing**: chamadas como `rect(10, 10, 50, 50)` são automaticamente convertidas para `P5.rect(10, 10, 50, 50)`. Você pode escrever sem o prefixo `P5.` na maioria dos casos.
- **snake_case** é suportado: `create_canvas(400, 400)` → `P5.createCanvas(400, 400)`.

---

## Estrutura básica de um sketch

```python
def setup():
    create_canvas(800, 600)
    background(30)

def draw():
    fill(255)
    circle(mouse_x, mouse_y, 40)

def mouse_pressed():
    background(30)
```

Funções de ciclo de vida reconhecidas automaticamente: `setup`, `draw`, `mouse_pressed`, `mouse_released`, `mouse_moved`, `mouse_dragged`, `key_pressed`, `key_released`, `window_resized`, etc.

---

## Regras críticas de interoperabilidade Python ↔ JavaScript

### 1. Funções que NÃO são auto-prefixadas (conflito com Python)

Use sempre `P5.` explicitamente nestas:

| Função p5 | Por quê |
|-----------|---------|
| `P5.random(...)` | Conflita com o módulo `random` do Python |
| `P5.map(v, a, b, c, d)` | Conflita com `map()` built-in do Python |
| `P5.min(...)` / `P5.max(...)` | Conflitam com built-ins do Python |
| `P5.set(...)` | Conflita com `set()` built-in do Python |

### 2. Listas Python → Arrays JavaScript

Python lists **não** são convertidas automaticamente. Use os helpers globais:

```python
# ERRADO — pode falhar silenciosamente
shader.set_uniform('color', [1.0, 0.5, 0.0])

# CORRETO
shader.set_uniform('color', js_array([1.0, 0.5, 0.0]))
```

Helpers disponíveis globalmente (sem import):

| Helper | Uso |
|--------|-----|
| `js_array(lista)` | Python list/tuple → JS Array |
| `js_object(dicionario)` | Python dict → JS object |
| `to_js(valor)` | Conversor Pyodide genérico |
| `create_proxy(fn)` | Mantém callback Python vivo no escopo JS |

### 3. NumPy — evite proxies temporários

```python
# ERRADO — proxy destruído antes de p5 usar o valor
for row in my_numpy_array:
    vertex(row[0], row[1])

# CORRETO — converta para tipos nativos Python
for x, y in my_numpy_array.tolist():
    vertex(x, y)
```

### 4. Callbacks DOM

```python
def on_change(event):
    global valor
    valor = slider.value()

def setup():
    global slider
    slider = create_slider(0, 255, 128)
    slider.input(create_proxy(on_change))  # create_proxy é obrigatório!
```

---

## Assets e arquivos

- **Imagens/dados**: faça upload via IDE ou coloque no diretório do projeto.
- `P5.load_image("img.png")` — funciona diretamente.
- `open("data.txt")` — funciona no modo IDE (virtual FS). No modo standalone, prefira `P5.load_strings()` ou `pyodide.http.pyfetch`.
- **Shaders**: crie arquivos `.vert` e `.frag` e carregue com `P5.load_shader("s.vert", "s.frag")`.

---

## Dependências externas

### Python (requirements.txt)
```
numpy
pandas
```

### JavaScript ESM (js_modules.txt)
```
# alias usado no Python como nome do módulo
https://cdn.jsdelivr.net/npm/lil-gui@0.21/+esm = lil
```

Uso no Python:
```python
gui = lil.GUI.new()
```

---

## Padrões e boas práticas

- Declare variáveis globais com `global` dentro de `setup()` e `draw()`.
- Prefira `P5.random()` a `random.random()` para valores visuais.
- Para embaralhar listas Python, use `random.shuffle(lista)` em vez de `P5.shuffle()`.
- Para vetores, use `p5.Vector.add(v1, v2)` (instância estática).
- Ao usar shaders com uniforms numéricos, sempre converta: `shader.set_uniform('val', float(x))`.

---

## O que NÃO fazer

- ❌ Não usar `localStorage` ou APIs de browser diretamente no sketch Python.
- ❌ Não passar numpy scalars diretamente a funções p5 que armazenam valores (ex: `vertex()`).
- ❌ Não assumir que listas Python chegam como arrays JS automaticamente.
- ❌ Não criar callbacks DOM sem `create_proxy()`.
- ❌ Não usar `map()`, `random()`, `min()`, `max()`, `set()` sem `P5.` quando quiser a versão p5.

---

## Referências

- Repositório: https://github.com/esperanc/Py5Script
- IDE online: https://esperanc.github.io/Py5Script/
- Referência p5.js: https://p5js.org/reference/
- PyScript docs: https://docs.pyscript.net/
