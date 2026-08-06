import PySide6
from PySide6.QtWidgets import (QWidget, QScrollArea, QFrame, QListWidget, QListWidgetItem)
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter


class FilmStrip(QWidget):
  def __init__(self, images):
    super().__init__()
    self.images = images          # list[QImage]
    self._scaled = []         # 表示用 QPixmap
    self._height = 0

  def set_images(self, images: list):
    self.images = images
    self._height = 0          # 次の paint で作り直させる
    self.updateGeometry()
    self.update()

  def _rebuild(self, h: int):
    """ビューポート高さに合わせて全フレームをスケールし直す"""
    self._scaled = [
        QPixmap.fromImage(img).scaledToHeight(h, Qt.SmoothTransformation)
        for img in self.images
    ]
    self._height = h
    total = sum(p.width() for p in self._scaled)
    self.setFixedWidth(total)      # スクロール範囲がこれで決まる

  def paintEvent(self, event):
    if not self.images:
        return
    if self.height() != self._height:
        self._rebuild(self.height())

    p = QPainter(self)
    x = 0
    clip = event.rect()            # 再描画が必要な範囲
    for pm in self._scaled:
      if x + pm.width() >= clip.left() and x <= clip.right():
        p.drawPixmap(x, 0, pm)     # 表示範囲のものだけ描く
      x += pm.width()


class EditPage(QScrollArea):

  def __init__(self, qimages):
    super().__init__()
    self.qimages = qimages
    self.strip = FilmStrip(self.qimages)
    self.strip.set_images(self.qimages)
    self.setWidget(self.strip)
    self.setWidgetResizable(True)      # 高さをビューポートに追従させる
    self.setFrameShape(QFrame.NoFrame)
    self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

  def set_qimages(self, qimages):
    self.qimages = qimages
    self.strip.set_images(qimages)


  def wheelEvent(self, event):
    d = event.angleDelta().y()
    if d:
      bar = self.horizontalScrollBar()
      bar.setValue(bar.value() - d)
      event.accept()
    else:
      super().wheelEvent(event)