class Frame:
    def __init__(self, origin, u, v):
        """
        Initializes the coordinate frame.
        """
        self.origin_x = origin.x
        self.origin_y = origin.y
        
        # The Basis Matrix M transforms Frame -> World
        # M = | u.x  v.x |
        #     | u.y  v.y |
        self.m00 = u.x
        self.m01 = v.x
        self.m10 = u.y
        self.m11 = v.y

        # Calculate Determinant: ad - bc
        det = (self.m00 * self.m11) - (self.m01 * self.m10)
        
        if abs(det) < 1e-9:
            raise ValueError("Basis vectors are collinear or zero; determinant is zero.")

        # Calculate Inverse Matrix M_inv transforms World -> Frame
        # M_inv = (1/det) * |  v.y  -v.x |
        #                   | -u.y   u.x |
        inv_det = 1.0 / det
        self.inv00 =  self.m11 * inv_det
        self.inv01 = -self.m01 * inv_det
        self.inv10 = -self.m10 * inv_det
        self.inv11 =  self.m00 * inv_det

    def to_world_vector(self, vec):
        """
        Converts a vector from Frame Space to World Space.
        Formula: V_world = Matrix * V_local
        """
        # Matrix multiplication row 1: ax + by
        wx = (self.m00 * vec.x) + (self.m01 * vec.y)
        # Matrix multiplication row 2: cx + dy
        wy = (self.m10 * vec.x) + (self.m11 * vec.y)
        return createVector(wx, wy)

    def to_frame_vector(self, vec):
        """
        Converts a vector from World Space to Frame Space.
        Formula: V_local = InverseMatrix * V_world
        """
        lx = (self.inv00 * vec.x) + (self.inv01 * vec.y)
        ly = (self.inv10 * vec.x) + (self.inv11 * vec.y)
        return createVector(lx, ly)

    def to_world_point(self, pt):
        """
        Converts a point from Frame Space to World Space.
        Formula: P_world = (Matrix * P_local) + Origin
        """
        # 1. Rotate/Scale (Matrix multiply)
        wx = (self.m00 * pt.x) + (self.m01 * pt.y)
        wy = (self.m10 * pt.x) + (self.m11 * pt.y)
        
        # 2. Translate (Add Origin)
        wx += self.origin_x
        wy += self.origin_y
        
        return createVector(wx, wy)

    def to_frame_point(self, pt):
        """
        Converts a point from World Space to Frame Space.
        Formula: P_local = InverseMatrix * (P_world - Origin)
        """
        # 1. Translate (Subtract Origin)
        dx = pt.x - self.origin_x
        dy = pt.y - self.origin_y
        
        # 2. Rotate/Scale (Inverse Matrix multiply)
        lx = (self.inv00 * dx) + (self.inv01 * dy)
        ly = (self.inv10 * dx) + (self.inv11 * dy)
        
        return createVector(lx, ly)
