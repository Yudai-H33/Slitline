import cv2
from PySide6.QtGui import QImage

class CreateImages:

  def __init__(self, src, outdir, max_frame):
    self.src = src
    self.outdir = outdir
    self.max_frame = max_frame


  def run(self):
    cap = cv2.VideoCapture(self.src)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    qimages = []
    for i in range(total):
      if self.max_frame < i:
        break
      ok, frame = cap.read()
      if not ok:
        break

      # cv2.imwrite(self.outdir + "/" + "frame_" + str(i) + ".png", frame)
      rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
      h, w, ch = rgb.shape

      qimage = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
      qimages.append(qimage)
      print(str(i) + " frame was created.")
    print("all images created.")
    return qimages