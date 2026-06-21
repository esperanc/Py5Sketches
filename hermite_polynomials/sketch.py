"""
Plots Hermite Polynomials.
"""
from line_chart import LineChart
from math import comb, pow

chart = None
w,h = 680,430

hermite = {
    "h00": lambda t: 2*t**3 - 3*t**2 + 1,
    "h10": lambda t: t**3 - 2*t**2 + t,
    "h01": lambda t:-2*t**3 + 3*t**2,
    "h11": lambda t: t**3 -  t**2
    }
    
def setup():
    global s_factor
    s_factor = min(windowWidth/w,windowHeight/h)
    create_canvas(s_factor*w, s_factor*h)
    create_chart()

def create_chart():
    global chart
    chart = LineChart(x=0, y=0, w=w, h=h)

    chart.set_title("Hermite Polynomials")
    chart.set_x_label("t")
    chart.set_y_label("b(t)")
    chart.set_x_ticks(7)
    chart.set_y_ticks(6)
    
    for func in ["h00", "h10", "h01", "h11"]:
        pts = [
            createVector(x/50, hermite[func](x / 50))
            for x in range(51)
        ]
        chart.add_series(pts, label=func)

    chart.set_show_grid(True)
    chart.set_show_points(False)   # too many points — skip dots
    chart.set_stroke_weight(3)

def draw():
    background(245)
    scale (s_factor)
    chart.draw()