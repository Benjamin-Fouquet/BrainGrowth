import numpy as np
import math
from numba import jit, prange

# Finds the nearest surface nodes to nodes (csn) and distances to them (d2s) - these are needed to set up the growth of the gray matter
@jit
def dist2surf(Ut0, tets, SN, nn, nsn, csn, d2s):
  #csn = np.zeros(nn)  # Nearest surface nodes
  #d2s = np.zeros(nn)  # Distances to nearest surface nodes
  for i in prange(nn):
    d2min = 1e9
    for j in prange(nsn):
      d2 = np.dot(Ut0[SN[j]] - Ut0[i], Ut0[SN[j]] - Ut0[i])
      if d2 < d2min:
        d2min = d2
        p = j
    csn[i] = p
    d2s[i] = np.sqrt(d2min)

  return csn, d2s

# Calculate the relative growth rate
@jit
def growthRate(GROWTH_RELATIVE, t):
  at = GROWTH_RELATIVE*t

  return at

# Calculate the thickness of growing layer
@jit
def cortexThickness(THICKNESS_CORTEX, t):
  H = THICKNESS_CORTEX + 0.01*t

  return H

# Calculate gray and white matter shear modulus (gm and wm) for a tetrahedron, calculate the global shear modulus
@jit
def shearModulus(d2s, H, tets, i, muw, mug, gr):
  gm = 1.0/(1.0 + math.exp(10.0*(0.25*(d2s[tets[i][0]] + d2s[tets[i][1]] + d2s[tets[i][2]] + d2s[tets[i][3]])/H - 1.0)))*0.25*(gr[tets[i][0]] + gr[tets[i][1]] + gr[tets[i][2]] + gr[tets[i][3]])
  wm = 1.0 - gm
  mu = muw*wm + mug*gm  # Global modulus of white matter and gray matter

  return gm, mu

# Calculate relative (relates to d2s) tangential growth factor G
def growthTensor_tangen(Nt, gm, at, G, i):
  G[i] = np.identity(3) + (np.identity(3) - np.matrix([[Nt[0]*Nt[0], Nt[0]*Nt[1], Nt[0]*Nt[2]], [Nt[0]*Nt[1], Nt[1]*Nt[1], Nt[1]*Nt[2]], [Nt[0]*Nt[2], Nt[1]*Nt[2], Nt[2]*Nt[2]]]))*gm*at

  return G[i]

# Calculate homogeneous growth factor G
def growthTensor_homo(G, i, GROWTH_RELATIVE, t):
  G[i] = 1.0 + GROWTH_RELATIVE*t

  return G[i]

# Calculate homogeneous growth factor G (2nd version)
def growthTensor_homo_2(G, i, GROWTH_RELATIVE):
  G[i] = GROWTH_RELATIVE

  return G[i]

# Calculate cortical layer (relates to d2s) homogeneous growth factor G
def growthTensor_relahomo(gm, G, i, GROWTH_RELATIVE, t):
  #G[i] = np.full((3, 3), gm*GROWTH_RELATIVE)
  G[i] = 1.0 + GROWTH_RELATIVE*t*gm

  return G[i]
