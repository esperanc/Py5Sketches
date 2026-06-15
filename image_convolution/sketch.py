"""
Demonstrates the application of 3x3 convolution kernels on assorted images.
Disclaimer: All images were downloaded from 
https://www.hlevkin.com/hlevkin/TestImages/
"""
from gui import GuiBlock
import math

kernels = {
    "identity": [0, 0, 0, 0, 1, 0, 0, 0, 0],
    "blur":[1, 1, 1, 1, 1, 1, 1, 1, 1],
    "gaussian_blur": [1, 2, 1, 2, 4, 2, 1, 2, 1],
    "sharpen": [0, -1, 0, -1, 5, -1, 0, -1, 0],
    "sharpen_diag": [-1, -1, -1, -1, 9, -1, -1, -1, -1],
    "edge" : [-1, -1, -1, -1, 8, -1, -1, -1, -1],
    "sobel_h": [-1, 0, 1, -2, 0, 2, -1, 0, 1],
    "sobel_v": [-1, -2, -1, 0, 0, 0, 1, 2, 1]
}

image_dict = {
    "airfield2.bmp": None,
    "baboon.bmp": None,
    "boats.bmp" : None,
    "cameraman.bmp": None,
    "finger.bmp": None,
    "flower.bmp" : None,
    "girl.bmp" : None,
    "houses.bmp" : None, 
    "pens.bmp" : None,
    "lenna.bmp" : None,
    "lighthouse.bmp" : None,
    "pepper.bmp": None,
}

# How the convolution treats color. Maps the GUI label to the shader's u_mode.
color_modes = {
    "rgb": 0,             # convolve each channel independently (uniform)
    "luminance": 1,       # convolve only luminance, output grayscale
    "luminance_color": 2  # convolve luminance, keep the pixel's original color
}

def preload():
    global my_shader
    my_shader = loadShader("vert.glsl", "frag.glsl")
    # global img
    # img = {}
    # for name in image_names:
    #     img[name] = load_image(name)

def setup():
    createCanvas(windowWidth, windowHeight, WEBGL)
    pixelDensity(1)
    
    global gui
    gui = GuiBlock()
    gui.addSelect("kernel", kernels.keys(), "identity")
    gui.addSelect("image", image_dict.keys(), "cameraman.bmp")
    gui.addSelect("mode", color_modes.keys(), "rgb")
    gui.change(update_kernel)
    
    global kernel_display
    kernel_div = create_div()
    kernel_div.position (width-130,10)
    kernel_div.style("background", "gray")
    kernel_div.style("font", GuiBlock.font)
    kernel_div.style("padding", "10px")
    kernel_div.style("width", "100px")
    kernel_div.style("max-width", "100px")
    kernel_display = []
    callback = create_proxy(lambda el: apply_convolution())
    for i in range(9):
        k = str(kernels["identity"][i])
        kd = create_input(k)
        kd.size(25)
        kd.style("display",'inline-block')
        kd.parent(kernel_div)
        kd.input(callback)
        kernel_display.append(kd)
        if i%3==2: 
            br = createElement("br")
            br.parent(kernel_div)
    
    global fb
    fb = None

    apply_convolution()
    
def handle_image(img):
    image_dict [gui.image] = img
    print ("loaded", gui.image)
    apply_convolution()

def handle_fail(event):
    print ("failed: ")
    print (event)
  
load_callback = create_proxy(handle_image)
fail_callback = create_proxy(handle_fail)

def apply_convolution():
    src = image_dict [gui.image]
    # Load image on demand
    if src is None:
        #url = 'https://esperanc.github.io/Py5Sketches/image_convolution/'+gui.image
        url = './'+gui.image
        loadImage(url, load_callback, fail_callback)
        return
        
    # Decode the convolution kernel
    try:
        kernel=[]
        for kd in kernel_display:
            num = int(kd.value())
            if math.isnan(num): return
            kernel.append(num)
    except Exception as e:
        print (e)
        return
    
    # Adapt the frame buffer to the image source
    global fb
    if fb == None or fb.width != src.width or fb.height != fb.height:
        if fb != None: fb.remove()
        fb = create_framebuffer(js_object(
            {"width": src.width,
             "height": src.height,
             "density": 1}))
    
    # Apply the kernel
    fb.begin()
    clear()
    shader(my_shader)
    my_shader.setUniform('u_texture', src)
    my_shader.setUniform('u_kernel', kernel)
    weight = max(1,sum(kernel))
    my_shader.setUniform('u_weight', weight)
    my_shader.setUniform('u_mode', color_modes[gui.mode])
    no_stroke()
    plane(src.width,src.height)
    fb.end()
    reset_shader()

def update_kernel():
    kernel = kernels[gui.kernel]
    for i,k in enumerate(kernel):
        kernel_display[i].value(k)
    apply_convolution()

def draw():
    background(240)
    if not fb: return
    sfactor = min(width/fb.width,height/fb.height)*0.9
    scale(sfactor)
    image(fb,-fb.width/2,-fb.height/2)
    
