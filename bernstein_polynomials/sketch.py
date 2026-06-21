"""
Plots Bernstein Polynomials for any given degree.
"""

from line_chart import LineChart
from math import comb, pow
from gui import GuiBlock

chart = None
w,h = 680,430

def bernstein(n,k,t):
    return comb(n,k)*pow(t,k)*pow(1-t,n-k)
    
def setup():
    global s_factor
    s_factor = min(windowWidth/w,windowHeight/h)
    create_canvas(s_factor*w, s_factor*h)
    create_chart(3)
    global gui
    gui = GuiBlock()
    gui.addNumber("n",1,6,3,1)
    gui.change(lambda: create_chart(gui.n))

def create_chart(n):
    global chart
    chart = LineChart(x=0, y=0, w=w, h=h)

    chart.set_title("Bernstein Polynomials")
    chart.set_x_label("t")
    chart.set_y_label("b(t)")
    chart.set_x_ticks(7)
    chart.set_y_ticks(6)
    
    for k in range(0,n+1):
        pts = [
            createVector(x/50, bernstein(n,k,x / 50))
            for x in range(51)
        ]
        chart.add_series(pts, label=f"b({n},{k})")

    chart.set_show_grid(True)
    chart.set_show_points(False)   # too many points — skip dots
    chart.set_stroke_weight(3)

def draw():
    background(245)
    scale (s_factor)
    chart.draw()