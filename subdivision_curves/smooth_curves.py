# 
#  Four point subdivision (Dyn-Levin-Gregory)
# 
def four_point (points, closed = False, w = 0.06):
    n = len(points)
    def next(i):
        if closed: return  (i + 1) % n
        else: return min(n - 1, i + 1)
    def next2(i):
        if closed: return  (i + 2) % n
        else: return min(n - 1, i + 2)
    def prev(i):
        if closed: return  (i + n - 1) % n
        else: return max (0, i - 1)
    v = []
    for i in range(n):
        p = [points[prev(i)], points[i], points[next(i)], points[next2(i)]]
        q = [0, 0]
        for j in [0,1]:
            q[j] = -w * p[0][j] + (0.5 + w) * p[1][j] + (0.5 + w) * p[2][j] - w * p[3][j]
        v.append(points[i])
        v.append(q)
    if not closed: v.pop()
    return v
    
# 
#  Lane Riesenfeld subdivision step
# 
def lr(points, closed = False, degree = 2):
    # duplicate
    v = []
    if not closed:
        for i in range(1,degree):
            v.append(points[0])
    for p in points:
        v.append(p)
        v.append(p)
    n = len(v)
    def next (i):
        if closed: return  (i + 1) % n
        else: return min (n - 1, i + 1)
  
    # average
    for d in range(1, degree+1):
        u = []
        for i in range(n):
            p = v[i]
            q = v[next(i)]
            u.append([(p[0] + q[0]) / 2, (p[1] + q[1]) / 2])
        v = u
    return v
    