"""
Cross-fading demo using textures and shaders.
"""
def preload():
    global my_shader
    my_shader = loadShader ("vert.glsl", "frag.glsl")
    global img1, img2
    img1 = loadImage("icon (29).png")
    img2 = loadImage("nongrid (74).png")
            
def setup():
    createCanvas(800, 800, WEBGL)

def draw():
    background(0)
    pd = pixelDensity()
    my_shader.setUniform("iResolution", js_array([width*pd,height*pd]));
    my_shader.setUniform("iTime", millis()/1000);
    my_shader.setUniform("tex1", img1)
    my_shader.setUniform("tex2", img2)
    shader(my_shader)
    noStroke()
    plane(800,800)
