import cv2,numpy as np
X0,Y0,X1,Y1=560,1110,640,1210
A=np.load('logo_alpha.npy')
core=(A>0.14).astype(np.uint8)
ring=(cv2.dilate(core,np.ones((5,5),np.uint8))-cv2.erode(core,np.ones((3,3),np.uint8)))
A3=A[...,None]
def delogo(f):
  f=f.copy();r=f[Y0:Y1,X0:X1].astype(np.float32)
  c=np.clip((r-A3*255)/(1-A3),0,255).astype(np.uint8)
  c=cv2.inpaint(c,ring,3,cv2.INPAINT_TELEA)
  f[Y0:Y1,X0:X1]=c
  return f
