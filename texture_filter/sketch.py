"""
Texture filtering demo.
"""
def setup():
    createCanvas(800,800, WEBGL)
    pixelDensity(1)
    global pg
    pg = createGraphics (8,8)
    pg.noStroke()
    for i in range(8):
        for j in range(8):
            pg.fill(0 if (i+j)%2==0 else 255)
            pg.square(i,j,1)
    textureMode(NORMAL)
    texture(pg)
    global tex
    tex = P5._renderer.getTexture(pg)
    tex.setInterpolation(NEAREST,NEAREST)
    global minf, maxf, f_dict
    f_dict = {"NEAREST":NEAREST, "LINEAR":LINEAR}
    minf = createSelect()
    minf.position (10,10)
    maxf = createSelect()
    maxf.position (10,30)
    for key in f_dict.keys():
        minf.option(key)
        maxf.option(key)

def draw():
    background(220)
    orbitControl()
    r,h,n = 200,200,20
    rotateX(-PI/10)
    #rotateY(radians(frameCount/4))
    lights()
    #tex.isDirty = True
    tex.setInterpolation(f_dict[minf.selected()],
         f_dict[maxf.selected()])
    for i in range(8):
        x = P5.map(i,0,7,-200,200)
        for j in range(8):
            z = P5.map(j,0,7, 200,-2000)
            push()
            translate(x,0,z)
            box(50)
            pop()

    