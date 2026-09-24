from ai_edge_litert.interpreter import Interpreter
import cv2, numpy as np
from delogo import delogo
it = Interpreter('seg.tflite'); it.allocate_tensors()
i = it.get_input_details()[0]; o = it.get_output_details()[0]
fr = np.load('frames.npy', mmap_mode='r')
P = []
for k in range(240, 336):
    f = delogo(fr[k])
    x = cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2RGB), (256, 256)).astype(np.float32) / 255
    it.set_tensor(i['index'], x[None]); it.invoke(); y = it.get_tensor(o['index'])[0]
    e = np.exp(y - y.max(2, keepdims=True)); p = e / e.sum(2, keepdims=True)
    P.append((p * 255).astype(np.uint8))
np.save('seg6.npy', np.stack(P))   # 96 x 256 x 256 x 6 (bg, hair, body-skin, face-skin, clothes, other)
