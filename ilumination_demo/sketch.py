"""
Demo Phong illumination model.
"""
from gui import GuiBlock

def setup():
    createCanvas(800,800,WEBGL)
    initLightsGui()
    initMaterialGui()
    guiSel = GuiBlock("")
    guiSel.addSelect("show", ["ambient light", "point light 1", 
        "point light 2", "material"], "material")
    guiSel.position(400,10)
    def changeShow():
        sel = guiSel.data["show"]
        for gui in (pl1,pl2,mat,al): gui.div.style("display","none")
        if sel=="ambient light":
            al.div.style("display","block")
        elif sel=="point light 1":
            pl1.div.style("display","block")
        elif sel=="point light 2":
            pl2.div.style("display","block")
        else:
            mat.div.style("display","block")
    changeShow()
    guiSel.change(changeShow)

def initLightsGui():
    global pl1, pl2, al
    pl1 = gui = GuiBlock("Point Light 1")
    gui.addNumber("x",-1000,1000,200)
    gui.addNumber("y",-1000,1000,-200)
    gui.addNumber("z",-1000,1000,200)
    gui.addColor("color","red")
    gui.addCheckbox("enable",True)
    pl2 = gui = GuiBlock("Point Light 2")
    gui.addNumber("x",-1000,1000,-200)
    gui.addNumber("y",-1000,1000,-200)
    gui.addNumber("z",-1000,1000,200)
    gui.addColor("color","blue")
    gui.addCheckbox("enable",True)
    al = gui = GuiBlock("Ambient Light")
    gui.addColor("color", "#222222")

def initMaterialGui():
    global mat
    mat = gui = GuiBlock("Material")
    mat.addColor ("fill", "#ffffff")
    mat.addColor ("ambient", "#ffffff")
    mat.addColor ("specular", "#ffffff")
    mat.addNumber("shininess", 1,100,20)
    
def draw():
    background(220)
    noStroke()
    for gui in (pl1,pl2):
        if gui.data["enable"]:
            pt = [gui.data[coord] for coord in "xyz"]
            pointLight(color(gui.data["color"]),*pt)
    fill(mat.data["fill"])
    ambientLight(color(al.data["color"]))
    ambientMaterial(color(mat.data["ambient"]))
    specularMaterial(color(mat.data["specular"]))
    shininess(mat.data["shininess"])
    sphere(300)
    
