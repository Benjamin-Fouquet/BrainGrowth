import numpy as np
import math
from numba import jit

# Find the closest point of triangle abc to point p, if not, p projection through the barycenter inside the triangle
@jit
def closestPointTriangle(p, a, b, c, u, v, w):
  ab = b - a
  ac = c - a
  ap = p - a
  d1 = np.dot(ab, ap)
  d2 = np.dot(ac, ap)
  if d1 <= 0.0 and d2 <= 0.0:
    u = 1.0
    v = 0.0
    w = 0.0
    return a, u, v, w

  bp = p - b
  d3 = np.dot(ab, bp)
  d4 = np.dot(ac, bp)
  if d3 >= 0.0 and d4 <= d3:
    u = 0.0
    v = 1.0
    w = 0.0
    return b, u, v, w

  vc = d1*d4 - d3*d2
  if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
    v = d1 / (d1 - d3)
    u = 1.0 - v
    w = 0.0
    return a + ab * v, u, v, w

  cp = p - c;
  d5 = np.dot(ab,cp);
  d6 = np.dot(ac,cp);
  if d6 >= 0.0 and d5 <= d6:
    u = 0.0
    v = 0.0
    w = 1.0
    return c, u, v, w

  vb = d5*d2 - d1*d6
  if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
    w = d2 / (d2 - d6)
    u = 1.0 - w
    v = 0.0
    return a + ac * w, u, v, w

  va = d3*d6 - d5*d4
  if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
    w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
    u = 0.0
    v = 1.0 - w
    return b + (c - b) * w, u, v, w

  denom = 1.0 / (va + vb + vc)
  v = vb * denom
  w = vc * denom
  u = 1.0 - v - w

  return a + ab * v + ac * w, u, v, w

@jit
def EV(X):
  c1 = X[0,0]*X[1,1] + X[0,0]*X[2,2] + X[1,1]*X[2,2] - X[0,1]*X[0,1] - X[1,2]*X[1,2] - X[0,2]*X[0,2]
  c0 = X[2,2]*X[0,1]*X[0,1] + X[0,0]*X[1,2]*X[1,2] + X[1,1]*X[0,2]*X[0,2] - X[0,0]*X[1,1]*X[2,2] - 2.0*X[0,2]*X[0,1]*X[1,2]
  p = np.trace(X)*np.trace(X) - 3.0*c1
  q = np.trace(X)*(p - 3.0/2.0*c1) - 27.0/2.0*c0

  phi = 27.0 * (0.25*c1*c1*(p-c1) + c0*(q + 27.0/4.0*c0))
  phi = 1.0/3.0 * math.atan2(np.sqrt(math.fabs(phi)), q)
  t = np.sqrt(math.fabs(p)) * math.cos(phi)
  s = 1.0/np.sqrt(3.0) * np.sqrt(math.fabs(p)) * math.sin(phi)

  l3 = 1.0/3.0 * (np.trace(X) - t) - s
  l2 = l3 + 2.0 * s
  l1 = l3 + t + s

  return l1, l2, l3

@jit
def tred2(n, V, d, e):
  """Symmetric Householder reduction to tridiagonal form.

  This is derived from the Algol procedures tred2 by Bowdler, Martin,
  Reinsch, and Wilkinson, Handbook for Auto. Comp., Vol.ii-Linear Algebra,
  and the corresponding Fortran subroutine in EISPACK.
  """
  for j in range(n):
    d[j] = V[n-1][j]

  for i in range(n-1, 0, -1):
    scale = 0.0
    h = 0.0

    for k in range(i):
      scale += abs(d[k])

    if scale == 0.0:
      e[i] = d[i-1]

      for j in range(i):
        d[j] = V[i-1][j]
        V[i][j] = V[j][i] = 0.0

    else:
      for k in range(i):
        d[k] /= scale
        h += d[k]**2

      f = d[i-1]
      g = math.sqrt(h)

      if f > 0.0:
        g = -g

      e[i] = scale*g
      h -= f*g
      d[i-1] = f-g

      for j in range(i):
        e[j] = 0.0

      for j in range(i):
        f = d[j]
        V[j][i] = f
        g = e[j] + V[j][j]*f

        for k in range(j+1, i):
          g += V[k][j]*d[k]
          e[k] += V[k][j]*f

        e[j] = g

      f = 0.0

      for j in range(i):
        e[j] /= h
        f += e[j]*d[j]

      hh = f / (2*h)

      for j in range(i):
        e[j] -= hh*d[j]

      for j in range(i):
        f = d[j]
        g = e[j]

        for k in range(j, i):
          V[k][j] -= f*e[k] + g*d[k]

        d[j] = V[i-1][j]
        V[i][j] = 0.0

    d[i] = h

  for i in range(n-1):
    V[n-1][i] = V[i][i]
    V[i][i] = 1.0
    h = d[i+1]

    if h != 0.0:
      for k in range(i+1):
        d[k] = V[k][i+1] / h

      for j in range(i+1):
        g = 0.0

        for k in range(i+1):
          g += V[k][i+1] * V[k][j]

        for k in range(i+1):
          V[k][j] -= g*d[k]

    for k in range(i+1):
      V[k][i+1] = 0.0

  for j in range(n):
    d[j] = V[n-1][j]
    V[n-1][j] = 0.0

  V[n-1][n-1] = 1.0
  e[0] = 0.0

  return V, d, e

