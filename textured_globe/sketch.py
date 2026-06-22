"""
Demo: Texture coordinates in shaders.
"""
def preload():
    global my_shader
    my_shader = loadShader ("vert.glsl", "frag.glsl")
    global img
    img = loadImage("earth.jpg")
    
            
def setup():
    createCanvas(800, 800, WEBGL)
    textureMode(NORMAL)

def draw():
    background(0)
    pd = pixelDensity()
    my_shader.setUniform("iResolution", js_array([width*pd,height*pd]));
    my_shader.setUniform("iTime", millis()/1000);
    my_shader.setUniform("tex", img)
    shader(my_shader)
    noStroke()
    ortho()
    rotateY(radians(frameCount))
    sphere(300)
