"""
Simple Raymarching of reflective object with a cubemap as environment.
"""
import js

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
    prefix = "../raymarching_cubemap/"
    cubemapImages = [loadImage(prefix+url) for url in urls]

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
    
    global rblend, rblend_dict
    rblend_dict = { 
        "Reflection only": [1, 0, 0],
        "Illum only": [0, 1, 0],
        "Modulation": [0, 0, 1],
        "Blend": [0.5, 0.5, 0]
    }
    rblend = createSelect()
    for label in rblend_dict: rblend.option(label)
    rblend.position (10,30)
    
    global eye_dist, eye_dir, r, c
    eye_dist = 4
    eye_dir = createVector(0,0,1)
    r = min(width,height)/2 # arcball radius
    c = createVector(width/2,height/2) # arcball center
    
    global cubemap
    cubemap = createCubeMap()
    
def rot_around_axis (v, u, ang):
    """ Returns v rotated by ang around axis u """
    # Rodrigues formula
    # Term 1: v * cos(ang)
    term1 = p5.Vector.mult(v, cos(ang))
    
    # Term 2: (u x v) * sin(ang)
    crossProd = p5.Vector.cross(u, v)
    term2 = p5.Vector.mult(crossProd, sin(ang))
    
    # Term 3: u * (u . v) * (1 - cos(ang))
    dotProd = p5.Vector.dot(u, v)
    term3 = p5.Vector.mult(u, dotProd * (1 - cos(ang)))
    
    # Combine all terms
    return term1.add(term2).add(term3)

def get_rotation (a, b):
    """ Returns the rotation axis and angle that rotates a into b  """
    a = a.copy().normalize()
    b = b.copy().normalize()
    axis = a.cross(b)
    if axis.mag() < 1e-6:
        return createVector(0, 1, 0), 0.0   # no rotation
    return axis.normalize(), abs(a.angleBetween(b))

def mouseWheel(ev):
    """ Zoom in / out """
    global eye_dist 
    if ev.delta < 0 :
        eye_dist *= 9/10
    else:
        eye_dist *= 10/9

def arcball_point():
    """ Arcball point from mouse point """
    p = createVector(mouseX, height-mouseY)
    p.z = max(0, r-p.dist(c))
    return p
    
def mousePressed():
    """ Save start point for drag """
    global saved
    saved = eye_dir, arcball_point()

def get_camera_axes(eye_dir):
    """Returns the right and up vectors of the camera in world space."""
    world_up = createVector(0, 1, 0)
    
    # If eye_dir is nearly parallel to world_up, use a different reference
    if abs(p5.Vector.dot(eye_dir.copy().normalize(), world_up)) > 0.99:
        world_up = createVector(0, 0, 1)
    

    right = world_up.copy().cross(eye_dir).normalize()  
    up    = eye_dir.copy().cross(right).normalize()   
    
    return right, up

def mouseDragged():
    prev_dir, a = saved 
    b = arcball_point()
    
    # Subtract center point
    a_rel = a.copy().sub(c)
    b_rel = b.copy().sub(c)
    
    # Rotation axis in screen space
    u_screen, ang = get_rotation(a_rel, b_rel)
    
    # Rotation axis in world space
    x_world, y_world = get_camera_axes(prev_dir)
    u_world = p5.Vector.mult(x_world,  u_screen.x)
    u_world.add(p5.Vector.mult(y_world,  u_screen.y))
    u_world.add(p5.Vector.mult(prev_dir, u_screen.z))
    u_world.normalize()
    
    # Rotate camera in the opposite direction of the desired
    # object rotation
    global eye_dir
    eye_dir = rot_around_axis(prev_dir, u_world, -ang) 

def eye():
    return eye_dir.copy().mult(eye_dist).array()

def createCubeMap():
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
        gl.bindTexture(gl.TEXTURE_CUBE_MAP, tex)
        # the actual image element is in img.canvas
        gl.texImage2D(target, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img.canvas)
        gl.generateMipmap(gl.TEXTURE_CUBE_MAP);
        
    gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
    return tex

def draw():
    background(220)
    noStroke()

    shader(my_shader)
    pd = pixelDensity()
    my_shader.setUniform("iResolution", 
       js_array([width*pd,height*pd]))
    my_shader.setUniform("iTime", millis()/1000)
    my_shader.setUniform("eye", eye())
    my_shader.setUniform("oper", js_array(op_dict[op.selected()]))
    my_shader.setUniform("rblend", js_array(rblend_dict[rblend.selected()]))
    
    # Vincula a textura manualmente ao slot 0
    gl = drawingContext
    gl.activeTexture(gl.TEXTURE0)
    gl.bindTexture(gl.TEXTURE_CUBE_MAP, cubemap)
    
    # p5 não entende cubemaps. Uniforme tem que ser
    # setado manualmente
    uCubemapLoc = gl.getUniformLocation(my_shader._glProgram, 'uCubemap')
    gl.uniform1i(uCubemapLoc, 0)
    
    plane(width,height)
