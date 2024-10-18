#include <ModbusSerial.h>
#include <Arduino.h>

const int TxenPin = -1; // -1 disables the feature, change that if you are using an RS485 driver, this pin would be connected to the DE and /RE pins of the driver.

const byte SlaveId = 10;
// Modbus Registers Offsets (0-9999)
// const int Lamp1Coil = 0;
const int TTLCoil = 16;
const int testCoil = 17;
const int timeoutToggle = 18;
const int depressuriseStatus = 0;
const int resetStatus = 1;

const int SWITCH = 0; const int IN = 1; const int OUT = 2; const int VENT = 3; const int SHORT = 4;
const int LEDS[] = {32, 34, 36, 38, 40, 42, 44, 46};
const int VALVES[] = {8, 9, 10, 22, 52, 26, 28, 30};
const int test_led = 12;

const int valveCoil[] = {0, 1, 2, 3, 4, 5, 6, 7};
const int LEDCoil[] = {8, 9, 10, 11, 12, 13, 14, 15}; 

// status LEDs
const int STATUS_LEDS[] = {5, 6, 7, 11, 12, 13, 23, 50};

//default timings
const unsigned long DEFPollTime = 500; //default time between pressure readings
const unsigned long DEFPressureTime = 3000; //default time required to build pressure before bubbling
const unsigned long DEFHeartbeatTime = 5000; //default time between heartbeats

//TTL Pins, T4 and T5 not working??
const int T1 = 25; const int T2 = 3; const int T3 = 4; const int T4 = 2; const int T5 = 24;

//Analog pins - pressure1 is external
const int Pressure1 = A1; const int Pressure2 = A2; const int Pressure3 = A3; const int Pressure4 = A4;

//VARIABLES
bool TNcontrol = 0; //TerraNova control - allows valves to be controlled by TTL signals or sequences
bool pressureLog = 1; //log pressure values
bool TTLControl = 1; //TTL control toggle
bool TTLState = 1; //TTL state
bool decodeFlag = 0; //flag to decode a sequence
bool execFlag = 0; //flag to execute a sequence
bool simpleTTL = 0; //simple TTL control toggle - unused
bool newStepFlag = 0; //flag to indicate a new step needs loading
bool prevState = 0; //previous state of TTL inputs

float pressureInputs[4] = {0,0,0,0};  //container for pressure values from the analog pins

unsigned long pollTime = DEFPollTime; //time between pressure readings
unsigned long pressureTime = DEFPressureTime; //time required to build pressure before bubbling
size_t currentStepIndex = 0; //current step in the sequence

unsigned long tNow = 0; //current time
unsigned long tPoll = 0; //start time
unsigned long tStart = 0; //start time of system
unsigned long heartBeat = 0; //time of last heartbeat
unsigned long mbTimeout = 2000; //timeout length for modbus commands
unsigned long mbLast = 0; //time of last modbus command

String sequence = ""; //sequence to be decoded

struct Step {
  char type; //type of step - 'b' for bubble, 'd' for delay, 'n' for alt bubble
  unsigned long length; //length of step in ms
};

Step currentStep = {'e', 1}; //current step in the sequence

Step nextStep = {'e', 1}; //next step in the sequence

bool stepRunning = false; //flag to indicate if a step is currently running

char validTypes[4] = {'b', 'd', 'n', 'e'}; //valid step types

bool started = 0; //flag to indicate if the system has been started

volatile bool resetFlag = 0; //flag to indicate a reset is required - triggered when no serial activity for a set time

#define MySerial Serial // define serial port used, Serial most of the time, or Serial1, Serial2 ... if available
const unsigned long Baudrate = 9600;

// ModbusSerial object
ModbusSerial mb (MySerial, SlaveId, TxenPin);

void declarePins();
void initLEDs();
void addCoils();
void handleTTL();
void reset();
void setValves();
void setValve(int valve, int state);
void readPressure();
void updatePressureRegisters();
void depressurise();
float convertToBar(float pressure);

void setup() {

    MySerial.begin (Baudrate); // works on all boards but the configuration is 8N1 which is incompatible with the MODBUS standard
    // prefer the line below instead if possible
    // MySerial.begin (Baudrate, MB_PARITY_EVEN);
    
    mb.config (Baudrate);
    mb.setAdditionalServerData("ValveController"); // for Report Server ID function (0x11)

    declarePins();
    initLEDs();
    addCoils();
    // Add Lamp1Coil register - Use addCoil() for digital outputs
    // mb.addCoil(Lamp1Coil);
    pinMode(test_led, OUTPUT);
    tStart = millis();
}

void loop() {
    
    if(TTLState == false){  //only run the timer when not in TTL mode
        if(MySerial.available()>0){ //if there is serial activity and system is not in TTL mode
            //digitalWrite(test_led, HIGH);
            mbLast = millis(); //update mbLast
        }
        else{
            //digitalWrite(test_led, LOW);
            if ((long)(millis() - mbLast) > (long)(mbTimeout)){reset();}    //If no serial activity for longer than mbTimeout, declare disconnection
        }
    }

    // Call once inside loop() - all magic here
    mb.task();

    // Attach LedPin to Lamp1Coil register
    // digitalWrite (13, mb.Coil (Lamp1Coil));

    if (mb.coil(TTLCoil) == true){
        handleTTL();
        TTLState = true;
    }
    else{
        if (TTLState == true){mbLast = millis();TTLState = false;}  //If system was in TTL mode, update mbLast and TTLState
            
        setValves(); //set valves based on coil values  

        //check for depressurise command
        if(mb.ists(depressuriseStatus) == 1){depressurise();} //check for depressurise command

        //check for reset command   
        if(mb.ists(resetStatus) == 1){reset();} //check for reset command   
    }

    if((long)(millis() - tPoll) > (long)pollTime){ //if it's time to poll the pressure sensors
        tPoll = millis(); //update tPoll
        //read pressure sensors
        readPressure();
        updatePressureRegisters();

        //if(pressureInputs[2] > 1000){depressurise();} //if pressure is too high, vent
    }
}

