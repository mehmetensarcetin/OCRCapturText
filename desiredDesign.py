from PySide6 import QtWidgets, QtGui, QtCore
import sys

# Subclass QComboBox to make its popup widen to fit contents
class WideComboBox(QtWidgets.QComboBox):
    def showPopup(self):
        fm = self.view().fontMetrics()
        max_width = max(fm.horizontalAdvance(self.itemText(i)) for i in range(self.count())) + 20
        popup_width = max(max_width, self.width())
        self.view().setMinimumWidth(popup_width)
        super().showPopup()

class ScreenshotOverlay(QtWidgets.QWidget):
    screenshot_taken = QtCore.Signal(QtGui.QPixmap)

    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        self.setWindowState(self.windowState() | QtCore.Qt.WindowFullScreen)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.rubber_band = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
        self.origin = QtCore.QPoint()

    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rubber_band.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
        self.rubber_band.show()

    def mouseMoveEvent(self, event):
        self.rubber_band.setGeometry(QtCore.QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        self.rubber_band.hide()
        rect = QtCore.QRect(self.origin, event.pos()).normalized()
        self.hide()  # önce overlay’i gizle ki ekran alındığında kendisi gözükmesin
        QtWidgets.QApplication.processEvents()
        screen = QtGui.QGuiApplication.primaryScreen()
        pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
        self.screenshot_taken.emit(pixmap)
        self.close()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern PySide6 App")
        self.resize(800, 600)

        # Create a toolbar
        self.toolbar = QtWidgets.QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QtCore.QSize(24, 24))
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.toolbar)

        # Connect orientation change to centering logic
        self.toolbar.orientationChanged.connect(self.on_toolbar_orientation_changed)
        # Apply initial alignment
        self.on_toolbar_orientation_changed(self.toolbar.orientation())

        # + Yeni button (distinct style)
        new_btn = QtWidgets.QToolButton()
        new_btn.setText("+ Yeni")
        new_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        new_btn.setCursor(QtCore.Qt.PointingHandCursor)
        new_btn.setStyleSheet(
            "QToolButton { background-color: #2E8B57; color: white; border-radius: 4px; }"
            "QToolButton:hover { background-color: #3CB371; }"
        )
        new_btn.setFixedSize(75, 30)
        self.toolbar.addWidget(new_btn)
        self.toolbar.addSeparator()

        # OCR dili dropdown
        ocr_label = QtWidgets.QLabel("OCR Dili:")
        ocr_label.setFixedHeight(30)
        self.toolbar.addWidget(ocr_label)
        self.ocr_combo = WideComboBox()
        self.ocr_combo.addItems(["Türkçe", "İngilizce", "Almanca", "Fransızca"])
        self.ocr_combo.setFixedSize(45, 30)
        self.toolbar.addWidget(self.ocr_combo)
        self.toolbar.addSeparator()

        # Gecikme(sn) dropdown
        delay_label = QtWidgets.QLabel("Gecikme (sn):")
        delay_label.setFixedHeight(30)
        self.toolbar.addWidget(delay_label)
        self.delay_combo = WideComboBox()
        self.delay_combo.addItems(["0", "3", "5", "10"])
        self.delay_combo.setFixedSize(45, 30)
        self.toolbar.addWidget(self.delay_combo)
        self.toolbar.addSeparator()

        # Yazı and Resim buttons (same design)
        for text in ["Yazı", "Resim"]:
            btn = QtWidgets.QToolButton()
            btn.setText(text)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QToolButton { background-color: #f0f0f0; color: #333; border: 1px solid #ccc; border-radius: 4px; }"
                "QToolButton:hover { background-color: #e0e0e0; }"
            )
            btn.setFixedSize(60, 30)
            self.toolbar.addWidget(btn)
            self.toolbar.addSeparator()

        # Right alignment spacer
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        # "..." menu button without arrow
        menu_btn = QtWidgets.QToolButton()
        menu_btn.setText("...")
        menu_btn.setCursor(QtCore.Qt.PointingHandCursor)
        menu_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        menu_btn.setFixedSize(30, 30)
        menu = QtWidgets.QMenu(menu_btn)
        menu.addAction("Ayarlar")
        menu.addSeparator()
        menu.addAction("Info")
        menu_btn.clicked.connect(lambda: menu.exec(menu_btn.mapToGlobal(QtCore.QPoint(0, menu_btn.height()))))
        self.toolbar.addWidget(menu_btn)

        # Central image display label
        self.image_label = QtWidgets.QLabel("Ana içerik burada.")
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.setCentralWidget(self.image_label)

        # connect screenshot
        new_btn.clicked.connect(self.start_screenshot)

    def on_toolbar_orientation_changed(self, orientation):
        # When vertical, center items horizontally; otherwise left-align
        if orientation == QtCore.Qt.Vertical:
            self.toolbar.layout().setAlignment(QtCore.Qt.AlignHCenter)
        else:
            self.toolbar.layout().setAlignment(QtCore.Qt.AlignLeft)

    def start_screenshot(self):
        # optional delay
        delay = int(self.delay_combo.currentText())
        if delay > 0:
            QtCore.QTimer.singleShot(delay*1000, self._show_overlay)
        else:
            self._show_overlay()

    def _show_overlay(self):
        self.overlay = ScreenshotOverlay()
        self.overlay.screenshot_taken.connect(self.on_screenshot)
        self.overlay.show()

    def on_screenshot(self, pixmap: QtGui.QPixmap):
        # display in central label
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        ))

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())