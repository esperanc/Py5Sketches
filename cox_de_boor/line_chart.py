# line_chart.py — A reusable line chart class for the Py5Script environment.
#
# Usage:
#   from line_chart import LineChart
#
# The chart maps data expressed as p5.Vector objects (x, y) to canvas
# coordinates automatically.  Multiple series are supported, each rendered
# with its own colour.
#
# Coordinate system note:
#   Py5Script / p5.js uses P5 as the sketch instance and p5 (lowercase) for
#   static classes such as p5.Vector.  Snake_case is auto-converted to
#   camelCase, so both forms work for P5 calls.


class LineChart:
    """A line chart rendered with p5.js primitives inside Py5Script.

    Parameters (all optional — sensible defaults are provided)
    ----------------------------------------------------------
    x, y          : int   Canvas position of the top-left corner of the chart
                          area (including margins).  Defaults to (0, 0).
    w, h          : int   Total width / height of the chart area (including
                          margins).  Defaults to canvas width / height.
    margin_top    : int   Space reserved above the plot for a title.
    margin_right  : int   Space on the right.
    margin_bottom : int   Space below the plot for x-axis labels.
    margin_left   : int   Space to the left for y-axis labels.
    """

    # ------------------------------------------------------------------ #
    # Construction / configuration                                        #
    # ------------------------------------------------------------------ #

    def __init__(self, x=0, y=0, w=None, h=None,
                 margin_top=40, margin_right=30,
                 margin_bottom=50, margin_left=60):

        # Chart origin and outer dimensions (resolved lazily if None)
        self._x = x
        self._y = y
        self._w = w          # None → use width  global set by createCanvas
        self._h = h          # None → use height global set by createCanvas

        # Margins between the outer rect and the actual plot area
        self._margin_top    = margin_top
        self._margin_right  = margin_right
        self._margin_bottom = margin_bottom
        self._margin_left   = margin_left

        # Data: list of dicts, one per series
        #   { 'points': [p5.Vector, ...], 'label': str, 'color': (r,g,b) }
        self._series = []

        # Axis configuration
        self._x_ticks    = 5        # desired number of x-axis ticks
        self._y_ticks    = 5        # desired number of y-axis ticks
        self._x_label    = ""       # axis label text
        self._y_label    = ""       # axis label text
        self._title      = ""       # chart title

        # User supplied axis bounds
        self._x_bounds = None
        self._y_bounds = None

        # Visual style
        self._bg_color       = (255, 255, 255)   # plot-area background
        self._axis_color     = (40,  40,  40)    # axes and ticks
        self._grid_color     = (210, 210, 210)   # grid lines
        self._label_size     = 11                # tick label font size (px)
        self._title_size     = 14                # title font size (px)
        self._axis_label_size = 12               # axis-name font size (px)
        self._stroke_weight  = 1.5               # series line weight (px)
        self._point_radius   = 4                 # data-point dot radius (px)
        self._show_grid      = True
        self._show_points    = True
        self._show_legend    = True

        # Default palette (cycles when more series are added)
        self._palette = [
            (31,  119, 180),
            (255, 127,  14),
            (44,  160,  44),
            (214,  39,  40),
            (148, 103, 189),
            (140,  86,  75),
            (227, 119, 194),
            (127, 127, 127),
        ]

    # ------------------------------------------------------------------ #
    # Series management                                                   #
    # ------------------------------------------------------------------ #

    def add_series(self, points, label=None, color=None):
        """Add a data series.

        Parameters
        ----------
        points : list of p5.Vector
            Data points.  Each vector's .x / .y fields are the data values.
        label  : str, optional
            Series name shown in the legend.
        color  : (r, g, b) tuple, optional
            RGB stroke colour.  Cycles through the built-in palette if omitted.
        """
        idx = len(self._series)
        if color is None:
            color = self._palette[idx % len(self._palette)]
        if label is None:
            label = f"Series {idx + 1}"
        self._series.append({'points': list(points),
                             'label':  label,
                             'color':  color})
        return self   # allow chaining

    def clear_series(self):
        """Remove all series."""
        self._series = []
        return self

    def set_series(self, index, points, label=None, color=None):
        """Replace an existing series by index."""
        if index < 0 or index >= len(self._series):
            raise IndexError(f"No series at index {index}")
        existing = self._series[index]
        self._series[index] = {
            'points': list(points),
            'label':  label if label is not None else existing['label'],
            'color':  color if color is not None else existing['color'],
        }
        return self

    # ------------------------------------------------------------------ #
    # Geometry getters / setters                                         #
    # ------------------------------------------------------------------ #

    @property
    def x(self):         return self._x
    @x.setter
    def x(self, v):      self._x = v

    @property
    def y(self):         return self._y
    @y.setter
    def y(self, v):      self._y = v

    @property
    def w(self):         return self._w if self._w is not None else width
    @w.setter
    def w(self, v):      self._w = v

    @property
    def h(self):         return self._h if self._h is not None else height
    @h.setter
    def h(self, v):      self._h = v

    @property
    def margin_top(self):         return self._margin_top
    @margin_top.setter
    def margin_top(self, v):      self._margin_top = v

    @property
    def margin_right(self):       return self._margin_right
    @margin_right.setter
    def margin_right(self, v):    self._margin_right = v

    @property
    def margin_bottom(self):      return self._margin_bottom
    @margin_bottom.setter
    def margin_bottom(self, v):   self._margin_bottom = v

    @property
    def margin_left(self):        return self._margin_left
    @margin_left.setter
    def margin_left(self, v):     self._margin_left = v

    def set_margins(self, top=None, right=None, bottom=None, left=None):
        """Convenience: set one or more margins at once."""
        if top    is not None: self._margin_top    = top
        if right  is not None: self._margin_right  = right
        if bottom is not None: self._margin_bottom = bottom
        if left   is not None: self._margin_left   = left
        return self

    # ------------------------------------------------------------------ #
    # Axis / label setters                                               #
    # ------------------------------------------------------------------ #

    def set_title(self, title):
        self._title = title
        return self

    def set_x_label(self, label):
        self._x_label = label
        return self

    def set_y_label(self, label):
        self._y_label = label
        return self

    def set_x_ticks(self, n):
        self._x_ticks = max(2, int(n))
        return self

    def set_y_ticks(self, n):
        self._y_ticks = max(2, int(n))
        return self
        
    def set_x_bounds(self,xmin,xmax):
        self._x_bounds = (xmin,xmax)
        return self

    def set_y_bounds(self,ymin,ymax):
        self._y_bounds = (ymin,ymax)
        return self

    # ------------------------------------------------------------------ #
    # Style setters                                                      #
    # ------------------------------------------------------------------ #

    def set_show_grid(self, flag):
        self._show_grid = bool(flag)
        return self

    def set_show_points(self, flag):
        self._show_points = bool(flag)
        return self

    def set_show_legend(self, flag):
        self._show_legend = bool(flag)
        return self

    def set_stroke_weight(self, w):
        self._stroke_weight = w
        return self

    def set_point_radius(self, r):
        self._point_radius = r
        return self

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _plot_rect(self):
        """Returns (px, py, pw, ph) — the inner plot rectangle in canvas px."""
        px = self._x + self._margin_left
        py = self._y + self._margin_top
        pw = self.w  - self._margin_left - self._margin_right
        ph = self.h  - self._margin_top  - self._margin_bottom
        return px, py, pw, ph

    def _data_bounds(self):
        """Compute (x_min, x_max, y_min, y_max) across all series."""
        all_pts = [pt for s in self._series for pt in s['points']]
        if not all_pts:
            return 0, 1, 0, 1
        xs = [pt.x for pt in all_pts]
        ys = [pt.y for pt in all_pts]
        x_min, x_max = self._x_bounds if self._x_bounds else (min(xs), max(xs))
        y_min, y_max = self._y_bounds if self._y_bounds else (min(ys), max(ys))
        # Avoid zero-range axes
        if x_min == x_max: x_min, x_max = x_min - 1, x_max + 1
        if y_min == y_max: y_min, y_max = y_min - 1, y_max + 1
        return x_min, x_max, y_min, y_max

    @staticmethod
    def _nice_step(data_range, n_ticks):
        """Return a 'nice' tick step for the given range / count."""
        import math
        raw = data_range / max(n_ticks - 1, 1)
        mag = 10 ** math.floor(math.log10(abs(raw)) if raw != 0 else 0)
        for factor in (1, 2, 2.5, 5, 10):
            step = factor * mag
            if data_range / step <= n_ticks:
                return step
        return raw

    @staticmethod
    def _tick_values(v_min, v_max, n_ticks):
        """Return a list of evenly spaced, nicely rounded tick values."""
        import math
        step  = LineChart._nice_step(v_max - v_min, n_ticks)
        start = math.floor(v_min / step) * step
        ticks = []
        v = start
        while v <= v_max + step * 1e-6:
            if v_min - step * 0.01 <= v <= v_max + step * 0.01:
                ticks.append(round(v, 10))
            v += step
        return ticks

    def _to_canvas(self, data_x, data_y, px, py, pw, ph,
                   x_min, x_max, y_min, y_max):
        """Map a data coordinate to a canvas pixel position."""
        cx = px + (data_x - x_min) / (x_max - x_min) * pw
        cy = py + ph - (data_y - y_min) / (y_max - y_min) * ph
        return cx, cy

    @staticmethod
    def _fmt(v):
        """Format a tick value compactly."""
        if v == int(v):
            return str(int(v))
        # Up to 4 significant decimal digits, strip trailing zeros
        return f"{v:.4g}"

    # ------------------------------------------------------------------ #
    # Drawing                                                            #
    # ------------------------------------------------------------------ #

    def draw(self):
        """Render the chart onto the p5 canvas.  Call inside draw()."""
        px, py, pw, ph = self._plot_rect()
        x_min, x_max, y_min, y_max = self._data_bounds()

        # ── Background ──────────────────────────────────────────────── #
        no_stroke()
        fill(*self._bg_color)
        rect(px, py, pw, ph)

        # ── Grid lines ──────────────────────────────────────────────── #
        if self._show_grid:
            stroke(*self._grid_color)
            stroke_weight(1)

            for tv in self._tick_values(x_min, x_max, self._x_ticks):
                cx, _ = self._to_canvas(tv, y_min, px, py, pw, ph,
                                        x_min, x_max, y_min, y_max)
                line(cx, py, cx, py + ph)

            for tv in self._tick_values(y_min, y_max, self._y_ticks):
                _, cy = self._to_canvas(x_min, tv, px, py, pw, ph,
                                        x_min, x_max, y_min, y_max)
                line(px, cy, px + pw, cy)

        # ── Series (lines + dots) ────────────────────────────────────── #
        for series in self._series:
            pts = series['points']
            if not pts:
                continue
            r, g, b = series['color']

            # Lines
            stroke(r, g, b)
            stroke_weight(self._stroke_weight)
            no_fill()
            beginShape()
            for pt in pts:
                cx, cy = self._to_canvas(pt.x, pt.y, px, py, pw, ph,
                                         x_min, x_max, y_min, y_max)
                vertex(cx, cy)
            endShape()

            # Points
            if self._show_points:
                fill(r, g, b)
                no_stroke()
                for pt in pts:
                    cx, cy = self._to_canvas(pt.x, pt.y, px, py, pw, ph,
                                             x_min, x_max, y_min, y_max)
                    circle(cx, cy, self._point_radius * 2)

        # ── Axes ────────────────────────────────────────────────────── #
        stroke(*self._axis_color)
        stroke_weight(1.5)
        # x-axis
        line(px, py + ph, px + pw, py + ph)
        # y-axis
        line(px, py, px, py + ph)

        # ── X-axis ticks & labels ────────────────────────────────────── #
        text_size(self._label_size)
        text_align(P5.CENTER, P5.TOP)
        fill(*self._axis_color)
        no_stroke()

        for tv in self._tick_values(x_min, x_max, self._x_ticks):
            cx, _ = self._to_canvas(tv, y_min, px, py, pw, ph,
                                    x_min, x_max, y_min, y_max)
            stroke(*self._axis_color)
            stroke_weight(1.5)
            line(cx, py + ph, cx, py + ph + 6)
            no_stroke()
            fill(*self._axis_color)
            text(self._fmt(tv), cx, py + ph + 9)

        # ── Y-axis ticks & labels ────────────────────────────────────── #
        text_align(P5.RIGHT, P5.CENTER)

        for tv in self._tick_values(y_min, y_max, self._y_ticks):
            _, cy = self._to_canvas(x_min, tv, px, py, pw, ph,
                                    x_min, x_max, y_min, y_max)
            stroke(*self._axis_color)
            stroke_weight(1.5)
            line(px - 6, cy, px, cy)
            no_stroke()
            fill(*self._axis_color)
            text(self._fmt(tv), px - 9, cy)

        # ── Axis names ──────────────────────────────────────────────── #
        text_size(self._axis_label_size)
        fill(*self._axis_color)
        no_stroke()

        if self._x_label:
            text_align(P5.CENTER, P5.BOTTOM)
            text(self._x_label, px + pw / 2,
                 self._y + self.h - 4)

        if self._y_label:
            push()
            translate(self._x + self._label_size,
                      py + ph / 2)
            rotate(-P5.HALF_PI)
            text_align(P5.CENTER, P5.TOP)
            text(self._y_label, 0, 0)
            pop()

        # ── Title ────────────────────────────────────────────────────── #
        if self._title:
            text_size(self._title_size)
            text_align(P5.CENTER, P5.TOP)
            fill(*self._axis_color)
            no_stroke()
            text(self._title, px + pw / 2, self._y + 8)

        # ── Legend ───────────────────────────────────────────────────── #
        if self._show_legend and self._series:
            self._draw_legend(px, py, pw)

    def _draw_legend(self, px, py, pw):
        """Draw a legend in the top-right corner of the plot area."""
        box_w  = 12
        pad    = 8
        row_h  = 18
        n      = len(self._series)
        leg_w  = 120
        leg_h  = n * row_h + pad

        lx = px + pw - leg_w - pad
        ly = py + pad

        # Background
        fill(255, 255, 255, 200)
        stroke(*self._axis_color)
        stroke_weight(0.5)
        rect(lx, ly, leg_w, leg_h, 4)

        text_size(self._label_size)
        text_align(P5.LEFT, P5.CENTER)

        for i, series in enumerate(self._series):
            r, g, b = series['color']
            cy = ly + pad / 2 + i * row_h + row_h / 2

            # Colour swatch
            fill(r, g, b)
            no_stroke()
            rect(lx + pad, cy - box_w / 4, box_w, box_w / 2, 2)

            # Label
            fill(*self._axis_color)
            text(series['label'], lx + pad + box_w + 6, cy)