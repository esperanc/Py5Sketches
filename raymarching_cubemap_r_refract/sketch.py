def preload():
    global my_shader
    my_shader = loadShader(
        "vertex_shader.glsl",
        "frag_shader.glsl")
    global cubemapImages
    urls = [
    	'posx.jpg', 'negx.jpg', 
    	'posy.jpg', 'negy.jpg', 
    	'posz.jpg', 'negz.jpg'
    ]
    cubemapImages = [loadImage(url) for url in urls]

def mousePressed():
    global mouseStart 
    mouseStart = mouseX, mouseY
    
def mouseDragged():
    global mouse
    mouse = mouseX, mouseY, *mouseStart
    
def setup():
    createCanvas(windowWidth, windowHeight, WEBGL)
    global mouse 
    mouse = width/2, height/2, 0, 0
    global cubemap
    cubemap = createCubemap()
    
def draw():
    background(220)
    noStroke()
    shader(my_shader)
    pd = pixelDensity()
    my_shader.setUniform("iResolution", 
       js_array([width*pd,height*pd]));
    my_shader.setUniform("iMouse", 
        js_array([x*pd for x in mouse]))
    my_shader.setUniform("iTime", millis()/1000);
   
    # Vincula a textura manualmente ao slot 0
    gl = drawingContext
    gl.activeTexture(gl.TEXTURE0)
    gl.bindTexture(gl.TEXTURE_CUBE_MAP, cubemap)
    
    # p5 não entende cubemaps. Uniforme tem que ser
    # setado manualmente
    uCubemapLoc = gl.getUniformLocation(my_shader._glProgram, 'uCubemap')
    gl.uniform1i(uCubemapLoc, 0)
    
    
    plane(width,height)
    
def createCubemap():
    """ Create cubemap from images """
    gl = drawingContext; 
    tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_CUBE_MAP, tex)
    targets = [
        gl.TEXTURE_CUBE_MAP_POSITIVE_X, gl.TEXTURE_CUBE_MAP_NEGATIVE_X,
        gl.TEXTURE_CUBE_MAP_POSITIVE_Y, gl.TEXTURE_CUBE_MAP_NEGATIVE_Y,
        gl.TEXTURE_CUBE_MAP_POSITIVE_Z, gl.TEXTURE_CUBE_MAP_NEGATIVE_Z
    ]
    for img,target in zip(cubemapImages,targets):
        # the actual image element is in img.canvas
        gl.texImage2D(target, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, 
            img.canvas)
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    return tex
