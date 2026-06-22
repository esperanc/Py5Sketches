"""
Simple shader with uniform passing.
"""
def preload():
    global my_shader
    my_shader = loadShader(
        "vert.glsl",
        "frag.glsl")

def setup():
    createCanvas(600, 600, WEBGL)

def draw():
    background(220)
    noStroke()
    shader(my_shader)
    my_shader.setUniform ("t", frameCount/10)
    ellipse (0,0,400,400)
