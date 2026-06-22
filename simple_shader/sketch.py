"""
Minimal shader example in p5
"""
def preload():
    global my_shader
    my_shader = loadShader(
        "vertex_shader.glsl",
        "frag_shader.glsl")

def setup():
    createCanvas(600, 600, WEBGL)

def draw():
    background(220)
    noStroke()
    shader(my_shader)
    ellipse (0,0,400,400)
