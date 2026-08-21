import PySide6
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QApplication, QLabel, QWidget, QPushButton, QVBoxLayout, QFileDialog, QStackedWidget
)
import os
import sys
from create_images import CreateImages
from edit import EditPage


class SelectPage(QWidget):

    next_requested = Signal(str, object)
    SLIT_WIDTH = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file_path = None
        self.SetupUi()

    def SetupUi(self):
        layout = QVBoxLayout(self)

        self.file_label = QLabel("ファイルが選択されていません")
        layout.addWidget(self.file_label)

        self.select_button = QPushButton("ファイルを選択")
        self.select_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_button)

        self.print_dir_button = QPushButton("画像処理開始")
        self.print_dir_button.setEnabled(False)
        self.print_dir_button.clicked.connect(self.print_file)
        layout.addWidget(self.print_dir_button)


    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "動画ファイルを選択",
            "",
            "動画ファイル (*.mov *.mp4)"
        )
        if file_path:
            self.selected_file_path = file_path
            self.file_label.setText(file_path)
            self.print_dir_button.setEnabled(True)


    def print_file(self):
        if self.selected_file_path:
            filepath = self.selected_file_path
            images = CreateImages(filepath, os.path.dirname(filepath), None, slit_width=self.SLIT_WIDTH)
            self.stitched = images.run()
            self.next_requested.emit(filepath, self.stitched)


# PySide6のアプリ本体（ユーザがコーディングしていく部分）
class MainWindow(QWidget):
    def __init__(self, parent=None):
        # 親クラスの初期化
        super().__init__(parent)

        window_width = 1200
        window_height = 720

        self.resize(window_width, window_height)
        self.setWindowTitle("SlitLine")

        self.SetupUi()

    def SetupUi(self):
        layout = QVBoxLayout(self)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.select = SelectPage()
        self.edit = EditPage(None, slit_width=SelectPage.SLIT_WIDTH)
        self.edit_page = self.build_edit_page()

        for p in (self.select, self.edit_page):
            self.stack.addWidget(p)

        self.select.next_requested.connect(self.goto_edit)

    def build_edit_page(self):
        container = QWidget()
        layout = QVBoxLayout(container)

        controls = QVBoxLayout()
        self.time_label = QLabel("経過時間: -- 秒（フレーム --）")
        controls.addWidget(self.time_label)

        self.set_start_button = QPushButton("この位置をスタートに設定")
        self.set_start_button.clicked.connect(self.edit.set_start_here)
        controls.addWidget(self.set_start_button)

        layout.addLayout(controls)
        layout.addWidget(self.edit)

        self.edit.time_changed.connect(self.update_time_label)

        return container

    def update_time_label(self, seconds, frame):
        self.time_label.setText(f"経過時間: {seconds:.3f} 秒（フレーム {frame}）")

    def goto_edit(self, filepath, bgr):
        self.edit.set_source(bgr)
        self.stack.setCurrentWidget(self.edit_page)


if __name__ == "__main__":
    # 環境変数にPySide6を登録
    dirname = os.path.dirname(PySide6.__file__)
    plugin_path = os.path.join(dirname, 'plugins', 'platforms')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

    app = QApplication(sys.argv)  # PySide6の実行
    window = MainWindow()  # ユーザがコーディングしたクラス
    window.show()  # PySide6のウィンドウを表示
    sys.exit(app.exec())  # PySide6の終了