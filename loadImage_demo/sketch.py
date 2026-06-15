def setup():
  createCanvas(windowWidth,windowHeight)
  loadImage('https://esperanc.github.io/Py5Sketches/fourier_filter/baboon.bmp', 
            create_proxy(handleImage))

def handleImage(img):
  image(img, 0, 0)
