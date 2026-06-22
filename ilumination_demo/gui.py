class GuiBlock:
    labelWidth = "5em"
    font = '15px "Helvetica Neue", Helvetica, Arial, sans-serif'
    def __init__(self,label=""):
        self.label = label
        self.div = createDiv(label)
        if label!="":
            br = createElement("br")
            br.parent(self.div)
        self.div.style("background", "lightgray")
        self.div.style("font", GuiBlock.font)
        self.div.style("padding", "10px")
        self.y = 5 if label=="" else 10
        self.data = {}
        self.elems = {}
        self.position(10,10)
        self.changeFunc = None
        
    def change(self,func):
        self.changeFunc = func
        
    def position(self,x=0,y=0):
        return self.div.position(x,y)
        
    def _addElement (self,name,element,valueFun=lambda el:el.value(),display=True):
        self.data[name]=valueFun(element)
        #sp = "&nbsp;"*(10-len(name))
        self.elems[name+"label"]=label=createSpan(name)
        label.style("min-width",GuiBlock.labelWidth)
        label.style("display",'inline-block')
        label.parent(self.div)
        self.elems[name]=element
        element.parent(self.div)
        if display:
            self.elems[name+"disp"]=disp=createSpan(f" {valueFun(element)}")
            disp.parent(self.div)
        def update(el):
            self.data[name]=valueFun(element)
            if display: disp.html(valueFun(element))
            if self.changeFunc:
                self.changeFunc()
        callback=create_proxy(update)
        element.elt.oninput = callback
        element.changed(callback)
        br = createElement("br")
        br.parent(self.div)
        
    def addColor(self,name,value="#ffffff"):
        picker=createColorPicker(value)
        self._addElement(name,picker)
       
        
    def addText(self,name,value=""):
        input=createInput(value)
        self._addElement(name,input,display=False)

    def addCheckbox(self,name,value=False):
        cb=createElement("input")
        cb.attribute("type","checkbox")
        if value: cb.elt.checked = True
        valueFun = lambda el: el.elt.checked
        self._addElement(name,cb,display=False,valueFun=valueFun)
        
        
    def addNumber(self,name,min=0,max=100,value=0,step=1):
        slider=createSlider(min,max,value,step)
        self._addElement(name,slider)
        
    def addSelect(self,name,options,value):
        sel = createSelect()
        for option in options: sel.option(option)
        sel.selected(value)
        valueFun = lambda el: el.selected()
        self._addElement(name,sel,display=False,valueFun=valueFun)