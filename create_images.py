import cv2
import numpy as np

class CreateImages:

  def __init__(self, src, outdir, max_frame, slit_width=1, slit_x=None, y_top=0.30, y_bottom=0.95):
    self.src = src
    self.outdir = outdir
    self.max_frame = max_frame
    self.slit_width = slit_width
    self.slit_x = slit_x
    self.y_top = y_top
    self.y_bottom = y_bottom


  def run(self):
    cap = cv2.VideoCapture(self.src)
    columns = []

    ok, prev_frame = cap.read()

    i = 0
    while ok:
      if self.max_frame and self.max_frame < i:
        break

      ok_next, next_frame = cap.read()

      fh, fw = prev_frame.shape[:2]
      y0 = int(fh * self.y_top)
      y1 = int(fh * self.y_bottom)
      x = fw // 2 if self.slit_x is None else self.slit_x

      prev_slit = prev_frame[y0:y1, x:x + self.slit_width].astype(np.float32)
      next_slit = next_frame[y0:y1, x:x + self.slit_width].astype(np.float32) if ok_next else prev_slit

      # フレーム間を線形補間し、slit_width>1のときの階段状ジャギーを滑らかにする
      alpha = np.linspace(0, 1, self.slit_width, dtype=np.float32).reshape(1, -1, 1)
      blended = (prev_slit * (1 - alpha) + next_slit * alpha).astype(np.uint8)
      columns.append(blended)

      prev_frame = next_frame
      ok = ok_next
      i += 1

    cap.release()
    if not columns:
        return None

    stitched = np.hstack(columns)                       # 横に連結
    stitched = stitched[:, ::-1]                        # 表示順序を反転（新しいフレームを左に）
    return np.ascontiguousarray(stitched)