"""
Bare bones raymarching with no illumination.
"""
def preload():
    global my_shader
    my_shader = loadShader(
        "vertex_shader.glsl",
        "frag_shader.glsl")

def setup():
    createCanvas(windowWidth, windowHeight, WEBGL)

def draw():
    background(220)
    noStroke()
    shader(my_shader)
    pd = pixelDensity()
    my_shader.setUniform("iResolution", 
       js_array([width*pd,height*pd]));
    my_shader.setUniform("iTime", millis()/1000);
    plane(width,height)