void declarePins(){
    //set valve pins as outputs
    for (int i = 0; i < 8; i++)
    {
        pinMode(VALVES[i], OUTPUT);
    }

    //set LED pins as outputs
    for (int i = 0; i < 8; i++)
    {
        pinMode(LEDS[i], OUTPUT);
    }

    //set status LED pins as outputs
    for (int i = 0; i < 8; i++)
    {
        pinMode(STATUS_LEDS[i], OUTPUT);
    }

    //set TTL pins as inputs
    pinMode(T1, INPUT);
    pinMode(T2, INPUT);
    pinMode(T3, INPUT);
    pinMode(T4, INPUT);
    pinMode(T5, INPUT);

    //analog pins as inputs
    pinMode(Pressure1, INPUT);
    pinMode(Pressure2, INPUT);
    pinMode(Pressure3, INPUT);
    pinMode(Pressure4, INPUT);
}

void initLEDs(){
    //set all valves to off
    for (int i = 0; i < 8; i++)
    {
        //setValve(i, 0);
    }

    //set all status LEDs to off
    for (int i = 0; i < 8; i++)
    {
        //setLED(i, 0);
    }
}

void addCoils(){
    //add coils for valves
    for (int i = 0; i < 8; i++)
    {
        mb.addCoil(valveCoil[i]);
    }

    //add coils for status LEDs
    for (int i = 0; i < 8; i++)
    {
        mb.addCoil(LEDCoil[i]);
    }

    mb.addCoil(TTLCoil, true);
    mb.addCoil(testCoil, false);
    mb.addCoil(timeoutToggle, false);
    mb.addIsts(resetStatus, 0);
    mb.addIsts(depressuriseStatus, 0);

    for (int i = 0; i < 4; i++){
        mb.addIreg(i, 0);
    }
}

void handleTTL(){
  if (simpleTTL == 1){ //simple TTL control, currently unreachable
    //set valves based on TTL inputs
    setValve(IN, digitalRead(T1));
    setValve(OUT, digitalRead(T2));
    setValve(SHORT, digitalRead(T3));
    setValve(VENT, digitalRead(T4));
    setValve(SWITCH, digitalRead(T5));
  }
  else
  {
    int combinedState = (digitalRead(T4) << 3) | (digitalRead(T3) << 2) | (digitalRead(T2) << 1) | digitalRead(T1);
    switch(combinedState){
      //TODO Add more cases as needed
      case 0:
        setValve(IN, 0);
        setValve(OUT, 0);
        setValve(SWITCH, 0);
        setValve(VENT, 0);
        setValve(SHORT, 0);
        break;
      default:
        Serial.println("LOG: Invalid TTL input");
        break;
    }
  }
}

void setValve(int valve, int state) //sets the valve & corresponding LED to on or off
{
  digitalWrite(VALVES[valve], state); //set the valve to the desired state
  digitalWrite(LEDS[valve], state);  //set the corresponding valve LED to the same state
  //Serial.println("LOG: Valve " + String(valve+1) + " set to " + String(state));
}

void reset(){
    //default to TTL control
    TTLState = true;
    mb.setCoil(TTLCoil, true);

    //reset prevState checker
    prevState = 0;
    mb.setCoil(timeoutToggle, false);
}

void setValves(){
    //set valves based on coil values
    for (int i = 0; i < 5; i++)
    {
        setValve(i, mb.coil(valveCoil[i]));
    }
}

void readPressure(){
    pressureInputs[0] = analogRead(Pressure1);
    pressureInputs[1] = analogRead(Pressure2);
    pressureInputs[2] = analogRead(Pressure3);
    pressureInputs[3] = analogRead(Pressure4);
}

void updatePressureRegisters(){
    mb.setIreg(0, pressureInputs[0]);
    mb.setIreg(1, pressureInputs[1]);
    mb.setIreg(2, pressureInputs[2]);
    mb.setIreg(3, pressureInputs[3]);
}

void depressurise(){
    //depressurise the system
    Serial.println("LOG: Depressurising system");
    if(convertToBar(analogRead(Pressure3)) > 0.1){
        setValve(SWITCH, 0);
        setValve(IN, 0);
        setValve(OUT, 1);
        setValve(VENT, 0);
        setValve(SHORT, 1);
        unsigned long startTime = millis();
        while (convertToBar(analogRead(Pressure3)) > 0.1) {
            if (millis() - startTime > 5000) {      //timeout, break loop
                break;
            }
            delay(50);
        }
        setValve(SHORT, 0);
        setValve(OUT, 0);
    }
    else{
        setValve(SWITCH, 0);
        setValve(IN, 0);
        setValve(OUT, 0);
        setValve(VENT, 0);
        setValve(SHORT, 0);
    }
    mb.setIsts(depressuriseStatus, 0);  
}

float convertToBar(float pressure){
    return (pressure-203.53)/0.8248/100;
}