@jit
def hypot(a, b):
  """Computes sqrt(a**2 + b**2) without under/overflow."""
  if abs(a) > abs(b):
    r = b / a
    r = abs(a) * math.sqrt(1 + r*r)
  elif b != 0.0:
    r = a / b
    r = abs(b) * math.sqrt(1 + r*r)

  return r

@jit
def tql2(n, V, d, e):
  """Symmetric tridiagonal QL algorithm.

  This is derived from the Algol procedures tql2, by Bowdler, Martin,
  Reinsch, and Wilkinson, Handbook for Auto. Comp., Vol.ii-Linear Algebra,
  and the corresponding Fortran subroutine in EISPACK.
  """
  for i in range(1, n):
    e[i-1] = e[i]

  e[n-1] = 0.0

  f = 0.0
  tst1 = 0.0
  eps = math.pow(2.0, -52.0)

  for l in range(n):
    tst1 = max(tst1, abs(d[l]) + abs(e[l]))
    m = l

    while m < n:
      if abs(e[m]) <= eps*tst1:
        break
      m += 1

    if m > l:
      iter = 0

      while True:
        iter += 1
        g = d[l]
        p = (d[l+1] - g) / (2.0*e[l])
        r = (p**2 + 1)**0.5
        #r = hypot(p, 1.0)

        if p < 0:
          r = -r

        d[l] = e[l] / (p + r)
        d[l+1] = e[l] * (p + r)
        dl1 = d[l+1]
        h = g - d[l]

        for i in range(l+2, n):
          d[i] -= h

        f += h
        p = d[m]
        c = 1.0
        c2 = c
        c3 = c
        el1 = e[l+1]
        s = 0.0
        s2 = 0.0

        for i in range(m-1, l-1, -1):
          c3 = c2
          c2 = c
          s2 = s
          g = c*e[i]
          h = c*p
          r = (p**2 + e[i]**2)**0.5
          #r = hypot(p, e[i])
          e[i+1] = s*r
          s = e[i] / r
          c = p / r
          p = c*d[i] - s*g
          d[i+1] = h + s*(c*g + s*d[i])

          for k in range(n):
            h = V[k][i+1]
            V[k][i+1] = s*V[k][i] + c*h
            V[k][i] = c*V[k][i] - s*h

        p = -s*s2*c3*el1*e[l] / dl1
        e[l] = s*p
        d[l] = c*p

        if abs(e[l]) <= eps*tst1:
          break

    d[l] = d[l] + f
    e[l] = 0.0

  for i in range(n-1):
    k = i
    p = d[i]

    for j in range(i+1, n):
      if d[j] < p:
        k = j
        p = d[j]

    if k != i:
      d[k] = d[i]
      d[i] = p

      for j in range(n):
        p = V[j][i]
        V[j][i] = V[j][k]
        V[j][k] = p

  return V, d, e

@jit
def eigen_decomposition(n, A, V, d):
  e = [0.0]*n
  for i in range(n):
    for j in range(n):
      V[i][j] = A[i,j]
  V, d, e = tred2(n, V, d, e)
  V, d, e = tql2(n, V, d, e)

  return V, d

@jit
def Eigensystem(n, A, V, d):
  A_ = np.zeros((n,n))
  V_ = np.zeros((n,n))

  A_ = A

  V_, d = eigen_decomposition(n, A_, V_, d)

  V = V_

  return d, V

