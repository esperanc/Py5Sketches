"""
Raymarching of objects with rounded corners using smooth min function.
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
    div = createDiv()
    div.style("background", "lightgray")
    div.style("padding", "5px")
    div.position(10,10)
    def stopPropagation(ev):
        ev.stopPropagation()
    jsStop = create_proxy(stopPropagation)
    div.mousePressed(jsStop)
    div.mouseMoved(jsStop)

    op_dict = { 
        "A ∩ B": [-1, -1, -1],
        "A ∪ B": [1, 1, 1],
        "A \\ B": [-1, 1, -1],
        "B \\ A": [-1, -1, 1]
    }
    op = createSelect()
    for label in op_dict: op.option(label)
    op.parent(div)
    
    global smooth_radius
    smooth_div = createDiv("smooth: ")
    smooth_div.parent(div)
    
    smooth_radius = createSlider(0,1,0.05,0.01)
    smooth_radius.parent(smooth_div)

    global smin_radius
    smin_div = createDiv("smin r.: ")
    smin_div.parent(div)
    
    smin_radius = createSlider(0,1,0.05,0.01)
    smin_radius.parent(smin_div)
    
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
    my_shader.setUniform("smooth_radius", smooth_radius.value())
    my_shader.setUniform("smin_radius", smin_radius.value())

    plane(width,height)
