"""
Shape drawing in the fragment shader.
"""
def preload():
    global my_shader
    my_shader = loadShader("vert.glsl", "frag.glsl")
    
def setup():
    createCanvas(800, 800, WEBGL)
    pixelDensity(1)

def draw():
    background(220)
    shader(my_shader)
    noStroke()
    plane(800,800)
