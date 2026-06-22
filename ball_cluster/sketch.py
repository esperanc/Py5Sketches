"""
Ball cluster with OrbitControl.
"""
rand = P5.random

def setup():
    createCanvas(800, 800, WEBGL)
    global geom
    beginGeometry()
    for i in range(100):
        push()
        p = [rand(-200,200) for i in (0,1,2)]
        translate(*p)
        sphere(40)
        pop()
    geom = endGeometry()

def draw():
    background(100)
    orbitControl()
    lights()
    noStroke()
    model(geom)
