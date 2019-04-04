import numpy as np
import math
from numba import jit, njit, prange
from mathfunc import det_dim_3, det_dim_2, cross_dim_3, dot_mat_dim_3, transpose_dim_3

# Import mesh, each line as a list
def importMesh(path):
  mesh = []
  with open(path) as inputfile:
    for line in inputfile:
      mesh.append(line.strip().split(' '))
    for i in range(len(mesh)):
      mesh[i] = list(filter(None, mesh[i]))
      mesh[i] = np.array([float(a) for a in mesh[i]])

  return mesh

# Read nodes, get undeformed coordinates x y z and save them in Ut0, initialize deformed coordinates Ut
@njit(parallel=True)
def vertex(mesh):
  nn = np.int64(mesh[0][0])
  Ut0 = np.zeros((nn,3), dtype=np.float64) # Undeformed coordinates of nodes
  #Ut = np.zeros((nn,3), dtype = float) # Deformed coordinates of nodes
  for i in prange(nn):
    Ut0[i] = np.array([float(mesh[i+1][1]),float(mesh[i+1][0]),float(mesh[i+1][2])]) # Change x, y (Netgen?)
    
  Ut = Ut0 # Initialize deformed coordinates of nodes
  
  return Ut0, Ut, nn

# Read element indices (tets: index of four vertices of tetrahedra) and get number of elements (ne)
@njit(parallel=True)
def tetraVerticesIndices(mesh, nn):
  ne = np.int64(mesh[nn+1][0])
  tets = np.zeros((ne,4), dtype=np.int64) # Index of four vertices of tetrahedra
  for i in prange(ne):
    tets[i] = np.array([int(mesh[i+nn+2][1])-1,int(mesh[i+nn+2][2])-1,int(mesh[i+nn+2][4])-1,int(mesh[i+nn+2][3])-1])  # Note the switch of handedness (1,2,3,4 -> 1,2,4,3) - the code uses right handed tets
  
  return tets, ne

# Read surface triangle indices (faces: index of three vertices of triangles) and get number of surface triangles (nf)
@njit(parallel=True)
def triangleIndices(mesh, nn, ne):
  nf = np.int64(mesh[nn+ne+2][0])
  faces = np.zeros((nf,3), dtype=np.int64) # Index of three vertices of triangles
  for i in prange(nf):
    faces[i] = np.array([int(mesh[i+nn+ne+3][1])-1,int(mesh[i+nn+ne+3][2])-1,int(mesh[i+nn+ne+3][3])-1])

  return faces, nf

# Determine surface nodes and index maps
@jit
def numberSurfaceNodes(faces, nn, nf):
  nsn = 0 # Number of nodes at the surface
  SNb = np.zeros(nn, dtype=int) # SNb: Nodal index map from full mesh to surface. Initialization SNb with all 0
  SNb[faces[:,0]] = SNb[faces[:,1]] = SNb[faces[:,2]] = 1
  for i in range(nn):
    if SNb[i] == 1:
      nsn += 1 # Determine surface nodes
  SN = np.zeros(nsn, dtype=int) # SN: Nodal index map from surface to full mesh
  p = 0 # Iterator
  for i in range(nn):
    if SNb[i] == 1:
      SN[p] = i
      SNb[i] = p
      p += 1

  return nsn, SN, SNb

# Return the total volume of a tetrahedral mesh
@jit(nopython=True, parallel=True)
def volume_mesh(Vn_init, nn, ne, tets, Ut):
  A_init = np.zeros((ne,3,3), dtype=np.float64)
  vol_init = np.zeros(ne, dtype=np.float64)

  A_init[:,0] = Ut[tets[:,1]] - Ut[tets[:,0]]
  A_init[:,1] = Ut[tets[:,2]] - Ut[tets[:,0]]
  A_init[:,2] = Ut[tets[:,3]] - Ut[tets[:,0]]
  vol_init[:] = det_dim_3(transpose_dim_3(A_init[:]))/6.0

  for i in range(ne):
    Vn_init[tets[i,0]] += vol_init[i]/4.0
    Vn_init[tets[i,1]] += vol_init[i]/4.0
    Vn_init[tets[i,2]] += vol_init[i]/4.0
    Vn_init[tets[i,3]] += vol_init[i]/4.0

  Vm_init = np.sum(Vn_init)

  return Vm_init

# Mark non-growing areas
@njit(parallel=True)
def markgrowth(Ut0, nn):
  gr = np.zeros(nn, dtype = np.float64)
  for i in prange(nn):
    rqp = np.linalg.norm(np.array([(Ut0[i,0]+0.1)*0.714, Ut0[i,1], Ut0[i,2]-0.05]))
    if rqp < 0.6:
      gr[i] = max(1.0 - 10.0*(0.6-rqp), 0.0)
    else:
      gr[i] = 1.0

  return gr

# Configuration of tetrahedra at reference state (A0)
@jit
def configRefer(Ut0, tets, ne):
  A0 = np.zeros((ne,3,3), dtype=np.float64)
  A0[:,0] = Ut0[tets[:,1]] - Ut0[tets[:,0]] # Reference state
  A0[:,1] = Ut0[tets[:,2]] - Ut0[tets[:,0]]
  A0[:,2] = Ut0[tets[:,3]] - Ut0[tets[:,0]]
  A0[:] = transpose_dim_3(A0[:])

  return A0

