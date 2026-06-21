"""
Ray marching of two shapes with boolean operations.
"""

def preload():
    global my_shader
    my_shader = loadShader(
        "vertex_shader.glsl",
        "frag_shader.glsl")

def mousePressed():
    global mouseStart 
    mouseStart = mouseX, mouseY
    
def mouseDragged():
    global mouse
    mouse = mouseX, mouseY, *mouseStart
    
def setup():
    createCanvas(windowWidth, windowHeight, WEBGL)

    global op, op_dict
    op_dict = { 
        "A ∩ B": [-1, -1, -1],
        "A ∪ B": [1, 1, 1],
        "A \\ B": [-1, 1, -1],
        "B \\ A": [-1, -1, 1]
    }
    op = createSelect()
    for label in op_dict: op.option(label)
    op.position (10,10)

    global mouse 
    mouse = width/2, height/2, 0, 0
    
def draw():
    background(220)
    noStroke()
    shader(my_shader)
    pd = pixelDensity()
    my_shader.setUniform("iResolution", 
       js_array([width*pd,height*pd]));
    my_shader.setUniform("iTime", millis()/1000);
    my_shader.setUniform("iMouse", 
        js_array([x*pd for x in mouse]))
    my_shader.setUniform("oper", 
        js_array(op_dict[op.selected()]))
    plane(width,height)
