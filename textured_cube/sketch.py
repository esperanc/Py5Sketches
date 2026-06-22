"""
Exemplo de cubo texturado com p5.
"""
def setup():
    createCanvas(800,800, WEBGL)
    global pg
    pg = createGraphics (400,400)
    pg.background('bisque')
    pg.circle(200,200,150)
    global cb_tex, cb_illum
    cb_tex = createCheckbox("texture", True)
    cb_tex.position (10,10)
    cb_illum = createCheckbox("illum", True)
    cb_illum.position(10,30)
    for cb in cb_illum,cb_tex:
        cb.style("width", "100px")
        cb.style("background","white")

def draw():
    background(220)
    if cb_tex.checked():
        texture(pg)
    else: 
        texture(0)
    if cb_illum.checked():
        lights()
    else:
        noLights()
    orbitControl()
    rotateY(radians(frameCount))
    box(400)
