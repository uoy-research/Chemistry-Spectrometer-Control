import tkinter as tk
from tkinter import ttk, messagebox
import TKinterModernThemes as TKMT
from TKinterModernThemes.WidgetFrame import Widget
import serial
# from ArdControl.arduinoController import ArduinoController
# TKMT docs https://github.com/RobertJN64/TKinterModernThemes

defaultPort = "4"

def buttonCMD():
        print("Button clicked!")

class App(TKMT.ThemedTKinterFrame):
    def __init__(self, theme, mode, usecommandlineargs=True, usethemeconfigfile=True):
        super().__init__("Spec Control", theme, mode, usecommandlineargs, usethemeconfigfile)
        
        self.init = True
        # Set window size
        self.root.geometry("800x600")
        # self.root.wm_maxsize(800, 600)
        # self.root.wm_minsize(800, 600)
        self.root.resizable(False, False)

        self.notebook = self.Notebook("App Notebook")
        self.tab1 = self.notebook.addTab("Manual")
        self.tab2 = self.notebook.addTab("Auto")
        self.tab3 = self.notebook.addTab("TTL")

        # Bind the tab change event
        self.notebook.notebook.bind("<<NotebookTabChanged>>", self.onTabChange)
        self.previous_tab = self.notebook.notebook.index("current")

        # Add widgets to the notebook tabs
        self.tab1.Label("Arduino controls", row=0, col=0, size=15)
        self.tab1.Label("Connect to Arduino", row=1, col=0, size=10)
        self.connectSerialButton = self.tab1.Button("Connect", self.connectSerial, row=1, col=1)
        self.tab1.Label("Port No.", row=2, col=0, size=10)
        self.portNo = tk.Variable()
        self.portNo.set(defaultPort)
        self.tab1.NumericalSpinbox(variable = self.portNo, row=2, col=1, lower=1, upper=255, increment=1, pady=10)
        self.warning_label = self.tab1.Label("", row=2, col=0, size=8, pady=10,padx=10, sticky="S")
        self.warning_label.config({"foreground":"red"})
        #self.tab1.Label("Manual Control", row=4, col=0, size=10, colspan=2)
        self.manualEnable = tk.BooleanVar()
        self.manualControlButton = self.tab1.Checkbutton("Manual Valve Control", self.manualEnable, row=0, col=2, colspan=1, style="Switch.TCheckbutton", padx=10, pady=10)
        self.manualEnable.trace_add("write", self.manualControl)
        
        self.valveStates = []
        self.valveButtons = []

        for i in range(8):
            valve_state = tk.BooleanVar()
            valve_button = self.tab1.Checkbutton(
                "Valve " + str(i + 1), 
                valve_state, 
                row=1 + i, 
                col=2, 
                style="Switch.TCheckbutton", 
                padx=10, 
                pady=10
            )
            valve_state.trace_add("write", lambda *args, valve=i: self.printValve(valve))
            valve_button.grid_remove()
            self.valveStates.append(valve_state)
            self.valveButtons.append(valve_button)

        self.serialConnected = False

        self.tab2.addLabelFrame("Auto Control")
        self.tab2.Button("Auto Button", buttonCMD)

        self.tab3.addLabelFrame("TTL Control")
        self.tab3.Button("TTL Button", buttonCMD)




        self.run(onlyFrames=False, cleanresize=False, recursiveResize=False)
    
    def onTabChange(self, event):
        if(self.init == True):
            self.init = False
            return
        else:
            current_tab = self.notebook.notebook.index("current")
            if not messagebox.askyesno("Confirm", "Do you want to switch tabs?"):
                self.notebook.notebook.select(self.previous_tab)
                self.init = True
            else:
                self.previous_tab = current_tab

    def connectSerial(self):
        if(not self.serialConnected):
            print("validating port number")
            try:
                port = int(self.portNo.get())
                if(port < 1 or port > 255):
                    raise ValueError
                else:
                    print("Port number is valid")
                    self.warning_label.config(text="")

            except ValueError:
                self.warning_label.config(text="Invalid port number")
                print("Port number is invalid")
                self.connectSerialButton.config(text="Connect")
                return
            
            print("Connecting to Arduino")
            serialPort = "COM" + self.portNo.get()
            try:
                self.ser = serial.Serial(serialPort, 9600)
                print("Connected to Arduino")
                self.warning_label.config(text="")
                self.connectSerialButton.config(text="Disconnect")
                self.serialConnected = True
            except serial.SerialException:
                print("Failed to connect to Arduino")
                self.warning_label.config(text="Failed to connect to Arduino on " + serialPort)
                self.connectSerialButton.config(text="Connect")
                #disable manual control
                return
        else:
            print("Disconnecting from Arduino")
            try:
                self.ser.close()
                print("Disconnected from Arduino")
                self.connectSerialButton.config(text="Connect")
                self.serialConnected = False
            except serial.SerialException:
                print("Error disconnecting from Arduino")
                self.connectSerialButton.config(text="Connect")
                self.serialConnected = False
                #disable manual control

    def manualControl(self, *args):
        if (self.manualEnable.get() and self.serialConnected == True):
            print("Manual control enabled")
            for button in self.valveButtons:
                button.grid()
        else:
            print("Manual control disabled")
            self.manualEnable.set(False)
            if self.serialConnected == False:
                print("Cannot enable manual control without connecting to Arduino")
            for button in self.valveButtons:
                button.grid_remove()

    def printValve(self, valve):
        if self.valveStates[valve].get():
            print("Valve " + str(valve+1) + " is open")
            # Tell arduino to open valve
        else:  
            print("Valve " + str(valve+1) + " is closed")
            # Tell arduino to close valve



if __name__ == "__main__":
    App("sun-valley", "light")