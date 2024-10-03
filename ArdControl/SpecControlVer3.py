from arduinoController import ArduinoController
from motorController import MotorController
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from PyQt6 import QtCore, QtGui, QtWidgets
import sys
import os
import logging
import matplotlib
import time
import threading
import json
matplotlib.use('QtAgg')


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

class Step:
    def __init__(self, step_type, time_length):
        self.step_type = step_type
        self.time_length = time_length

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):

        # Initialise variables
        self.verbosity = True
        self.ardConnected = False
        self.selectedMode = None
        self.connection_in_progress = False
        self.monitoring = False
        self.saving = False
        self.plot_thread = None
        self.default_save_path = os.path.join("C:\\", "NMR Results")
        self.motorConnectd = False
        self.steps = []
        self.controller = None
        self.motorController = None
        self.sequenceLoaded = False
        self.sequenceReady = False
        self.sequenceRunning = False

        # Create the main window
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1259, 680)
        MainWindow.setFixedSize(1259, 680)

        # Create the central widget
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # Create the layout widgets
        self.verticalLayoutWidget = QtWidgets.QWidget(
            parent=self.centralwidget)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(10, 10, 181, 291))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")

        # Create the layout
        self.ardConnectLayout = QtWidgets.QVBoxLayout(
            self.verticalLayoutWidget)
        self.ardConnectLayout.setContentsMargins(0, 0, 0, 0)
        self.ardConnectLayout.setObjectName("ardConnectLayout")

        # Create the COM port label
        self.ardCOMPortLabel = QtWidgets.QLabel(
            parent=self.verticalLayoutWidget)
        self.ardCOMPortLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setPointSize(15)
        self.ardCOMPortLabel.setFont(font)
        self.ardCOMPortLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.ardCOMPortLabel.setObjectName("ardCOMPortLabel")
        self.ardConnectLayout.addWidget(self.ardCOMPortLabel)

        # Create the COM port spin box
        self.ardCOMPortSpinBox = QtWidgets.QSpinBox(
            parent=self.verticalLayoutWidget)
        self.ardCOMPortSpinBox.setMinimumSize(QtCore.QSize(0, 24))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.ardCOMPortSpinBox.setFont(font)
        self.ardCOMPortSpinBox.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.ardCOMPortSpinBox.setObjectName("ardCOMPortSpinBox")
        self.ardConnectLayout.addWidget(self.ardCOMPortSpinBox)

        # Create the warning label
        self.ardWarningLabel = QtWidgets.QLabel(
            parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.ardWarningLabel.setFont(font)
        self.ardWarningLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.ardWarningLabel.setObjectName("ardWarningLabel")
        self.ardConnectLayout.addWidget(self.ardWarningLabel)

        # Create the radio buttons
        self.autoConnectRadioButton = QtWidgets.QRadioButton(
            parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.autoConnectRadioButton.setFont(font)
        self.autoConnectRadioButton.setObjectName("autoConnectRadioButton")
        self.ardConnectLayout.addWidget(
            self.autoConnectRadioButton, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.TTLRadioButton = QtWidgets.QRadioButton(
            parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.TTLRadioButton.setFont(font)
        self.TTLRadioButton.setObjectName("TTLRadioButton")
        self.ardConnectLayout.addWidget(
            self.TTLRadioButton, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.manualRadioButton = QtWidgets.QRadioButton(
            parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.manualRadioButton.setFont(font)
        self.manualRadioButton.setObjectName("manualRadioButton")
        self.ardConnectLayout.addWidget(
            self.manualRadioButton, 0, QtCore.Qt.AlignmentFlag.AlignLeft)

        # Create the button group, this should make radio buttons exclusive
        self.ardConnectButtonGroup = QtWidgets.QButtonGroup(MainWindow)
        self.ardConnectButtonGroup.addButton(self.autoConnectRadioButton)
        self.ardConnectButtonGroup.addButton(self.TTLRadioButton)
        self.ardConnectButtonGroup.addButton(self.manualRadioButton)

        # Create the connect button
        self.ardConnectButton = QtWidgets.QPushButton(
            parent=self.verticalLayoutWidget)
        self.ardConnectButton.setMinimumSize(QtCore.QSize(0, 70))
        font = QtGui.QFont()
        font.setPointSize(18)
        self.ardConnectButton.setFont(font)
        self.ardConnectButton.setObjectName("ardConnectButton")
        self.ardConnectLayout.addWidget(self.ardConnectButton)

        # Create the feedback text box
        self.textBrowser = QtWidgets.QTextBrowser(parent=self.centralwidget)
        self.textBrowser.setGeometry(QtCore.QRect(200, 10, 321, 291))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.textBrowser.setFont(font)
        self.textBrowser.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.textBrowser.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textBrowser.setObjectName("textBrowser")

        # Create a dividing line
        self.line = QtWidgets.QFrame(parent=self.centralwidget)
        self.line.setGeometry(QtCore.QRect(10, 300, 1000, 20))
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")

        # Create the valve layout
        self.gridLayoutWidget = QtWidgets.QWidget(parent=self.centralwidget)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 320, 66, 294))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.valveLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.valveLayout.setContentsMargins(0, 0, 0, 0)
        self.valveLayout.setObjectName("valveLayout")

        # Create the valve buttons
        self.Valve2Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve2Button.setMinimumSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Valve2Button.setFont(font)
        self.Valve2Button.setObjectName("Valve2Button")
        self.valveLayout.addWidget(self.Valve2Button, 3, 0, 1, 1)
        '''
        self.Valve7Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve7Button.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Valve7Button.setFont(font)
        self.Valve7Button.setObjectName("Valve7Button")
        self.valveLayout.addWidget(self.Valve7Button, 5, 0, 1, 1)

        self.Valve6Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve6Button.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Valve6Button.setFont(font)
        self.Valve6Button.setObjectName("Valve6Button")
        self.valveLayout.addWidget(self.Valve6Button, 4, 1, 1, 1)
        '''
        self.Valve1Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve1Button.setMinimumSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Valve1Button.setFont(font)
        self.Valve1Button.setObjectName("Valve1Button")
        self.valveLayout.addWidget(self.Valve1Button, 2, 0, 1, 1)
        self.Valve4Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve4Button.setMinimumSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Valve4Button.setFont(font)
        self.Valve4Button.setObjectName("Valve4Button")
        self.valveLayout.addWidget(self.Valve4Button, 5, 0, 1, 1)
        self.Valve3Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve3Button.setMinimumSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Valve3Button.setFont(font)
        self.Valve3Button.setObjectName("Valve3Button")
        self.valveLayout.addWidget(self.Valve3Button, 4, 0, 1, 1)
        '''
        self.Valve8Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve8Button.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Valve8Button.setFont(font)
        self.Valve8Button.setObjectName("Valve8Button")
        self.valveLayout.addWidget(self.Valve8Button, 5, 1, 1, 1)
        '''
        self.Valve5Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve5Button.setMinimumSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Valve5Button.setFont(font)
        self.Valve5Button.setObjectName("Valve5Button")
        self.valveLayout.addWidget(self.Valve5Button, 6, 0, 1, 1)
        self.Valve1Button.setCheckable(True)
        self.Valve2Button.setCheckable(True)
        self.Valve3Button.setCheckable(True)
        self.Valve4Button.setCheckable(True)
        self.Valve5Button.setCheckable(True)
        # self.Valve6Button.setCheckable(True)
        # self.Valve7Button.setCheckable(True)
        # self.Valve8Button.setCheckable(True)

        # Create the valve label and checkbox
        self.ValveLabel = QtWidgets.QLabel(parent=self.gridLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.ValveLabel.setFont(font)
        self.ValveLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.ValveLabel.setObjectName("ValveLabel")
        self.valveLayout.addWidget(self.ValveLabel, 0, 0, 1, 1)
        self.showValvesCheckbox = QtWidgets.QCheckBox(
            parent=self.gridLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.showValvesCheckbox.setFont(font)
        self.showValvesCheckbox.setTristate(False)
        self.showValvesCheckbox.setObjectName("showValvesCheckbox")
        self.valveLayout.addWidget(
            self.showValvesCheckbox, 7, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)

        self.resetButton = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.resetButton.setMinimumSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.resetButton.setFont(font)
        self.resetButton.setObjectName("resetButton")
        self.valveLayout.addWidget(self.resetButton, 8, 0, 1, 1)

        # Create the motor layout
        self.verticalLayoutWidget_2 = QtWidgets.QWidget(
            parent=self.centralwidget)
        self.verticalLayoutWidget_2.setGeometry(
            QtCore.QRect(530, 10, 201, 291))
        self.verticalLayoutWidget_2.setObjectName("verticalLayoutWidget_2")
        self.motorConnectLayout = QtWidgets.QVBoxLayout(
            self.verticalLayoutWidget_2)
        self.motorConnectLayout.setContentsMargins(0, 0, 0, 0)
        self.motorConnectLayout.setObjectName("motorConnectLayout")

        # Create the motor COM port label
        self.motorCOMPortLabel = QtWidgets.QLabel(
            parent=self.verticalLayoutWidget_2)
        self.motorCOMPortLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setPointSize(15)
        self.motorCOMPortLabel.setFont(font)
        self.motorCOMPortLabel.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter)
        self.motorCOMPortLabel.setObjectName("motorCOMPortLabel")
        self.motorConnectLayout.addWidget(self.motorCOMPortLabel)

        # Create the motor COM port spin box
        self.motorCOMPortSpinBox = QtWidgets.QSpinBox(
            parent=self.verticalLayoutWidget_2)
        self.motorCOMPortSpinBox.setMinimumSize(QtCore.QSize(0, 24))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.motorCOMPortSpinBox.setFont(font)
        self.motorCOMPortSpinBox.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.motorCOMPortSpinBox.setObjectName("motorCOMPortSpinBox")
        self.motorConnectLayout.addWidget(self.motorCOMPortSpinBox)

        # Create the motor warning label
        self.motorWarningLabel = QtWidgets.QLabel(
            parent=self.verticalLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.motorWarningLabel.setFont(font)
        self.motorWarningLabel.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter)
        self.motorWarningLabel.setObjectName("motorWarningLabel")
        self.motorConnectLayout.addWidget(self.motorWarningLabel)

        # Create the motor buttons
        self.motorConnectButton = QtWidgets.QPushButton(
            parent=self.verticalLayoutWidget_2)
        self.motorConnectButton.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.motorConnectButton.setFont(font)
        self.motorConnectButton.setObjectName("motorConnectButton")
        self.motorConnectLayout.addWidget(self.motorConnectButton)
        self.motorCalibrateButton = QtWidgets.QPushButton(
            parent=self.verticalLayoutWidget_2)
        self.motorCalibrateButton.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.motorCalibrateButton.setFont(font)
        self.motorCalibrateButton.setObjectName("motorCalibrateButton")
        self.motorConnectLayout.addWidget(self.motorCalibrateButton)
        self.motorStopButton = QtWidgets.QPushButton(
            parent=self.verticalLayoutWidget_2)
        self.motorStopButton.setMinimumSize(QtCore.QSize(0, 90))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.motorStopButton.setFont(font)
        self.motorStopButton.setObjectName("motorStopButton")
        self.motorConnectLayout.addWidget(self.motorStopButton)

        # Create the monitor layout
        self.gridLayoutWidget_2 = QtWidgets.QWidget(parent=self.centralwidget)
        self.gridLayoutWidget_2.setGeometry(QtCore.QRect(760, 320, 261, 291))
        self.gridLayoutWidget_2.setObjectName("gridLayoutWidget_2")
        self.monitorLayout = QtWidgets.QGridLayout(self.gridLayoutWidget_2)
        self.monitorLayout.setContentsMargins(0, 0, 0, 0)
        self.monitorLayout.setObjectName("monitorLayout")

        '''
        # Create the pressure monitor button
        self.pressureMonitorButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.pressureMonitorButton.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.pressureMonitorButton.setFont(font)
        self.pressureMonitorButton.setObjectName("pressureMonitorButton")
        self.monitorLayout.addWidget(self.pressureMonitorButton, 0, 0, 1, 2)
        '''

        self.quickVentButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.quickVentButton.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.quickVentButton.setFont(font)
        self.quickVentButton.setObjectName("quickVentButton")
        self.monitorLayout.addWidget(self.quickVentButton, 0, 0, 1, 1)

        self.slowVentButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.slowVentButton.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.slowVentButton.setFont(font)
        self.slowVentButton.setObjectName("slowVentButton")
        self.monitorLayout.addWidget(self.slowVentButton, 0, 1, 1, 1)

        self.valveMacro1Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.valveMacro1Button.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.valveMacro1Button.setFont(font)
        self.valveMacro1Button.setObjectName("valveMacro1Button")
        self.monitorLayout.addWidget(self.valveMacro1Button, 1, 0, 1, 1)

        self.valveMacro2Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.valveMacro2Button.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.valveMacro2Button.setFont(font)
        self.valveMacro2Button.setObjectName("valveMacro2Button")
        self.monitorLayout.addWidget(self.valveMacro2Button, 1, 1, 1, 1)

        self.valveMacro3Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.valveMacro3Button.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.valveMacro3Button.setFont(font)
        self.valveMacro3Button.setObjectName("valveMacro3Button")
        self.monitorLayout.addWidget(self.valveMacro3Button, 2, 0, 1, 1)

        self.valveMacro4Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.valveMacro4Button.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.valveMacro4Button.setFont(font)
        self.valveMacro4Button.setObjectName("valveMacro4Button")
        self.monitorLayout.addWidget(self.valveMacro4Button, 2, 1, 1, 1)

        self.valveMacro5Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.valveMacro5Button.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.valveMacro5Button.setFont(font)
        self.valveMacro5Button.setObjectName("valveMacro5Button")
        self.monitorLayout.addWidget(self.valveMacro5Button, 3, 0, 1, 1)

        self.valveMacro6Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.valveMacro6Button.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.valveMacro6Button.setFont(font)
        self.valveMacro6Button.setObjectName("valveMacro6Button")
        self.monitorLayout.addWidget(self.valveMacro6Button, 3, 1, 1, 1)

        # Create the pressure radio buttons
        self.pressure4RadioButton = QtWidgets.QRadioButton(
            parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pressure4RadioButton.setFont(font)
        self.pressure4RadioButton.setObjectName("pressure4RadioButton")
        self.pressure4RadioButton.setAutoExclusive(False)
        self.pressure4RadioButton.setChecked(True)
        self.monitorLayout.addWidget(
            self.pressure4RadioButton, 5, 1, 1, 1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.pressure2RadioButton = QtWidgets.QRadioButton(
            parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pressure2RadioButton.setFont(font)
        self.pressure2RadioButton.setObjectName("pressure2RadioButton")
        self.pressure2RadioButton.setAutoExclusive(False)
        self.pressure2RadioButton.setChecked(True)
        self.monitorLayout.addWidget(
            self.pressure2RadioButton, 4, 1, 1, 1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.pressure1RadioButton = QtWidgets.QRadioButton(
            parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pressure1RadioButton.setFont(font)
        self.pressure1RadioButton.setObjectName("pressure1RadioButton")
        self.pressure1RadioButton.setAutoExclusive(False)
        self.pressure1RadioButton.setChecked(True)
        self.monitorLayout.addWidget(
            self.pressure1RadioButton, 4, 0, 1, 1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.pressure3RadioButton = QtWidgets.QRadioButton(
            parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pressure3RadioButton.setFont(font)
        self.pressure3RadioButton.setObjectName("pressure3RadioButton")
        self.pressure3RadioButton.setAutoExclusive(False)
        self.pressure3RadioButton.setChecked(True)
        self.monitorLayout.addWidget(
            self.pressure3RadioButton, 5, 0, 1, 1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

        # Create the save path buttons
        self.selectSavePathButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.selectSavePathButton.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.selectSavePathButton.setFont(font)
        self.selectSavePathButton.setObjectName("selectSavePathButton")
        self.monitorLayout.addWidget(self.selectSavePathButton, 6, 0, 1, 1)
        self.savePathEdit = QtWidgets.QLineEdit(parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.savePathEdit.setFont(font)
        self.savePathEdit.setObjectName("savePathEdit")
        self.monitorLayout.addWidget(self.savePathEdit, 7, 0, 1, 2)
        self.beginSaveButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.beginSaveButton.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.beginSaveButton.setFont(font)
        self.beginSaveButton.setObjectName("beginSaveButton")
        self.monitorLayout.addWidget(self.beginSaveButton, 6, 1, 1, 1)

        # Create the bubble time widgets
        self.bubbleTimeLabel = QtWidgets.QLabel(parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.bubbleTimeLabel.setFont(font)
        self.bubbleTimeLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight |
                                          QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.bubbleTimeLabel.setObjectName("bubbleTimeLabel")
        self.monitorLayout.addWidget(self.bubbleTimeLabel, 9, 0, 1, 1)
        self.quickBubbleButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.quickBubbleButton.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.quickBubbleButton.setFont(font)
        self.quickBubbleButton.setObjectName("quickBubbleButton")
        self.monitorLayout.addWidget(self.quickBubbleButton, 8, 0, 1, 2)
        self.bubbleTimeDoubleSpinBox = QtWidgets.QDoubleSpinBox(
            parent=self.gridLayoutWidget_2)
        self.bubbleTimeDoubleSpinBox.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.bubbleTimeDoubleSpinBox.setObjectName("bubbleTimeDoubleSpinBox")
        self.bubbleTimeDoubleSpinBox.setMinimum(0.0)
        self.bubbleTimeDoubleSpinBox.setValue(5.00)
        self.monitorLayout.addWidget(self.bubbleTimeDoubleSpinBox, 9, 1, 1, 1)

        # Create the motor position layout
        self.gridLayoutWidget_3 = QtWidgets.QWidget(parent=self.centralwidget)
        self.gridLayoutWidget_3.setGeometry(QtCore.QRect(740, 10, 281, 121))
        self.gridLayoutWidget_3.setObjectName("gridLayoutWidget_3")
        self.motorPosLayout = QtWidgets.QGridLayout(self.gridLayoutWidget_3)
        self.motorPosLayout.setContentsMargins(0, 0, 0, 0)
        self.motorPosLayout.setObjectName("motorPosLayout")

        # Create the motor position widgets
        self.curMotorPosLabel = QtWidgets.QLabel(
            parent=self.gridLayoutWidget_3)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.curMotorPosLabel.setFont(font)
        self.curMotorPosLabel.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.curMotorPosLabel.setObjectName("curMotorPosLabel")
        self.motorPosLayout.addWidget(self.curMotorPosLabel, 0, 0, 1, 1)
        self.targetMotorPosEdit = QtWidgets.QLineEdit(
            parent=self.gridLayoutWidget_3)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.targetMotorPosEdit.sizePolicy().hasHeightForWidth())
        self.targetMotorPosEdit.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.targetMotorPosEdit.setFont(font)
        self.targetMotorPosEdit.setObjectName("targetMotorPosEdit")
        self.motorPosLayout.addWidget(self.targetMotorPosEdit, 1, 1, 1, 1)
        self.curMotorPosEdit = QtWidgets.QLineEdit(
            parent=self.gridLayoutWidget_3)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.curMotorPosEdit.sizePolicy().hasHeightForWidth())
        self.curMotorPosEdit.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.curMotorPosEdit.setFont(font)
        self.curMotorPosEdit.setObjectName("curMotorPosEdit")
        self.motorPosLayout.addWidget(self.curMotorPosEdit, 0, 1, 1, 1)
        self.targetMotorPosLabel = QtWidgets.QLabel(
            parent=self.gridLayoutWidget_3)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.targetMotorPosLabel.setFont(font)
        self.targetMotorPosLabel.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.targetMotorPosLabel.setObjectName("targetMotorPosLabel")
        self.motorPosLayout.addWidget(self.targetMotorPosLabel, 1, 0, 1, 1)
        self.motorMoveToTargetButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_3)
        self.motorMoveToTargetButton.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.motorMoveToTargetButton.setFont(font)
        self.motorMoveToTargetButton.setObjectName("motorMoveToTargetButton")
        self.motorPosLayout.addWidget(self.motorMoveToTargetButton, 2, 0, 1, 2)

        # Create the motor macro layout
        self.gridLayoutWidget_4 = QtWidgets.QWidget(parent=self.centralwidget)
        self.gridLayoutWidget_4.setGeometry(QtCore.QRect(740, 130, 281, 171))
        self.gridLayoutWidget_4.setObjectName("gridLayoutWidget_4")
        self.motorMacroLayout = QtWidgets.QGridLayout(self.gridLayoutWidget_4)
        self.motorMacroLayout.setContentsMargins(0, 0, 0, 0)
        self.motorMacroLayout.setObjectName("motorMacroLayout")

        # Create the motor macro buttons
        self.motorMacro4Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_4)
        self.motorMacro4Button.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.motorMacro4Button.setFont(font)
        self.motorMacro4Button.setObjectName("motorMacro4Button")
        self.motorMacroLayout.addWidget(self.motorMacro4Button, 2, 1, 1, 1)
        self.motorMacro3Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_4)
        self.motorMacro3Button.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.motorMacro3Button.setFont(font)
        self.motorMacro3Button.setObjectName("motorMacro3Button")
        self.motorMacroLayout.addWidget(self.motorMacro3Button, 2, 0, 1, 1)
        self.motorAscentButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_4)
        self.motorAscentButton.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.motorAscentButton.setFont(font)
        self.motorAscentButton.setObjectName("motorAscentButton")
        self.motorMacroLayout.addWidget(self.motorAscentButton, 0, 1, 1, 1)
        self.motorMacro1Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_4)
        self.motorMacro1Button.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.motorMacro1Button.setFont(font)
        self.motorMacro1Button.setObjectName("motorMacro1Button")
        self.motorMacroLayout.addWidget(self.motorMacro1Button, 1, 0, 1, 1)
        self.motorMacro2Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_4)
        self.motorMacro2Button.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.motorMacro2Button.setFont(font)
        self.motorMacro2Button.setObjectName("motorMacro2Button")
        self.motorMacroLayout.addWidget(self.motorMacro2Button, 1, 1, 1, 1)
        self.motorToTopButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_4)
        self.motorToTopButton.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.motorToTopButton.setFont(font)
        self.motorToTopButton.setObjectName("motorToTopButton")
        self.motorMacroLayout.addWidget(self.motorToTopButton, 0, 0, 1, 1)
        self.motorMacro5Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_4)
        self.motorMacro5Button.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.motorMacro5Button.setFont(font)
        self.motorMacro5Button.setObjectName("motorMacro5Button")
        self.motorMacroLayout.addWidget(self.motorMacro5Button, 3, 0, 1, 1)
        self.motorMacro6Button = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_4)
        self.motorMacro6Button.setMinimumSize(QtCore.QSize(0, 35))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.motorMacro6Button.setFont(font)
        self.motorMacro6Button.setObjectName("motorMacro6Button")
        self.motorMacroLayout.addWidget(self.motorMacro6Button, 3, 1, 1, 1)

        # Set the central widget
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menuBar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 1029, 21))
        self.menuBar.setObjectName("menuBar")
        self.motorMacroMenu = QtWidgets.QMenu(parent=self.menuBar)
        self.motorMacroMenu.setObjectName("motorMacroMenu")
        MainWindow.setMenuBar(self.menuBar)
        self.editMotorMacroAction = QtGui.QAction(parent=MainWindow)
        self.editMotorMacroAction.setObjectName("editMotorMacroAction")
        self.motorMacroMenu.addAction(self.editMotorMacroAction)
        self.editValveMacroAction = QtGui.QAction(parent=MainWindow)
        self.editValveMacroAction.setObjectName("editValveMacroAction")
        self.motorMacroMenu.addAction(self.editValveMacroAction)
        self.menuBar.addAction(self.motorMacroMenu.menuAction())

        # Create the graph widgets container
        self.graphContainer = QtWidgets.QWidget(self.centralwidget)
        self.graphContainer.setGeometry(QtCore.QRect(89, 323, 655, 299))
        self.graphContainer.setObjectName("graphContainer")
        self.graphContainer.setStyleSheet(
            "border: 2px Solid LightGray;")  # Add border

        # Create the graph widgets
        self.figure = Figure()
        self.sc = MplCanvas(self, width=5, height=4, dpi=100)
        self.graphWidget = QtWidgets.QWidget(
            parent=self.centralwidget)
        self.graphWidget.setGeometry(QtCore.QRect(91, 325, 651, 294))
        self.graphWidget.setObjectName("graphWidget")
        self.graphLayout = QtWidgets.QVBoxLayout(self.graphWidget)
        self.graphLayout.setContentsMargins(0, 0, 0, 0)
        self.graphLayout.setObjectName("graphLayout")
        self.graphLayout.addWidget(self.sc)

        # Create the toolbar and add it to the layout
        self.toolbar = NavigationToolbar(self.sc, self)
        self.graphLayout.addWidget(self.toolbar)

        # Create a vertical dividing line
        self.line_2 = QtWidgets.QFrame(parent=self.centralwidget)
        self.line_2.setGeometry(QtCore.QRect(1020, 15, 20, 620))
        self.line_2.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_2.setObjectName("line_2")

        # Create sequence layout
        self.sequenceLayoutWidget = QtWidgets.QWidget(parent=self.centralwidget)
        self.sequenceLayoutWidget.setGeometry(QtCore.QRect(1040, 10, 200, 500))
        self.sequenceLayoutWidget.setObjectName("sequenceLayoutWidget")
        self.sequenceLayout = QtWidgets.QGridLayout(self.sequenceLayoutWidget)
        self.sequenceLayout.setContentsMargins(0, 0, 0, 0)
        self.sequenceLayout.setObjectName("sequenceLayout")

        # Create the sequence label
        self.sequenceLabel = QtWidgets.QLabel(parent=self.sequenceLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.sequenceLabel.setFont(font)
        self.sequenceLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.sequenceLayout.addWidget(self.sequenceLabel, 0, 0, 1, 1)

        # Create the sequence controls
        self.sequenceLoadButton = QtWidgets.QPushButton(parent=self.sequenceLayoutWidget)
        self.sequenceLoadButton.setMinimumSize(QtCore.QSize(0, 60))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.sequenceLoadButton.setFont(font)
        self.sequenceLoadButton.setObjectName("sequenceLoadButton")
        self.sequenceLayout.addWidget(self.sequenceLoadButton, 1, 0, 1, 1)

        self.sequenceExecuteButton = QtWidgets.QPushButton(parent=self.sequenceLayoutWidget)
        self.sequenceExecuteButton.setMinimumSize(QtCore.QSize(0, 60))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.sequenceExecuteButton.setFont(font)
        self.sequenceExecuteButton.setObjectName("sequenceExecuteButton")
        self.sequenceLayout.addWidget(self.sequenceExecuteButton, 2, 0, 1, 1)

        self.currentStepTypeLabel = QtWidgets.QLabel(parent=self.sequenceLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.currentStepTypeLabel.setFont(font)
        self.currentStepTypeLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.currentStepTypeLabel.setObjectName("currentStepLabel")
        self.sequenceLayout.addWidget(self.currentStepTypeLabel, 3, 0, 1, 1)

        self.currentStepTypeEdit = QtWidgets.QLineEdit(parent=self.sequenceLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.currentStepTypeEdit.setFont(font)
        self.currentStepTypeEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.currentStepTypeEdit.setObjectName("currentStepTypeEdit")
        self.currentStepTypeEdit.setReadOnly(True)
        self.sequenceLayout.addWidget(self.currentStepTypeEdit, 4, 0, 1, 1)

        self.currentStepTimeLabel = QtWidgets.QLabel(parent=self.sequenceLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.currentStepTimeLabel.setFont(font)
        self.currentStepTimeLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.currentStepTimeLabel.setObjectName("currentStepTimeLabel")
        self.sequenceLayout.addWidget(self.currentStepTimeLabel, 5, 0, 1, 1)

        self.currentStepTimeEdit = QtWidgets.QLineEdit(parent=self.sequenceLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.currentStepTimeEdit.setFont(font)
        self.currentStepTimeEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.currentStepTimeEdit.setObjectName("currentStepTimeEdit")
        self.currentStepTimeEdit.setReadOnly(True)
        self.sequenceLayout.addWidget(self.currentStepTimeEdit, 6, 0, 1, 1)

        self.stepsRemainingLabel = QtWidgets.QLabel(parent=self.sequenceLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.stepsRemainingLabel.setFont(font)
        self.stepsRemainingLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.stepsRemainingLabel.setObjectName("stepsRemainingLabel")
        self.sequenceLayout.addWidget(self.stepsRemainingLabel, 7, 0, 1, 1)

        self.stepsTimeRemainingLabel = QtWidgets.QLabel(parent=self.sequenceLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.stepsTimeRemainingLabel.setFont(font)
        self.stepsTimeRemainingLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.stepsTimeRemainingLabel.setObjectName("stepsTimeRemainingLabel")
        self.sequenceLayout.addWidget(self.stepsTimeRemainingLabel, 8, 0, 1, 1)

        self.sequenceStopButton = QtWidgets.QPushButton(parent=self.sequenceLayoutWidget)
        self.sequenceStopButton.setMinimumSize(QtCore.QSize(0, 60))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.sequenceStopButton.setFont(font)
        self.sequenceStopButton.setObjectName("sequenceStopButton")
        self.sequenceLayout.addWidget(self.sequenceStopButton, 9, 0, 1, 1)


        # Connect the buttons to their slots
        # QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.ardConnectButton.clicked.connect(self.on_ardConnectButton_clicked)
        self.manualRadioButton.clicked.connect(
            self.on_manualRadioButton_clicked)
        self.TTLRadioButton.clicked.connect(self.on_TTLRadioButton_clicked)
        self.autoConnectRadioButton.clicked.connect(
            self.on_autoConnectRadioButton_clicked)
        self.Valve1Button.clicked.connect(self.on_Valve1Button_clicked)
        self.Valve2Button.clicked.connect(self.on_Valve2Button_clicked)
        self.Valve3Button.clicked.connect(self.on_Valve3Button_clicked)
        self.Valve4Button.clicked.connect(self.on_Valve4Button_clicked)
        self.Valve5Button.clicked.connect(self.on_Valve5Button_clicked)
        # self.Valve6Button.clicked.connect(self.on_Valve6Button_clicked)
        # self.Valve7Button.clicked.connect(self.on_Valve7Button_clicked)
        # self.Valve8Button.clicked.connect(self.on_Valve8Button_clicked)
        # self.pressureMonitorButton.clicked.connect(self.on_pressureMonitorButton_clicked)
        self.pressure1RadioButton.clicked.connect(
            self.on_pressure1RadioButton_clicked)
        self.pressure2RadioButton.clicked.connect(
            self.on_pressure2RadioButton_clicked)
        self.pressure3RadioButton.clicked.connect(
            self.on_pressure3RadioButton_clicked)
        self.pressure4RadioButton.clicked.connect(
            self.on_pressure4RadioButton_clicked)
        self.selectSavePathButton.clicked.connect(
            self.on_selectSavePathButton_clicked)
        self.resetButton.clicked.connect(self.on_resetButton_clicked)
        self.beginSaveButton.clicked.connect(self.on_beginSaveButton_clicked)
        self.quickVentButton.clicked.connect(self.on_quickVentButton_clicked)

        # Connect menu actions to their slots
        self.editMotorMacroAction.triggered.connect(self.edit_motor_macro)
        self.editValveMacroAction.triggered.connect(self.edit_valve_macro)

        self.retranslateUi(MainWindow)
        self.update_controls()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Spectrometer GUI"))
        self.ardCOMPortLabel.setText(
            _translate("MainWindow", "Arduino COM Port"))
        self.ardWarningLabel.setText(_translate("MainWindow", ""))
        self.ardWarningLabel.setStyleSheet("color: red")
        self.autoConnectRadioButton.setText(
            _translate("MainWindow", "Automatic Mode"))
        self.TTLRadioButton.setText(_translate("MainWindow", "TTL Mode"))
        self.manualRadioButton.setText(_translate("MainWindow", "Manual Mode"))
        self.ardConnectButton.setText(_translate("MainWindow", "Connect"))
        self.Valve2Button.setText(_translate("MainWindow", "Inlet"))
        # self.Valve7Button.setText(_translate("MainWindow", "V7"))
        # self.Valve6Button.setText(_translate("MainWindow", "V6"))
        self.Valve1Button.setText(_translate("MainWindow", "Switch"))
        self.Valve4Button.setText(_translate("MainWindow", "Vent"))
        self.Valve3Button.setText(_translate("MainWindow", "Outlet"))
        # self.Valve8Button.setText(_translate("MainWindow", "V8"))
        self.Valve5Button.setText(_translate("MainWindow", "Short"))
        self.ValveLabel.setText(_translate("MainWindow", "Valves"))
        self.showValvesCheckbox.setText(
            _translate("MainWindow", "Graph\nValves"))
        self.motorCOMPortLabel.setText(
            _translate("MainWindow", "Motor COM Port"))
        self.motorWarningLabel.setText(_translate("MainWindow", ""))
        self.motorWarningLabel.setStyleSheet("color: red")
        self.motorConnectButton.setText(
            _translate("MainWindow", "Connect Motor"))
        self.motorCalibrateButton.setText(
            _translate("MainWindow", "Calibrate Motor"))
        self.motorStopButton.setText(_translate("MainWindow", "Stop Motor"))
        # self.pressureMonitorButton.setText(_translate("MainWindow", "Begin Pressure Monitor"))
        self.quickVentButton.setText(_translate("MainWindow", "Quick Vent"))
        self.slowVentButton.setText(_translate("MainWindow", "Slow Vent"))
        self.pressure4RadioButton.setText(
            _translate("MainWindow", "Pressure 4"))
        self.pressure2RadioButton.setText(
            _translate("MainWindow", "Pressure 2"))
        self.pressure1RadioButton.setText(
            _translate("MainWindow", "Pressure 1"))
        self.pressure3RadioButton.setText(
            _translate("MainWindow", "Pressure 3"))
        self.selectSavePathButton.setText(
            _translate("MainWindow", "Select Path.."))
        self.beginSaveButton.setText(_translate("MainWindow", "Begin Saving"))
        self.bubbleTimeLabel.setText(
            _translate("MainWindow", "Bubble Time (s)"))
        self.quickBubbleButton.setText(
            _translate("MainWindow", "Quick Bubble"))
        self.curMotorPosLabel.setText(_translate(
            "MainWindow", "Current Motor Pos (mm)"))
        self.targetMotorPosLabel.setText(
            _translate("MainWindow", "Target Motor Pos (mm)"))
        self.motorMoveToTargetButton.setText(
            _translate("MainWindow", "Move to Target Position"))
        self.motorMacro4Button.setText(
            _translate("MainWindow", "Motor Macro 4"))
        self.motorMacro3Button.setText(
            _translate("MainWindow", "Motor Macro 3"))
        self.motorAscentButton.setText(_translate("MainWindow", "Slow Ascent"))
        self.motorMacro1Button.setText(
            _translate("MainWindow", "Motor Macro 1"))
        self.motorMacro2Button.setText(
            _translate("MainWindow", "Motor Macro 2"))
        self.motorToTopButton.setText(
            _translate("MainWindow", "Return to Top"))
        self.motorMacro5Button.setText(
            _translate("MainWindow", "Motor Macro 5"))
        self.motorMacro6Button.setText(
            _translate("MainWindow", "Motor Macro 6"))
        self.motorMacroMenu.setTitle(
            _translate("MainWindow", "Edit Macros"))
        self.editMotorMacroAction.setText(
            _translate("MainWindow", "Edit Motor Macros"))
        self.editValveMacroAction.setText(_translate(
            "MainWindow", "Edit Valve Macros"))
        self.savePathEdit.setText(_translate("MainWindow", "C:/NMR Results"))
        self.resetButton.setText(_translate("MainWindow", "Reset"))
        self.valveMacro1Button.setText(
            _translate("MainWindow", "Valve Macro 1"))
        self.valveMacro2Button.setText(
            _translate("MainWindow", "Valve Macro 2"))
        self.valveMacro3Button.setText(
            _translate("MainWindow", "Valve Macro 3"))
        self.valveMacro4Button.setText(
            _translate("MainWindow", "Valve Macro 4"))
        self.valveMacro5Button.setText(
            _translate("MainWindow", "Valve Macro 5"))
        self.valveMacro6Button.setText(
            _translate("MainWindow", "Valve Macro 6"))
        self.sequenceLabel.setText(_translate("MainWindow", "Sequence\nControls"))
        self.sequenceLoadButton.setText(_translate("MainWindow", "Load Sequence"))
        self.sequenceExecuteButton.setText(_translate("MainWindow", "Execute Sequence"))
        self.sequenceStopButton.setText(_translate("MainWindow", "Stop Sequence"))
        self.currentStepTypeLabel.setText(_translate("MainWindow", "Current Step Type"))
        self.currentStepTimeLabel.setText(_translate("MainWindow", "Current Step Time"))
        self.stepsRemainingLabel.setText(_translate("MainWindow", "Steps Remaining: "))
        self.stepsTimeRemainingLabel.setText(_translate("MainWindow", "Time Remaining: "))


    def on_ardConnectButton_clicked(self):

        if self.connection_in_progress:
            return  # Ignore subsequent clicks if connection is in progress

        # Set the flag to indicate connection in progress
        self.connection_in_progress = True
        # Disable the button to prevent multiple clicks
        self.ardConnectButton.setEnabled(False)

        if self.ardConnected == True:
            self.ardConnected = False
            self.UIUpdateArdConnection()
            self.controller.serial_connected = False    # type: ignore
            if self.controller != None:
                self.controller.stop()  # type: ignore

        else:
            if self.ardCOMPortSpinBox.value() == None:
                self.ardWarningLabel.setText("No COM Port Selected")
                self.ardWarningLabel.setStyleSheet("color: red")
                self.ardConnected = False
                self.UIUpdateArdConnection()
                return
            elif self.selectedMode != None:
                try:
                    self.controller = ArduinoController(
                        port=self.ardCOMPortSpinBox.value(), verbose=self.verbosity, mode=self.selectedMode)
                    try:
                        self.controller.start()
                        if self.controller.serial_connected:
                            self.ardConnected = True
                            self.start_plotting()
                            self.UIUpdateArdConnection()
                        else:
                            self.ardWarningLabel.setText(
                                "Controller Failed to Start")
                            self.ardWarningLabel.setStyleSheet("color: red")
                            self.ardConnected = False
                            self.controller.stop()
                            self.controller = None
                            self.UIUpdateArdConnection()
                    except Exception as e:
                        if self.verbosity:
                            print(e)
                        self.ardWarningLabel.setText(
                            "Controller Failed to Start")
                        self.ardWarningLabel.setStyleSheet("color: red")
                        self.ardConnected = False
                        self.controller.stop()  # type: ignore
                        self.controller = None
                        self.UIUpdateArdConnection()
                        return
                except Exception as e:
                    if self.verbosity:
                        print(e)
                    self.ardWarningLabel.setText("Connection Failed")
                    self.ardWarningLabel.setStyleSheet("color: red")
                    self.ardConnected = False
                    if self.controller != None:
                        try:
                            self.controller.stop()
                        except Exception as e:
                            if self.verbosity:
                                print(e)
                        self.controller = None
                    self.UIUpdateArdConnection()
                    return
            else:
                self.ardWarningLabel.setText("No Mode Selected")
                self.ardWarningLabel.setStyleSheet("color: red")
                self.ardConnected = False
                self.UIUpdateArdConnection()

    def on_autoConnectRadioButton_clicked(self):
        self.selectedMode = 1

    def on_TTLRadioButton_clicked(self):
        self.selectedMode = 2

    def on_manualRadioButton_clicked(self):
        self.selectedMode = 0

    def UIUpdateArdConnection(self):
        self.connection_in_progress = False  # Reset the flag
        self.ardConnectButton.setEnabled(True)  # Re-enable the button
        if self.ardConnected == False:
            self.ardConnectButton.setText("Connect")
            self.ardCOMPortSpinBox.setEnabled(True)
            self.autoConnectRadioButton.setEnabled(True)
            self.TTLRadioButton.setEnabled(True)
            self.manualRadioButton.setEnabled(True)
        else:
            self.ardConnectButton.setText("Disconnect")
            self.ardCOMPortSpinBox.setEnabled(False)
            self.autoConnectRadioButton.setEnabled(False)
            self.TTLRadioButton.setEnabled(False)
            self.manualRadioButton.setEnabled(False)
            self.ardWarningLabel.setText("Connected")
            self.ardWarningLabel.setStyleSheet("color: green")
        self.update_controls()

    def on_Valve1Button_clicked(self):
        logging.info("Valve 1 button clicked")
        self.Valve1Button.setChecked(False)
        if self.ardConnected:
            self.controller.get_valve_states()  # type: ignore
            if self.controller.valve_states[0] == 0:    # type: ignore
                logging.info("Turning on valve 1")
                self.controller.send_command(   # type: ignore
                    "TURN_ON_SWITCH_VALVE")  # type: ignore
                self.Valve1Button.setChecked(True)
            else:
                logging.info("Turning off valve 1")
                self.controller.send_command(   # type: ignore
                    "TURN_OFF_SWITCH_VALVE")  # type: ignore
                self.Valve1Button.setChecked(False)

    def on_Valve2Button_clicked(self):
        logging.info("Valve 2 button clicked")
        self.Valve2Button.setChecked(False)
        if self.ardConnected:
            self.controller.get_valve_states()  # type: ignore
            if self.controller.valve_states[1] == 0:    # type: ignore
                logging.info("Turning on valve 2")
                self.controller.send_command(   # type: ignore
                    "TURN_ON_INLET_VALVE")  # type: ignore
                self.Valve2Button.setChecked(True)
            else:
                logging.info("Turning off valve 2")
                self.controller.send_command(   # type: ignore
                    "TURN_OFF_INLET_VALVE")  # type: ignore
                self.Valve2Button.setChecked(False)

    def on_Valve3Button_clicked(self):
        logging.info("Valve 3 button clicked")
        self.Valve3Button.setChecked(False)
        if self.ardConnected:
            self.controller.get_valve_states()  # type: ignore
            if self.controller.valve_states[2] == 0:    # type: ignore
                logging.info("Turning on valve 3")
                self.controller.send_command(   # type: ignore
                    "TURN_ON_OUTPUT_VALVE")  # type: ignore
                self.Valve3Button.setChecked(True)
            else:
                logging.info("Turning off valve 3")
                self.controller.send_command(   # type: ignore
                    "TURN_OFF_OUTPUT_VALVE")  # type: ignore
                self.Valve3Button.setChecked(False)

    def on_Valve4Button_clicked(self):
        logging.info("Valve 4 button clicked")
        self.Valve4Button.setChecked(False)
        if self.ardConnected:
            self.controller.get_valve_states()  # type: ignore
            if self.controller.valve_states[3] == 0:    # type: ignore
                logging.info("Turning on valve 4")
                self.controller.send_command(   # type: ignore
                    "TURN_ON_VENT_VALVE")  # type: ignore
                self.Valve4Button.setChecked(True)
            else:
                logging.info("Turning off valve 4")
                self.controller.send_command(   # type: ignore
                    "TURN_OFF_VENT_VALVE")   # type: ignore
                self.Valve4Button.setChecked(False)

    def on_Valve5Button_clicked(self):
        logging.info("Valve 5 button clicked")
        self.Valve5Button.setChecked(False)
        # self.controller.get_valve_states()  # type: ignore
        if self.ardConnected:
            if self.controller.valve_states[4] == 0:    # type: ignore
                logging.info("Turning on valve 5")
                self.controller.send_command(   # type: ignore
                    "TURN_ON_SHORT_VALVE")  # type: ignore
                self.Valve5Button.setChecked(True)
            else:
                logging.info("Turning off valve 5")
                self.controller.send_command(   # type: ignore
                    "TURN_OFF_SHORT_VALVE")   # type: ignore
                self.Valve5Button.setChecked(False)
    '''
    def on_Valve6Button_clicked(self):
        logging.info("Valve 6 button clicked")
        self.Valve6Button.setChecked(False)
        logging.info("Valve 6 not implemented")

    def on_Valve7Button_clicked(self):
        logging.info("Valve 7 button clicked")
        self.Valve7Button.setChecked(False)
        logging.info("Valve 7 not implemented")

    def on_Valve8Button_clicked(self):
        logging.info("Valve 8 button clicked")
        self.Valve8Button.setChecked(False)
        logging.info("Valve 8 not implemented")
    '''
    """
    def on_pressureMonitorButton_clicked(self):
        logging.info("Pressure monitor button clicked")
        if self.ardConnected:
            if self.monitoring:
                self.monitoring = False
                self.pressureMonitorButton.setText("Begin Pressure Monitor")
                self.controller.send_command(
                    "DISABLE_PRESSURE_LOG") # type: ignore
            else:
                self.monitoring = True
                self.pressureMonitorButton.setText("Stop Pressure Monitor")
                self.controller.send_command(
                    "ENABLE_PRESSURE_LOG") # type: ignore
        else:
            if self.monitoring:
                self.monitoring = False
                self.pressureMonitorButton.setText("Begin Pressure Monitor")
    """

    def start_plotting(self):
        self.monitoring = True
        self.plot_thread = threading.Thread(target=self.update_plot)
        self.plot_thread.daemon = True
        self.plot_thread.start()

    def update_plot(self):
        while self.monitoring:
            if self.ardConnected and self.controller.new_plot:  # type: ignore
                self.controller.new_plot = False  # type: ignore
                self.sc.axes.clear()
                # Extract timestamps
                # timestamps = [float(reading[0]) for reading in self.controller.readings]
                num_readings = len(self.controller.readings)
                timestamps = list(range(1, num_readings + 1))

                # Extract the specific pressure readings
                if self.pressure1RadioButton.isChecked():
                    pressure_readings = [
                        float(reading[1]) for reading in self.controller.readings]
                    self.sc.axes.plot(
                        timestamps, pressure_readings) 
                if self.pressure2RadioButton.isChecked():
                    pressure_readings = [
                        float(reading[2]) for reading in self.controller.readings]
                    self.sc.axes.plot(
                        timestamps, pressure_readings)
                if self.pressure3RadioButton.isChecked():
                    pressure_readings = [
                        float(reading[3]) for reading in self.controller.readings]
                    self.sc.axes.plot(
                        timestamps, pressure_readings)
                if self.pressure4RadioButton.isChecked():
                    pressure_readings = [
                        float(reading[4]) for reading in self.controller.readings]
                    self.sc.axes.plot(
                        timestamps, pressure_readings)

                # Plot pressure against time
                self.sc.draw()
        
    def stop_plotting(self):
        self.monitoring = False
        self.plot_thread.join()

    def on_pressure1RadioButton_clicked(self):
        pass

    def on_pressure2RadioButton_clicked(self):
        pass

    def on_pressure3RadioButton_clicked(self):
        pass

    def on_pressure4RadioButton_clicked(self):
        pass

    def on_selectSavePathButton_clicked(self):
        """
        logging.info("Select save path button clicked")
        self.save_path = QtWidgets.QFileDialog.getExistingDirectory(
            directory=self.savePathEdit.text())
        self.savePathEdit.setText(os.path.join(
            self.save_path, f"pressure_data_{time.strftime('%m%d-%H%M')}.csv").replace("/", "\\"))
        """
        self.save_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.savePathEdit,
            "Select CSV File",
            self.savePathEdit.text(),
            "CSV Files (*.csv)"
        )

        if self.save_path:
            self.savePathEdit.setText(self.save_path)  # Optionally update the text field with the selected path
        else:
            self.savePathEdit.setText(os.path.join(
                self.default_save_path, f"pressure_data_{time.strftime('%m%d-%H%M')}.csv").replace("/", "\\"))

    def on_resetButton_clicked(self):
        logging.info("Reset button clicked")
        if self.ardConnected:
            self.controller.send_command("RESET")  # type: ignore

    def on_quickVentButton_clicked(self):
        logging.info("Quick vent button clicked")
        if self.ardConnected:
            self.controller.send_command("DEPRESSURISE")  # type: ignore

    def on_beginSaveButton_clicked(self):
        logging.info("Begin save button clicked")
        if self.ardConnected:
            if self.saving:
                self.saving = False
                self.beginSaveButton.setText("Begin Saving")
                self.controller.save_pressure_data(False, self.savePathEdit.text()) # type: ignore
            else:
                self.saving = True
                self.beginSaveButton.setText("Stop Saving")
                self.controller.save_pressure_data(True, self.savePathEdit.text()) # type: ignore

    def on_connectMotorButton_clicked(self):
        logging.info("Connect motor button clicked")
        if self.motorConnected:
            self.motorConnected = False
            self.UIUpdateMotorConnection()
            if self.motorController != None:
                self.motorController.serial_connected = False
                self.motorController.stop()
                # self.motorController = None    
        else:
            self.motorController = MotorController(port = self.ardCOMPortSpinBox.value())
            try:
                self.motorController.start()
                if self.motorController.serial_connected:
                    self.motorConnected = True
                    logging.info("Motor connected")
                    self.UIUpdateMotorConnection()
                else:
                    logging.info("Motor failed to connect")
                    self.motorConnected = False
                    self.motorController.stop()
                    self.motorController = None
                    self.UIUpdateMotorConnection()
            except Exception as e:
                logging.error(e)
                self.motorConnected = False
                self.motorController.stop()
                self.motorController = None
                self.UIUpdateMotorConnection()
    
    def on_calibrateMotorButton_clicked(self):
        logging.info("Calibrate motor button clicked")
        if self.motorConnected:
            self.motorController.calibrate()

    def on_stopMotorButton_clicked(self):
        logging.info("Stop motor button clicked")
        if self.motorConnected:
            self.motorController.stop_motor()

    def on_moveToTargetButton_clicked(self):
        logging.info("Move to target button clicked")
        if self.motorConnected:
            targetpos = float(self.targetMotorPosEdit.text())
            self.motorController.move_to_target(float(self.targetMotorPosEdit.text()))

    def add_step(self, step_type, time_length):
        step = Step(step_type, time_length)
        self.steps.append(step)

    def remove_step(self, index):
        if 0 <= index < len(self.steps):
            del self.steps[index]

    def list_steps(self):
        for step in self.steps:
            print(f"Step Type: {step.step_type}, Time Length: {step.time_length}")

    def edit_motor_macro(self):
        pass

    def edit_valve_macro(self):
        dialog = ValveMacroEditor(self)
        dialog.exec()

    def update_controls(self):
        if self.ardConnected:
            # Toggle connection controls
            self.manualRadioButton.setEnabled(False)
            self.autoConnectRadioButton.setEnabled(False)
            self.TTLRadioButton.setEnabled(False)
            self.ardCOMPortSpinBox.setEnabled(False)
            # Toggle graphing controls
            self.pressure1RadioButton.setEnabled(True)
            self.pressure2RadioButton.setEnabled(True)
            self.pressure3RadioButton.setEnabled(True)
            self.pressure4RadioButton.setEnabled(True)
            # Toggle save controls
            self.beginSaveButton.setEnabled(True)
            #self.savePathEdit.setEnabled(True)
            #self.selectSavePathButton.setEnabled(True)
            if self.selectedMode == 0:
                # Toggle valve controls
                self.Valve1Button.setEnabled(True)
                self.Valve2Button.setEnabled(True)
                self.Valve3Button.setEnabled(True)
                self.Valve4Button.setEnabled(True)
                self.Valve5Button.setEnabled(True)
                # self.Valve6Button.setEnabled(True)
                # self.Valve7Button.setEnabled(True)
                # self.Valve8Button.setEnabled(True)
                # self.pressureMonitorButton.setEnabled(True)
                self.quickVentButton.setEnabled(True)
                self.slowVentButton.setEnabled(True)
                self.valveMacro1Button.setEnabled(True)
                self.valveMacro2Button.setEnabled(True)
                self.valveMacro3Button.setEnabled(True)
                self.valveMacro4Button.setEnabled(True)
                self.valveMacro5Button.setEnabled(True)
                self.valveMacro6Button.setEnabled(True)
                self.quickBubbleButton.setEnabled(True)
                self.bubbleTimeDoubleSpinBox.setEnabled(True)
            elif self.selectedMode == 1 or self.selectedMode == 2:
                # Toggle valve controls
                self.Valve1Button.setEnabled(False)
                self.Valve2Button.setEnabled(False)
                self.Valve3Button.setEnabled(False)
                self.Valve4Button.setEnabled(False)
                self.Valve5Button.setEnabled(False)
                # self.Valve6Button.setEnabled(False)
                # self.Valve7Button.setEnabled(False)
                # self.Valve8Button.setEnabled(False)
                # self.pressureMonitorButton.setEnabled(False)
                self.quickVentButton.setEnabled(False)
                self.slowVentButton.setEnabled(False)
                self.valveMacro1Button.setEnabled(False)
                self.valveMacro2Button.setEnabled(False)
                self.valveMacro3Button.setEnabled(False)
                self.valveMacro4Button.setEnabled(False)
                self.valveMacro5Button.setEnabled(False)
                self.valveMacro6Button.setEnabled(False)
                self.quickBubbleButton.setEnabled(False)
                self.bubbleTimeDoubleSpinBox.setEnabled(False)
        else:
            # Toggle connection controls
            self.manualRadioButton.setEnabled(True)
            self.autoConnectRadioButton.setEnabled(True)
            self.TTLRadioButton.setEnabled(True)
            self.ardCOMPortSpinBox.setEnabled(True)
            # Toggle valve controls
            self.Valve1Button.setEnabled(False)
            self.Valve2Button.setEnabled(False)
            self.Valve3Button.setEnabled(False)
            self.Valve4Button.setEnabled(False)
            self.Valve5Button.setEnabled(False)
            # self.Valve6Button.setEnabled(False)
            # self.Valve7Button.setEnabled(False)
            # self.Valve8Button.setEnabled(False)
            # self.pressureMonitorButton.setEnabled(False)
            self.quickVentButton.setEnabled(False)
            self.slowVentButton.setEnabled(False)
            self.valveMacro1Button.setEnabled(False)
            self.valveMacro2Button.setEnabled(False)
            self.valveMacro3Button.setEnabled(False)
            self.valveMacro4Button.setEnabled(False)
            self.valveMacro5Button.setEnabled(False)
            self.valveMacro6Button.setEnabled(False)
            self.quickBubbleButton.setEnabled(False)
            self.bubbleTimeDoubleSpinBox.setEnabled(False)
            # Toggle graphing controls
            self.pressure1RadioButton.setEnabled(False)
            self.pressure2RadioButton.setEnabled(False)
            self.pressure3RadioButton.setEnabled(False)
            self.pressure4RadioButton.setEnabled(False)
            # Toggle save controls
            self.beginSaveButton.setEnabled(False)
            #self.savePathEdit.setEnabled(False)
            #self.selectSavePathButton.setEnabled(False)
        if self.saving:
            self.savePathEdit.setEnabled(False)
            self.selectSavePathButton.setEnabled(False)
        else:
            self.savePathEdit.setEnabled(True)
            self.selectSavePathButton.setEnabled(True)
        


class QTextEditLogger(logging.Handler, QtCore.QObject):
    appendPlainText = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super().__init__()
        QtCore.QObject.__init__(self)
        self.widget = parent
        self.widget.setReadOnly(True)
        self.appendPlainText.connect(self.widget.insertPlainText)
        self.appendPlainText.connect(self.scroll_to_bottom)

    def emit(self, record):
        msg = self.format(record) + '\n'
        self.appendPlainText.emit(msg)

    @QtCore.pyqtSlot()
    def scroll_to_bottom(self):
        self.widget.verticalScrollBar().setValue(
            self.widget.verticalScrollBar().maximum())
    
    def close(self):
        self.widget.clear()
        super().close()

class ValveMacroEditor(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Valve Macro Editor")
        self.setGeometry(100, 100, 650, 260)
        self.setFixedSize(620, 250)

        # Create a table widget
        self.table = QtWidgets.QTableWidget(self)
        self.table.setRowCount(6)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["Macro No.", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"])        
        
        # Set layout
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addWidget(self.table)
        self.setLayout(self.mainLayout)

                # Determine the directory of the executable
        self.executable_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

        # Load data from JSON file if it exists
        self.load_data()

        # Resize all columns to fit
        self.table.resizeColumnsToContents()

        self.table

    def load_data(self):
        json_path = os.path.join(self.executable_dir, 'valve_macro_data.json')
        #print(json_path)
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                for i, macro in enumerate(data):
                    item = QtWidgets.QTableWidgetItem(macro["Macro No."])
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make the item read-only
                    self.table.setItem(i, 0, item)
                    for j, state in enumerate(macro["Valves"], start=1):
                        combo = QtWidgets.QComboBox()
                        combo.addItems(["Open", "Closed", "Ignore"])
                        combo.setCurrentText(state)
                        self.table.setCellWidget(i, j, combo)
            except (json.JSONDecodeError, KeyError, IndexError):
                self.set_default_values()
        else:
            self.set_default_values()

    def set_default_values(self):
        for i in range(6):
            item = QtWidgets.QTableWidgetItem(f"Macro {i+1}")
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make the item read-only
            self.table.setItem(i, 0, item)
            for j in range(1, 9):
                combo = QtWidgets.QComboBox()
                combo.addItems(["Open", "Closed"])
                combo.setCurrentIndex(1)  # Default to "Closed"
                self.table.setCellWidget(i, j, combo)
    
    def get_macro_data(self):
        data = []
        for row in range(self.table.rowCount()):
            macro_number = self.table.item(row, 0).text()
            valve_states = [self.table.cellWidget(row, col).currentText() for col in range(1, 9)]
            data.append({"Macro No.": macro_number, "Valves": valve_states})
        return data
    
    def closeEvent(self, event):
        data = self.get_macro_data()
        json_path = os.path.join(self.executable_dir, 'valve_macro_data.json')
        print(json_path)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        super().closeEvent(event)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setup_logging()
        # Example plot
        # self.plot()

    def plot(self):
        self.sc.axes.plot([0, 1, 2, 3], [10, 1, 20, 3])
        self.sc.draw()

    def setup_logging(self):
        # Initialize the logger
        self.logTextBox = QTextEditLogger(self.textBrowser)
        self.logTextBox.setFormatter(logging.Formatter('%(message)s'))
        # %(asctime)s %(levelname)s %(module)s %(funcName)s

        logging.getLogger().addHandler(self.logTextBox)
        logging.getLogger().setLevel(logging.DEBUG)

        """
        # Log to file
        fh = logging.FileHandler('my-log.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s'))
        logging.getLogger().addHandler(fh)
        """

    def closeEvent(self, event):
        if self.plot_thread is not None:
            self.stop_plotting()

        if self.ardConnected or self.controller is not None:
            if self.verbosity:
                print("Arduino is still connected, stopping controller...")
            try:
                self.controller.stop()  # type: ignore
            except Exception as e:
                if self.verbosity:
                    print(e)
            if self.verbosity:
                print("Controller stopped")
        if self.verbosity:
            print("Application is closing...")

        """       
        # Remove and close logging handlers
        logger = logging.getLogger()
        handlers = logger.handlers[:]
        for handler in handlers:
            handler.close()
            logger.removeHandler(handler)

        # Ensure QTextEditLogger is properly closed
        if hasattr(self, 'logTextBox'):
            self.logTextBox.close()
        """     
        # Call the base class method to ensure the window closes
        event.accept()


if __name__ == "__main__":
    global_stylesheet = """
        QPushButton:disabled {
            background-color: grey;
            color: white;
        }
        QLineEdit:disabled {
            background-color: grey;
            color: black;
        }
        QSpinBox:disabled {
            background-color: grey;
            color: black;
        }
        """

    app = QtWidgets.QApplication(sys.argv)

    app.setStyleSheet(global_stylesheet)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
