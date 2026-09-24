from ai_edge_litert.interpreter import Interpreter
import cv2,numpy as np
from delogo import delogo
it=Interpreter('seg.tflite');it.allocate_tensors()
i=it.get_input_details()[0];o=it.get_output_details()[0]
fr=np.load('frames.npy',mmap_mode='r')
S,E=240,336
out=[];prev=None
for k in range(S,E):
  f=delogo(fr[k])
  x=cv2.resize(cv2.cvtColor(f,cv2.COLOR_BGR2RGB),(256,256)).astype(np.float32)/255
  it.set_tensor(i['index'],x[None]);it.invoke();y=it.get_tensor(o['index'])[0]
  e=np.exp(y-y.max(2,keepdims=True));p=e/e.sum(2,keepdims=True)
  a=1-cv2.resize(p[...,0],(720,1280),interpolation=cv2.INTER_CUBIC)
  a=np.clip((a-0.3)/0.5,0,1)
  if prev is not None:a=0.6*a+0.4*prev
  prev=a
  # fade out lower body / table
  yy=np.linspace(0,1,1280)[:,None]
  a=a*np.clip((1000-np.arange(1280)[:,None])/140,0,1)
  out.append(np.dstack([cv2.cvtColor(f,cv2.COLOR_BGR2RGB),(a*255).astype(np.uint8)]))
np.save('cut.npy',np.stack(out))
