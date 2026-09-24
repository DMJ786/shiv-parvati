import cv2,numpy as np
cap=cv2.VideoCapture('source/cafe_original.mp4');fr=[]
while True:
  ok,f=cap.read()
  if not ok:break
  fr.append(f)
fr=np.stack(fr);np.save('frames.npy',fr)
X0,Y0,X1,Y1=560,1110,640,1210
reg=fr[:,Y0:Y1,X0:X1].astype(np.float32)
g=reg.mean(3)
hp=np.stack([r-cv2.GaussianBlur(r,(0,0),8) for r in g[::3]])
m=(np.median(hp,0)>4).astype(np.uint8)
n,lab,st,_=cv2.connectedComponentsWithStats(m)
k=np.argmax(st[1:,4])+1;m=(lab==k).astype(np.uint8)
md=cv2.dilate(m,np.ones((7,7),np.uint8))
# estimate per-pixel alpha
al=[]
for r in reg[::6].astype(np.uint8):
  B=cv2.inpaint(r,md,5,cv2.INPAINT_TELEA).astype(np.float32)
  al.append(((r-B)/(255-B+1e-3)).mean(2))
A=np.clip(np.median(np.stack(al),0),0,0.95)*(md>0)
A=cv2.GaussianBlur(A,(3,3),0)*(md>0)
print('alpha max',A.max(),'mean core',A[m>0].mean())
np.save('logo_alpha.npy',A)
