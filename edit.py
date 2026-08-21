import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QPixmap, QImage, QPen, QColor
from PySide6.QtWidgets import QWidget, QScrollArea, QFrame


class FilmStrip(QWidget):

    MAJOR_TICK_EVERY = 10   # 何フレームごとに太い目盛りを引くか

    def __init__(self, source=None):
        super().__init__()
        self.source = source        # BGR numpy 配列（等倍）
        self._pixmap = QPixmap()
        self._cache_key = None
        self.zoom_x = 4.0
        self.smooth = True
        self.pad = 0
        self.slit_width = 1

    def set_source(self, bgr):
        self.source = bgr
        self._cache_key = None
        self.updateGeometry()
        self.update()

    def set_slit_width(self, slit_width: int):
        w = max(1, slit_width)
        if self.slit_width != w:
            self.slit_width = w
            self.update()

    def set_pad(self, pad: int):
        if self.pad != pad:
            self.pad = pad
            self._cache_key = None
            self.update()

    def set_zoom_x(self, z: float):
        self.zoom_x = max(0.25, min(z, 64.0))
        self._cache_key = None
        self.updateGeometry()
        self.update()

    def set_smooth(self, on: bool):
        self.smooth = on
        self._cache_key = None
        self.update()

    def _rebuild(self, target_h: int):
        h, w = self.source.shape[:2]
        new_w = max(1, int(w * self.zoom_x))

        # 論理ピクセルではなく実ピクセル解像度でリサイズし、HiDPI画面での
        # 二重スケーリングによるブロック状のボケを防ぐ
        dpr = self.devicePixelRatioF()
        phys_w = max(1, round(new_w * dpr))
        phys_h = max(1, round(target_h * dpr))

        if self.smooth:
            interp = cv2.INTER_LANCZOS4 if self.zoom_x > 1.0 else cv2.INTER_AREA
        else:
            interp = cv2.INTER_NEAREST

        resized = cv2.resize(self.source, (phys_w, phys_h),
                             interpolation=interp)
        rgb = np.ascontiguousarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
        hh, ww, ch = rgb.shape
        image = QImage(rgb.data, ww, hh, ch * ww, QImage.Format_RGB888)
        image.setDevicePixelRatio(dpr)
        self._pixmap = QPixmap.fromImage(image)

        self._cache_key = (target_h, self.zoom_x, self.smooth, dpr)
        self.setFixedWidth(new_w + self.pad * 2)

    def paintEvent(self, event):
        if self.source is None or self.height() <= 0:
            return
        key = (self.height(), self.zoom_x, self.smooth, self.devicePixelRatioF())
        if self._cache_key != key:
            self._rebuild(self.height())

        p = QPainter(self)
        p.drawPixmap(self.pad, 0, self._pixmap)
        self._draw_frame_ticks(p, event.rect())

    def _draw_frame_ticks(self, p: QPainter, clip_rect):
        step_px = self.slit_width * self.zoom_x
        if step_px < 3:
            return  # 縮小時は密集しすぎるので目盛りを省略

        first = max(0, int((clip_rect.left() - self.pad) / step_px) - 1)
        last = int((clip_rect.right() - self.pad) / step_px) + 1

        minor_pen = QPen(QColor(255, 255, 255, 60), 1)
        major_pen = QPen(QColor(255, 255, 255, 140), 1)

        for k in range(first, last + 1):
            x = self.pad + k * step_px
            is_major = k % self.MAJOR_TICK_EVERY == 0
            p.setPen(major_pen if is_major else minor_pen)
            p.drawLine(int(x), 0, int(x), self.height())


class _CenterLine(QWidget):
    """ビューポート中央に固定表示する縦線（stripの上に常に重ねて描画）"""

    WIDTH = 3

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(QPen(QColor(0, 0, 0), self.WIDTH))
        cx = self.width() // 2
        p.drawLine(cx, 0, cx, self.height())


class EditPage(QScrollArea):
    time_changed = Signal(float, int)      # 秒, フレーム番号

    def __init__(self, source=None, fps=240.0, slit_width=1):
        super().__init__()
        self.fps = fps or 30.0
        self.slit_width = max(1, slit_width)
        self.start_frame = 0.0

        self.strip = FilmStrip(source)
        self.strip.set_slit_width(self.slit_width)
        self.setWidget(self.strip)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.StrongFocus)

        self.center_line = _CenterLine(self)
        self.center_line.setGeometry(self.viewport().geometry())
        self.center_line.raise_()

        self.horizontalScrollBar().valueChanged.connect(self._emit_time)

    def set_source(self, bgr, fps=None, slit_width=None):
        if fps:
            self.fps = fps
        if slit_width:
            self.slit_width = max(1, slit_width)
        self.strip.set_slit_width(self.slit_width)
        self.strip.set_source(bgr)
        self._emit_time()

    def set_start_here(self):
        self.start_frame = self.center_frame()
        self._emit_time()

    def center_frame(self) -> float:
        if self.strip.source is None:
            return 0.0
        center = self.horizontalScrollBar().value() + self.viewport().width() / 2
        x_src = (center - self.strip.pad) / self.strip.zoom_x
        # 画像は表示順が反転しているため、フレーム番号は右端側から数える
        total_frames = self.strip.source.shape[1] / self.slit_width
        return total_frames - x_src / self.slit_width

    def _emit_time(self):
        f = self.center_frame()
        self.time_changed.emit((f - self.start_frame) / self.fps, int(round(f)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.strip.set_pad(self.viewport().width() // 2)
        self.center_line.setGeometry(self.viewport().geometry())
        self.center_line.raise_()

    def keyPressEvent(self, event):
        steps = 10 if event.modifiers() & Qt.ShiftModifier else 1
        delta = steps * self.slit_width * self.strip.zoom_x
        bar = self.horizontalScrollBar()
        if event.key() == Qt.Key_Left:
            bar.setValue(int(round(bar.value() - delta)))
        elif event.key() == Qt.Key_Right:
            bar.setValue(int(round(bar.value() + delta)))
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        bar = self.horizontalScrollBar()
        if event.modifiers() & Qt.ControlModifier:
            mx = event.position().x()
            anchor = (bar.value() + mx - self.strip.pad) / self.strip.zoom_x
            factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
            self.strip.set_zoom_x(self.strip.zoom_x * factor)
            bar.setValue(int(anchor * self.strip.zoom_x + self.strip.pad - mx))
            event.accept()
        elif event.angleDelta().y():
            bar.setValue(bar.value() - event.angleDelta().y())
            event.accept()
        else:
            super().wheelEvent(event)