# Configuration of a deformed tetrahedron (At)
@jit
def configDeform(Ut, tets, ne):
  At = np.zeros((ne,3,3), dtype=np.float64)
  At[:,0] = Ut[tets[:,1]] - Ut[tets[:,0]]
  At[:,1] = Ut[tets[:,2]] - Ut[tets[:,0]]
  At[:,2] = Ut[tets[:,3]] - Ut[tets[:,0]]
  #At = np.matrix([x1, x2, x3])
  At[:] = transpose_dim_3(At[:])

  return At

# Calculate normals of each surface triangle and apply these normals to surface nodes
@njit(parallel=True)
def normalSurfaces(Ut0, faces, SNb, nf, nsn, N0):
  Ntmp = np.zeros((nf,3), dtype=np.float64)
  Ntmp = cross_dim_3(Ut0[faces[:,1]] - Ut0[faces[:,0]], Ut0[faces[:,2]] - Ut0[faces[:,0]])
  for i in prange(nf):
    N0[SNb[faces[i,0]]] += Ntmp[i]
    N0[SNb[faces[i,1]]] += Ntmp[i]
    N0[SNb[faces[i,2]]] += Ntmp[i]
  for i in prange(nsn):
    N0[i] *= 1.0/np.linalg.norm(N0[i])

  return N0

# Calculate normals of each deformed tetrahedron
@njit(parallel=True)
def tetraNormals(N0, csn, tets, ne):
  Nt = np.zeros((ne,3), dtype=np.float64)
  Nt[:] = N0[csn[tets[:,0]]] + N0[csn[tets[:,1]]] + N0[csn[tets[:,2]]] + N0[csn[tets[:,3]]]
  for i in prange(ne):
    Nt[i] *= 1.0/np.linalg.norm(Nt[i])

  return Nt

# Calculate undeformed (Vn0) and deformed (Vn) nodal volume
# Computes the volume measured at each point of a tetrahedral mesh as the sum of 1/4 of the volume of each of the tetrahedra to which it belongs
@njit(parallel=True)    #(nopython=True, parallel=True)
def volumeNodal(G, A0, tets, Ut, ne, nn):
  Vn0 = np.zeros(nn, dtype=np.float64) #Initialize nodal volumes in reference state
  Vn = np.zeros(nn, dtype=np.float64)  #Initialize deformed nodal volumes
  At = np.zeros((ne,3,3), dtype=np.float64)
  vol0 = np.zeros(ne, dtype=np.float64)
  vol = np.zeros(ne, dtype=np.float64)
  At[:,0] = Ut[tets[:,1]] - Ut[tets[:,0]]
  At[:,1] = Ut[tets[:,2]] - Ut[tets[:,0]]
  At[:,2] = Ut[tets[:,3]] - Ut[tets[:,0]]
  vol0[:] = det_dim_3(dot_mat_dim_3(G[:], A0[:]))/6.0
  vol[:] = det_dim_3(transpose_dim_3(At[:]))/6.0
  for i in prange(ne):
    Vn0[tets[i][0]] += vol0[i]/4.0
    Vn0[tets[i][1]] += vol0[i]/4.0
    Vn0[tets[i][2]] += vol0[i]/4.0
    Vn0[tets[i][3]] += vol0[i]/4.0

    Vn[tets[i][0]] += vol[i]/4.0
    Vn[tets[i][1]] += vol[i]/4.0
    Vn[tets[i][2]] += vol[i]/4.0
    Vn[tets[i][3]] += vol[i]/4.0

  return Vn0, Vn

# Midplane
@njit(parallel=True)
def midPlane(Ut, Ut0, Ft, SN, nsn, mpy, a, hc, K):
  for i in prange(nsn):
    pt = SN[i]
    if Ut0[pt,1] < mpy - 0.5*a and Ut[pt,1] > mpy:
      Ft[pt,1] -= (mpy - Ut[pt,1])/hc*a*a*K
    if Ut0[pt,1] > mpy + 0.5*a and Ut[pt,1] < mpy:
      Ft[pt,1] -= (mpy - Ut[pt,1])/hc*a*a*K

  return Ft

# Calculate the longitudinal length of the real brain
@jit
def longitLength(t):
  L = -0.98153*t**2+3.4214*t+1.9936
  #L = -41.6607*t**2+101.7986*t+58.843 #for the case without normalisation

  return L

# Obtain zoom parameter by checking the longitudinal length of the brain model
@jit
def paraZoom(Ut, SN, L, nsn):
  xmin = ymin = 1.0
  xmax = ymax = -1.0

  xmin = min(Ut[SN[:],0])
  xmax = max(Ut[SN[:],0])
  ymin = min(Ut[SN[:],1])
  ymax = max(Ut[SN[:],1])

  # Zoom parameter
  zoom_pos = L/(xmax-xmin)

  return zoom_pos
