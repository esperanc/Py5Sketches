"""
Plots B-Spline base functions with adjustable degree and knots.
"""
from line_chart import LineChart
from gui import GuiBlock

chart = None
w,h = 600,600

def cox_de_boor(i, d, t, knots):

    def recurse(i, d):
        if d == 0: 
            return 1.0 if knots[i] <= t < knots[i+1] else 0.0
        
        # Calculate denominators to handle potential division by zero
        # (Standard B-spline convention: 0 / 0 = 0)
        denom1 = knots[i+d] - knots[i]
        denom2 = knots[i+d+1] - knots[i+1]
        
        term1 = 0.0
        if denom1 != 0:
            term1 = ((t - knots[i]) / denom1) * recurse(i, d-1)
            
        term2 = 0.0
        if denom2 != 0:
            term2 = ((knots[i+d+1] - t) / denom2) * recurse(i+1, d-1)
            
        return term1 + term2

    return recurse(i, d)

def setup():
    global s_factor
    s_factor = min(windowWidth/w,windowHeight/h)
    create_canvas(s_factor*w, s_factor*h)
    global gui
    GuiBlock.labelWidth = "7em"
    gui = GuiBlock()
    gui.addNumber("d",0,6,3,1)
    gui.addNumber("functions",1,6,3,1)
    gui.addText("knots", "0,1,2,3,4,5")
    gui.change(lambda: create_chart(gui.d,gui.functions,gui.knots))
    create_chart(gui.d,gui.functions,gui.knots)

def create_chart(d,m,knots_str):
    try:
        knots = list(map(lambda s:float(s), knots_str.split(",")))
    except Exception:
        return
    # Pad the knot vector.
    while len(knots)<m+d+1:
        increment = knots[-1]-knots[-2] if len(knots)>1 else 1
        knots.append(knots[-1]+increment)

    global chart
    chart = LineChart(x=0, y=0, w=w, h=h)

    chart.set_title("B-Spline blending functions")
    chart.set_x_label("t")
    chart.set_y_label("B(t)")
    chart.set_x_ticks(7)
    chart.set_y_ticks(6)
    
    tmax = knots[m+d]
    for i in range(0,m):
        pts = []
        for j in range(101):
            # Avoid evaluating the last point of the last interval.
            t = j/100.001*tmax
            pts.append(createVector(t, cox_de_boor(i,d,t,knots)))
        chart.add_series(pts, label=f"b({i},{d})")

    chart.set_show_grid(True)
    chart.set_show_points(False)   # too many points — skip dots
    chart.set_y_bounds(0,1)
    chart.set_stroke_weight(3)

def draw():
    background(245)
    scale (s_factor)
    chart.draw()