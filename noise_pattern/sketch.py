"""
 Several interesting noise / pattern shaders collected
 from https://thebookofshaders.com and https://shadertoy.com
 Credits for each shader are given in each .glsl file.
"""

from gui import GuiBlock

def preload():
    global shaderDict 
    shaderDict = {
        "simplex":loadShader("vert.glsl", "simplex.glsl"),
        "worley":loadShader("vert.glsl", "worley.glsl"),
        "crack":loadShader("vert.glsl", "crackmarble.glsl"),
        "fbm":loadShader("vert.glsl", "fbm.glsl"),
        "warp":loadShader("vert.glsl", "warp.glsl"),
        "voronoi":loadShader("vert.glsl", "voronoi.glsl"),
        "truchet":loadShader("vert.glsl", "truchet.glsl")
    }

def setup():
    createCanvas(800, 800, WEBGL)
    pixelDensity(1)
    global guiSel
    guiSel = GuiBlock("")
    guiSel.addSelect("shader", shaderDict.keys(), "simplex")
    

def draw():
    background(0)
    my_shader =  shaderDict[guiSel.data["shader"]]
    my_shader.setUniform("iResolution", js_array([width,height]));
    my_shader.setUniform("iTime", millis()/1000);
    shader(my_shader)
    noStroke()
    plane(800,800)
