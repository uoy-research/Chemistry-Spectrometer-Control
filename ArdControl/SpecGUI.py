import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLineEdit, QTextEdit
from PyQt6.QtCore import Qt
import serial
from arduinoController import ArduinoController

defaultPort = "4"


class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.readings = []
        self.valveStates = []
        self.init = True

        self.setWindowTitle("Spec Control")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self)

        self.manual_button = QPushButton("Start Manual Mode")
        self.manual_button.clicked.connect(self.buttonCMD)
        self.layout.addWidget(self.manual_button)

        self.auto_button = QPushButton("Start Auto Mode")
        self.auto_button.clicked.connect(self.buttonCMD)
        self.layout.addWidget(self.auto_button)

        self.ttl_button = QPushButton("Start TTL Mode")
        self.ttl_button.clicked.connect(self.buttonCMD)
        self.layout.addWidget(self.ttl_button)

        self.port_field = QLineEdit(defaultPort)
        self.layout.addWidget(self.port_field)

        self.console_window = QTextEdit()
        self.console_window.setReadOnly(True)
        self.console_window.setPlainText(
            "Here is where info will show but is there text wrapping?\n" * 10)
        self.layout.addWidget(self.console_window)

    def buttonCMD(self):
        print("Button clicked!")


def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
