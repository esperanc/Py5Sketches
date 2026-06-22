"""
Bumpmap demo with shaders.
"""
def preload():
    global my_shader
    my_shader = loadShader ("vert.glsl", "frag.glsl")
    global img
    img = loadImage("earth.jpg")
    
            
def setup():
    createCanvas(800, 800, WEBGL)
    global bumpSlider, texSlider;
    div = createDiv()
    div.style ("background", 'white')
    div.style ("padding", '0px 12px')
    div.position(10,10)
    bumpP = createP("Bump Scale ")
    bumpP.parent(div)
    bumpSlider = createSlider(0,10,5,1);
    bumpSlider.parent(bumpP);
    texP = createP("Texture blend")
    texP.parent(div)
    texSlider = createSlider(0,1,0.5,0.1)
    texSlider.parent(texP)

def draw():
    background(0)
    pd = pixelDensity()
    my_shader.setUniform("iResolution", js_array([width*pd,height*pd]));
    my_shader.setUniform("iTime", millis()/1000);
    my_shader.setUniform("tex", img)
    my_shader.setUniform("bumpScale", bumpSlider.value())
    my_shader.setUniform("texBlend", texSlider.value())
    shader(my_shader)
    noStroke()
    ortho()
    rotateY(radians(frameCount))
    sphere(300)