@jit
def cross(a, b):
  c = np.array([a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]])

  return c


@jit
def det_dim_3(a):
  b = np.zeros(len(a), dtype=np.float64)
  b[:] = a[:,0,0]*a[:,1,1]*a[:,2,2] - a[:,0,0]*a[:,1,2]*a[:,2,1] - a[:,0,1]*a[:,1,0]*a[:,2,2] + a[:,0,1]*a[:,1,2]*a[:,2,0] + a[:,0,2]*a[:,1,0]*a[:,2,1] - a[:,0,2]*a[:,1,1]*a[:,2,0]

  return b

@jit
def det_dim_2(a):
  b = a[0,0]*a[1,1]*a[2,2] - a[0,0]*a[1,2]*a[2,1] - a[0,1]*a[1,0]*a[2,2] + a[0,1]*a[1,2]*a[2,0] + a[0,2]*a[1,0]*a[2,1] - a[0,2]*a[1,1]*a[2,0]

  return b

@jit
def inv(a):

  return np.linalg.inv(a)

@jit
def inv_dim_3(a):

  return np.array([np.linalg.inv(b) for b in a])

@jit
def norm_dim_3(a):
  b = np.zeros(len(a), dtype=np.float64)
  b[:] = np.sqrt(a[:,0]*a[:,0] + a[:,1]*a[:,1] + a[:,2]*a[:,2])

  return b

@jit
def dot_vec(a, b):

  return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]

@jit
def dot_mat_dim_3(a, b):
  c = np.zeros((len(a),3,3), dtype=np.float64)
  c[:,0,0] = a[:,0,0]*b[:,0,0]+a[:,0,1]*b[:,1,0]+a[:,0,2]*b[:,2,0]
  c[:,0,1] = a[:,0,0]*b[:,0,1]+a[:,0,1]*b[:,1,1]+a[:,0,2]*b[:,2,1]
  c[:,0,2] = a[:,0,0]*b[:,0,2]+a[:,0,1]*b[:,1,2]+a[:,0,2]*b[:,2,2]
  c[:,1,0] = a[:,1,0]*b[:,0,0]+a[:,1,1]*b[:,1,0]+a[:,1,2]*b[:,2,0]
  c[:,1,1] = a[:,1,0]*b[:,0,1]+a[:,1,1]*b[:,1,1]+a[:,1,2]*b[:,2,1]
  c[:,1,2] = a[:,1,0]*b[:,0,2]+a[:,1,1]*b[:,1,2]+a[:,1,2]*b[:,2,2]
  c[:,2,0] = a[:,2,0]*b[:,0,0]+a[:,2,1]*b[:,1,0]+a[:,2,2]*b[:,2,0]
  c[:,2,1] = a[:,2,0]*b[:,0,1]+a[:,2,1]*b[:,1,1]+a[:,2,2]*b[:,2,1]
  c[:,2,2] = a[:,2,0]*b[:,0,2]+a[:,2,1]*b[:,1,2]+a[:,2,2]*b[:,2,2]

  return c

@jit
def transpose_dim_3(a):
  b = np.zeros((len(a),3,3), dtype=np.float64)
  b[:,0,0] = a[:,0,0]
  b[:,1,0] = a[:,0,1]
  b[:,2,0] = a[:,0,2]
  b[:,0,1] = a[:,1,0]
  b[:,1,1] = a[:,1,1]
  b[:,2,1] = a[:,1,2]
  b[:,0,2] = a[:,2,0]
  b[:,1,2] = a[:,2,1]
  b[:,2,2] = a[:,2,2]

  return b

@jit
def dot_mat_vec(a, b):

  return np.array([a[0,0]*b[0]+a[0,1]*b[1]+a[0,2]*b[2], a[1,0]*b[0]+a[1,1]*b[1]+a[1,2]*b[2], a[2,0]*b[0]+a[2,1]*b[1]+a[2,2]*b[2]])

def make_2D_array(lis):
  """Funciton to get 2D array from a list of lists"""
  n = len(lis)
  lengths = np.array([len(x) for x in lis])
  max_len = max(lengths)
  arr = np.zeros((n, max_len))

  for i in range(n):
    arr[i, :lengths[i]] = lis[i]
  return arr
