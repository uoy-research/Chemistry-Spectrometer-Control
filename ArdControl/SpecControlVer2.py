from arduinoController import ArduinoController
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from PyQt6 import QtCore, QtGui, QtWidgets
import sys
import matplotlib
import time
matplotlib.use('QtAgg')


class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):

        # Initialise variables
        self.verbosity = True
        self.ardConnected = False
        self.selectedMode = None
        self.controller = None

        # Create the main window
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1029, 657)

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
        self.line.setGeometry(QtCore.QRect(10, 300, 1041, 20))
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")

        # Create the valve layout
        self.gridLayoutWidget = QtWidgets.QWidget(parent=self.centralwidget)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 320, 181, 294))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.valveLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.valveLayout.setContentsMargins(0, 0, 0, 0)
        self.valveLayout.setObjectName("valveLayout")

        # Create the valve buttons
        self.Valve2Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve2Button.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Valve2Button.setFont(font)
        self.Valve2Button.setObjectName("Valve2Button")
        self.valveLayout.addWidget(self.Valve2Button, 2, 1, 1, 1)
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
        self.Valve1Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve1Button.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Valve1Button.setFont(font)
        self.Valve1Button.setObjectName("Valve1Button")
        self.valveLayout.addWidget(self.Valve1Button, 2, 0, 1, 1)
        self.Valve4Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve4Button.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Valve4Button.setFont(font)
        self.Valve4Button.setObjectName("Valve4Button")
        self.valveLayout.addWidget(self.Valve4Button, 3, 1, 1, 1)
        self.Valve3Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve3Button.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Valve3Button.setFont(font)
        self.Valve3Button.setObjectName("Valve3Button")
        self.valveLayout.addWidget(self.Valve3Button, 3, 0, 1, 1)
        self.Valve8Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve8Button.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Valve8Button.setFont(font)
        self.Valve8Button.setObjectName("Valve8Button")
        self.valveLayout.addWidget(self.Valve8Button, 5, 1, 1, 1)
        self.Valve5Button = QtWidgets.QPushButton(parent=self.gridLayoutWidget)
        self.Valve5Button.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Valve5Button.setFont(font)
        self.Valve5Button.setObjectName("Valve5Button")
        self.valveLayout.addWidget(self.Valve5Button, 4, 0, 1, 1)

        # Create the valve label and checkbox
        self.ValveLabel = QtWidgets.QLabel(parent=self.gridLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(18)
        self.ValveLabel.setFont(font)
        self.ValveLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.ValveLabel.setObjectName("ValveLabel")
        self.valveLayout.addWidget(self.ValveLabel, 0, 0, 1, 2)
        self.showValvesCheckbox = QtWidgets.QCheckBox(
            parent=self.gridLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.showValvesCheckbox.setFont(font)
        self.showValvesCheckbox.setTristate(False)
        self.showValvesCheckbox.setObjectName("showValvesCheckbox")
        self.valveLayout.addWidget(
            self.showValvesCheckbox, 6, 0, 1, 2, QtCore.Qt.AlignmentFlag.AlignHCenter)

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

        # Create the pressure monitor button
        self.pressureMonitorButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.pressureMonitorButton.setMinimumSize(QtCore.QSize(0, 50))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.pressureMonitorButton.setFont(font)
        self.pressureMonitorButton.setObjectName("pressureMonitorButton")
        self.monitorLayout.addWidget(self.pressureMonitorButton, 0, 0, 1, 2)

        # Create the pressure radio buttons
        self.pressure4RadioButton = QtWidgets.QRadioButton(
            parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pressure4RadioButton.setFont(font)
        self.pressure4RadioButton.setObjectName("pressure4RadioButton")
        self.pressure4RadioButton.setAutoExclusive(False)
        self.monitorLayout.addWidget(
            self.pressure4RadioButton, 2, 1, 1, 1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.pressure2RadioButton = QtWidgets.QRadioButton(
            parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pressure2RadioButton.setFont(font)
        self.pressure2RadioButton.setObjectName("pressure2RadioButton")
        self.pressure2RadioButton.setAutoExclusive(False)
        self.monitorLayout.addWidget(
            self.pressure2RadioButton, 1, 1, 1, 1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.pressure1RadioButton = QtWidgets.QRadioButton(
            parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pressure1RadioButton.setFont(font)
        self.pressure1RadioButton.setObjectName("pressure1RadioButton")
        self.pressure1RadioButton.setAutoExclusive(False)
        self.monitorLayout.addWidget(
            self.pressure1RadioButton, 1, 0, 1, 1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.pressure3RadioButton = QtWidgets.QRadioButton(
            parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pressure3RadioButton.setFont(font)
        self.pressure3RadioButton.setObjectName("pressure3RadioButton")
        self.pressure3RadioButton.setAutoExclusive(False)
        self.monitorLayout.addWidget(
            self.pressure3RadioButton, 2, 0, 1, 1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

        # Create the save path buttons
        self.selectSavePathButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.selectSavePathButton.setMinimumSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.selectSavePathButton.setFont(font)
        self.selectSavePathButton.setObjectName("selectSavePathButton")
        self.monitorLayout.addWidget(self.selectSavePathButton, 3, 0, 1, 1)
        self.savePathEdit = QtWidgets.QLineEdit(parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.savePathEdit.setFont(font)
        self.savePathEdit.setObjectName("savePathEdit")
        self.monitorLayout.addWidget(self.savePathEdit, 4, 0, 1, 2)
        self.beginSaveButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.beginSaveButton.setMinimumSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.beginSaveButton.setFont(font)
        self.beginSaveButton.setObjectName("beginSaveButton")
        self.monitorLayout.addWidget(self.beginSaveButton, 3, 1, 1, 1)

        # Create the bubble time widgets
        self.bubbleTimeLabel = QtWidgets.QLabel(parent=self.gridLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.bubbleTimeLabel.setFont(font)
        self.bubbleTimeLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight |
                                          QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.bubbleTimeLabel.setObjectName("bubbleTimeLabel")
        self.monitorLayout.addWidget(self.bubbleTimeLabel, 6, 0, 1, 1)
        self.quickBubbleButton = QtWidgets.QPushButton(
            parent=self.gridLayoutWidget_2)
        self.quickBubbleButton.setMinimumSize(QtCore.QSize(0, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.quickBubbleButton.setFont(font)
        self.quickBubbleButton.setObjectName("quickBubbleButton")
        self.monitorLayout.addWidget(self.quickBubbleButton, 5, 0, 1, 2)
        self.bubbleTimeDoubleSpinBox = QtWidgets.QDoubleSpinBox(
            parent=self.gridLayoutWidget_2)
        self.bubbleTimeDoubleSpinBox.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTrailing | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.bubbleTimeDoubleSpinBox.setObjectName("bubbleTimeDoubleSpinBox")
        self.monitorLayout.addWidget(self.bubbleTimeDoubleSpinBox, 6, 1, 1, 1)

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
        self.menuBar.addAction(self.motorMacroMenu.menuAction())

        # Create the graph widgets
        self.figure = Figure()
        self.sc = MplCanvas(self, width=5, height=4, dpi=100)
        self.graphWidget = QtWidgets.QWidget(
            parent=self.centralwidget)
        self.graphWidget.setGeometry(QtCore.QRect(200, 325, 551, 294))
        self.graphWidget.setObjectName("graphWidget")
        self.graphLayout = QtWidgets.QVBoxLayout(self.graphWidget)
        self.graphLayout.setContentsMargins(0, 0, 0, 0)
        self.graphLayout.setObjectName("graphLayout")
        self.graphLayout.addWidget(self.sc)

        # Create the toolbar and add it to the layout
        self.toolbar = NavigationToolbar(self.sc, self)
        self.graphLayout.addWidget(self.toolbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Spectrometer GUI"))
        self.ardCOMPortLabel.setText(
            _translate("MainWindow", "Arduino COM Port"))
        self.ardWarningLabel.setText(_translate("MainWindow", "TextLabel"))
        self.ardWarningLabel.setStyleSheet("color: red")
        self.autoConnectRadioButton.setText(
            _translate("MainWindow", "Automatic Mode"))
        self.TTLRadioButton.setText(_translate("MainWindow", "TTL Mode"))
        self.manualRadioButton.setText(_translate("MainWindow", "Manual Mode"))
        self.ardConnectButton.setText(_translate("MainWindow", "Connect"))
        self.Valve2Button.setText(_translate("MainWindow", "Inlet"))
        self.Valve7Button.setText(_translate("MainWindow", "V7"))
        self.Valve6Button.setText(_translate("MainWindow", "V6"))
        self.Valve1Button.setText(_translate("MainWindow", "Switch"))
        self.Valve4Button.setText(_translate("MainWindow", "Vent"))
        self.Valve3Button.setText(_translate("MainWindow", "Outlet"))
        self.Valve8Button.setText(_translate("MainWindow", "V8"))
        self.Valve5Button.setText(_translate("MainWindow", "Short"))
        self.ValveLabel.setText(_translate("MainWindow", "Valves"))
        self.showValvesCheckbox.setText(
            _translate("MainWindow", "Show Valves on Graph"))
        self.motorCOMPortLabel.setText(
            _translate("MainWindow", "Motor COM Port"))
        self.motorWarningLabel.setText(_translate("MainWindow", "TextLabel"))
        self.motorWarningLabel.setStyleSheet("color: red")
        self.motorConnectButton.setText(
            _translate("MainWindow", "Connect Motor"))
        self.motorCalibrateButton.setText(
            _translate("MainWindow", "Calibrate Motor"))
        self.motorStopButton.setText(_translate("MainWindow", "Stop Motor"))
        self.pressureMonitorButton.setText(
            _translate("MainWindow", "Begin Pressure Monitor"))
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
            _translate("MainWindow", "Edit Motor Macros"))
        self.editMotorMacroAction.setText(_translate("MainWindow", "Edit.."))

    def on_ardConnectButton_clicked(self):
        if self.ardConnected == True:
            self.ardConnected = False
            self.UIUpdateArdConnection()
            if self.controller != None:
                self.controller.stop()
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
                            self.UIUpdateArdConnection()
                        else:
                            self.ardWarningLabel.setText(
                                "Controller Failed to Start")
                            self.ardWarningLabel.setStyleSheet("color: red")
                            self.ardConnected = False
                            self.controller.stop()
                            self.controller = None
                    except Exception as e:
                        if self.verbosity:
                            print(e)
                        self.ardWarningLabel.setText(
                            "Controller Failed to Start")
                        self.ardWarningLabel.setStyleSheet("color: red")
                        self.ardConnected = False
                        self.controller.stop()  # type: ignore
                        self.controller = None
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


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Example plot
        self.plot()

    def plot(self):
        self.sc.axes.plot([0, 1, 2, 3], [10, 1, 20, 3])
        self.sc.draw()

    def closeEvent(self, event):
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
    window.plot()
    sys.exit(app.exec())
