#include <Arduino.h>

//CONSTANTS

//Pin values taken from communication from Chris Rhodes
//5 valves - IN, OUT, SHORT, NN, SWITCH - 42, 44 and 46 unused
//V1 = SWITCH, V2 = IN, V3 = OUT, V4 = NN, V5 = SHORT
//TODO check with James about which valve is which
//const int IN = 0; const int OUT = 1; const int SHORT = 2; const int NN = 3; const int SWITCH = 4;
const int SWITCH = 0; const int IN = 1; const int OUT = 2; const int VENT = 3; const int SHORT = 4;
const int LEDS[] = {32, 34, 36, 38, 40, 42, 44, 46};
const int VALVES[] = {8, 9, 10, 22, 52, 26, 28, 30};

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

const int maxLength = 9; //maximum number of steps in a sequence

//VARIABLES
bool TNcontrol = 0; //TerraNova control - allows valves to be controlled by TTL signals or sequences
bool pressureLog = 1; //log pressure values
bool TTLControl = 0; //TTL control toggle
bool decodeFlag = 0; //flag to decode a sequence
bool execFlag = 0; //flag to execute a sequence
bool simpleTTL = 0; //simple TTL control toggle - unused
bool newStepFlag = 0; //flag to indicate a new step needs loading

float pressureInputs[4] = {0,0,0,0};  //container for pressure values from the analog pins

unsigned long pollTime = DEFPollTime; //time between pressure readings
unsigned long pressureTime = DEFPressureTime; //time required to build pressure before bubbling
size_t currentStepIndex = 0; //current step in the sequence

unsigned long tNow = 0; //current time
unsigned long tPoll = 0; //start time
unsigned long tStepStart = 0; //start time of a step
unsigned long heartBeat = 0; //time of last heartbeat

String sequence = ""; //sequence to be decoded

struct Step {
  char type; //type of step - 'b' for bubble, 'd' for delay, 'n' for alt bubble
  unsigned long length; //length of step in ms
};

Step sequenceSteps[maxLength]; //array to hold the steps in the sequence

Step currentStep = {'e', 1}; //current step in the sequence

Step nextStep = {'e', 1}; //next step in the sequence

bool stepRunning = false; //flag to indicate if a step is currently running

char validTypes[4] = {'b', 'd', 'n', 'e'}; //valid step types

bool started = 0; //flag to indicate if the system has been started

//FUNCTIONS
void declarePins();

void initOutput();

void updateStatus();

void handleSerial();

void handleTTL();

void readPressure();

void setValve(int valve, int state);

void setLED(int led, int state);

void decodeSequence();

//void processStep(char stepType);

void closeValves();

void reset();

void depressurise();

bool isValidType(char type);

bool loadStep();

int convertToBar(int pressure);

void processStep(Step step);

void setup() {
  // put your setup code here, to run once:
  declarePins();
  initOutput(); //set all valves and LEDs to off & flash status LEDs
  tPoll = millis();  //begin polling timer
  heartBeat = millis();
  Serial.begin(9600); //Open serial communication
  started = 0; //set the started flag to false
}

void loop() {
  while (started == 0) {
    // Wait for the system to be started
    if (Serial.available() > 0) {
      char input = Serial.read();
      Serial.print("LOG: Received input: ");
      Serial.println(input);
      if (input == 'S') {
        started = 1;
        Serial.println("LOG: System started");
        heartBeat = millis(); // Update the heartbeat time
      }
    }
  }

  // put your main code here, to run repeatedly:
  tNow = millis();

  updateStatus();

  if(Serial.available()){handleSerial();}

  //if(decodeFlag == 1){decodeSequence();}

  if(execFlag == 1) {
    if (!(currentStep.type == 'e')) {  //if a sequence is running, and is not at the end
      if ((long)tNow - (long)tStepStart >= (long)currentStep.length) { // Check if the current step has been processed
        currentStep = nextStep; // Move the next step to the current step
        processStep(currentStep);
        tStepStart = millis(); // Reset the start time for the next step
        newStepFlag = true; // Set the flag to indicate a new step needs loading
        Serial.println("NEWSEQ"); // Send a new sequence response
      }
    } else {
      execFlag = 0; // Set the machine ready flag to false after processing all steps
      currentStep = {'e', 1}; // Reset the current step
      nextStep = {'e', 1}; // Reset the next step
      Serial.println("ENDSEQ"); // Send an end sequence response
    }
  }

  //if(execFlag == 1){processStoredSequence();}

  if(TTLControl == 1){handleTTL();}

  if((long)(tNow - tPoll) >= (long)pollTime){readPressure(); tPoll = tNow;}

  //Serial.println((long)(tNow - heartBeat) >= (long)DEFHeartbeatTime);

  if((long)(tNow - heartBeat) >= (long)DEFHeartbeatTime) {reset();} //reset if no heartbeat for 5 seconds

}

void declarePins()
{
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

void initOutput(){
  //set all valves to off
  for (int i = 0; i < 8; i++)
  {
    setValve(i, 0);
  }

  //flash status LEDs to show that the system is ready
  /*
  for (int i = 0; i < 8; i++)
  {
    setLED(i, 1);
  }
  */
  // delay(200);

  //set all status LEDs to off
  for (int i = 0; i < 8; i++)
  {
    setLED(i, 0);
  }

  //Initial heartbeat in case the first one is missed due to the initialisation delay
  Serial.println("HEARTBEAT_ACK");  //Heartbeat response
}

void setLED(int led, int state) //sets status LEDs to on or off
{
  digitalWrite(STATUS_LEDS[led], state);
}

void setValve(int valve, int state) //sets the valve & corresponding LED to on or off
{
  digitalWrite(VALVES[valve], state); //set the valve to the desired state
  digitalWrite(LEDS[valve], state);  //set the corresponding valve LED to the same state
  Serial.println("LOG: Valve " + String(valve+1) + " set to " + String(state));
}

void handleSerial()
{
  char input = Serial.read();
  if (isAlpha(input))
  {
    switch(input){
      case 'y': 
        Serial.println("HEARTBEAT_ACK");  //Heartbeat response
        heartBeat = millis(); //update the heartbeat time
        break;
      case 'i':   //Decode a sequence input
        // decodeFlag = 1; // Set the flag to indicate a new sequence is ready to be decoded
        break;
      case 'R':   //Execute the current loaded sequence
        if (TNcontrol == 1){
          if (decodeFlag == 1){
            execFlag = 1; // Set the machine ready flag to true
            tStepStart = millis(); // Set the start time for the first step
            currentStep = nextStep; // Move the next step to the current step
            processStep(currentStep); // Process the first step
            Serial.println("NEWSEQ"); // Send a new sequence response
          }
          else{
            Serial.println("LOG: No steps loaded yet");
          }
        }
        else{
          Serial.println("LOG: Auto control not enabled");
        }
        break;
      case 'M':   //Switch to manual control (TN = 0)
        if(TNcontrol == 0){
          TNcontrol = 1;
          Serial.println("LOG: Switching to Auto control");
        }
        else{
          Serial.println("LOG: Already in Auto control mode");
        }
        break;
      case 'm':   //Switch to manual control (TN = 0)
        if (TNcontrol == 1){
          TNcontrol = 0;
          Serial.println("LOG: Switching to Manual control");
        }
        else{
          Serial.println("LOG: Already in Manual control mode");
        }
        break;
      case 'K':   //Enable pressure logging
        // pressureLog = 1;
        break;
      case 'k':   //Disable pressure logging
        // pressureLog = 0; 
        break;
      case 'T':   //Enable TTL control
        simpleTTL = 1;
        // pressureLog = 1;  //Enable pressure logging when TTL control is enabled
        break;
      case 't':   //Disable TTL control
        simpleTTL = 0;
        break;
      case 's':   //Reset the system
        reset();
        break;
      case 'd':   //Depressurise the system
        depressurise();
        break;
      case 'l':   //Load a step
        if(loadStep()){
          if(newStepFlag == true){
            newStepFlag = false;
            decodeFlag = true;
          }
          else{
            Serial.print("WAITSEQ"); //send a wait sequence response
          }
        }
        else{
          Serial.println("ERROR: Failed to load step");
          decodeFlag = 0;
        }
        break;
      case 'Z':   //Turn on short valve
        setValve(SHORT, 1);
        break;
      case 'z':   //Turn off short valve
        setValve(SHORT, 0);
        break;
      case 'C':   //Turn on INLET valve
        setValve(IN, 1);
        break;
      case 'c':   //Turn off INLET valve
        setValve(IN, 0);
        break;
      case 'V':   //Turn on OUTLET valve
        setValve(OUT, 1);
        break;
      case 'v':   //Turn off OUTLET valve
        setValve(OUT, 0);
        break;
      case 'X':   //Turn on VENT valve
        setValve(VENT, 1);
        break;
      case 'x':   //Turn off VENT valve
        setValve(VENT, 0);
        break;
      case 'H':   //Turn on SWITCH valve
        setValve(SWITCH, 1);
        break;
      case 'h':   //Turn off SWITCH valve
        setValve(SWITCH, 0);
        break;
      default:
        Serial.println("LOG: Invalid input");  //Invalid input
        break;
    }
  }
  else
  {
    Serial.println("LOG: Invalid input, not a letter");  //Invalid input
  }
}

void decodeSequence() //decode the sequence input
{
  if (execFlag == 1) //if a sequence is potentially running, do not load a new sequence
  {
    Serial.println("SEQ: False"); //send a false sequence response
    Serial.println("LOG: Sequence already running, please wait for current sequence to end before loading a new one");
    decodeFlag = 0;
    return; //exit the function to avoid loading new sequence

    /* //ALTERNATE CODE, load new sequence anyway and overwrite the current one
    Serial.println("Sequence already running, cancelling current sequence and loading new one");
    memset(sequenceSteps, 0, sizeof(sequenceSteps));
    currentStepIndex = 0;
    execFlag = false; // Set the machine ready flag to false due to cancelling the current sequence
    closeValves();  // Close all valves for safety
    */
  }
  //decode the sequence
  if (Serial.available() > 0) {
    sequence = Serial.readStringUntil('\n'); // Read the entire input until newline
    decodeFlag = 0; // initialise the decode flag

    size_t i = 0;   // Unsigned int to avoid warning
    int stepIndex = 0;
    while (i < sequence.length()) {
      char stepType = sequence[i];  // Read the step type
      if (isValidType(stepType)) { // Check if the step type is valid
        i++;
        String stepLengthStr = "";
        while (i < sequence.length() && isDigit(sequence[i])) { // Read the step length until another type is found
          stepLengthStr += sequence[i];
          i++;
        }

        if (stepIndex >= maxLength) { // Check if the sequence is too long
          Serial.println("LOG: Sequence too long, only first 9 steps will be executed");
          break;
        }
        else{
          int stepLength = stepLengthStr.toInt(); // Convert the step length to an integer
          sequenceSteps[stepIndex] = {stepType, static_cast<unsigned long>(stepLength)}; // Store the step in the list
          stepIndex++;
        }
      }
      else {
        Serial.println("LOG: Invalid step type in sequence");
        Serial.println("SEQ: False"); //send a false sequence response
        decodeFlag = 0;
        break;
      }
    }
    Serial.println("SEQ: True"); //send a true sequence response
    decodeFlag = 1; // Set the flag to indicate sequence has been decoded
  }
  else
  {
    Serial.println("SEQ: False"); //send a false sequence response
    Serial.println("LOG: Expected sequence input, but none received");
    decodeFlag = 0;
  }
}

void readPressure() //read pressure values from the analog pins
{
  //read pressure values
  pressureInputs[0] = convertToBar(analogRead(Pressure1)); //pressure1 is external
  pressureInputs[1] = convertToBar(analogRead(Pressure2));
  pressureInputs[2] = convertToBar(analogRead(Pressure3));
  pressureInputs[3] = convertToBar(analogRead(Pressure4));

  if (pressureLog == 1){
    //build the pressure return string the way James has been using so far
    String pressureReturn = "P ";
    for (int i = 0; i < sizeof(pressureInputs) / sizeof(pressureInputs[0]); i++)
    {
      pressureReturn += String(pressureInputs[i]);
      pressureReturn += " ";
    }
    for (int i = 0;i < sizeof(VALVES) / sizeof(VALVES[0]); i++)
    {
      pressureReturn += String(digitalRead(VALVES[i]));
      pressureReturn += " ";
    }
    pressureReturn += "C";
    Serial.println(pressureReturn);
  }
}

void closeValves(){ //safety function run at the end of a sequence
  //close all valves
  for (int i = 0; i < sizeof(VALVES) / sizeof(VALVES[0]); i++)
  {
    setValve(i, 0);
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

void reset(){
  //attempt to signal to controller
  Serial.println("System Reset, please reconnect");
  //reset the system
  memset(sequenceSteps, 0, sizeof(sequenceSteps));
  currentStepIndex = 0;
  execFlag = 0;
  decodeFlag = 0;
  simpleTTL = 0;
  TNcontrol = 0;
  // pressureLog = 0;
  //depressurise();
  closeValves();
  tPoll = millis();
  started = 0;
}

void updateStatus(){
  //update status LEDs
  setLED(0, Serial); //LED 1 indicates serial communication
  setLED(1, TNcontrol); //LED 2 indicates TN control
  setLED(2, pressureLog); //LED 3 indicates pressure logging
  setLED(3, digitalRead(VALVES[SHORT])); //LED 4 indicates NN valve state
  //expand with more LEDs when they have a purpose
}

bool isValidType(char type) { // Check if the step type is valid
  for (int i = 0; i < sizeof(validTypes) / sizeof(validTypes[0]); i++) {
    if (type == validTypes[i]) {
      return true;
    }
  }
  return false;
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
    while (convertToBar(analogRead(Pressure3)) > 0.1){
      delay(50);
    }
    setValve(SHORT, 0);
    setValve(OUT, 0);
  }
  else{
    Serial.println("LOG: System already depressurised");
  }
}

int convertToBar(int pressure){
  return (pressure-203.53)/0.8248/100;
}

bool loadstep() {
  if (Serial.available() > 0) {
    char input = Serial.read();
    if (input == -1) {
      Serial.println("Failed to read from Serial");
      return false;
    }
    else if (!isValidType(input)) {
      Serial.println("LOG: Invalid step type");
      return false;
    }
    else{
      nextStep.type = input;
    }
    int length = Serial.parseInt();
    if (length == 0 && Serial.peek() != '0') {
      Serial.println("Failed to parse integer from Serial");
      return false;
    }
    else{
      nextStep.length = length;
    }

    Serial.println("LOG: Loaded step type " + String(nextStep.type) + " with length " + String(nextStep.length));
    return true;
  } else {
    Serial.println("LOG: Expected input, but none received");
    return false;
  }
}

void processStep(Step step){
    switch (step.type) {
    case 'b':
      // Handle bubble step
      setValve(SWITCH, 0);
      setValve(IN, 1);
      setValve(OUT, 1);
      setValve(VENT, 1);
      setValve(SHORT, 0);
      break;
    case 'd':
      // Handle delay step
      setValve(IN, 0);
      setValve(OUT, 0);
      setValve(VENT, 0);
      setValve(SHORT, 0);
      break;
    case 'n':
      // Handle alt bubble step
      Serial.println("LOG: Alt bubble step not implemented");
      break;
    case 'e':
      // Handle end step
      Serial.println("LOG: End of sequence reached");
      break;
    // Add more cases as needed
    default:
      Serial.println("LOG: Unknown step type");
      break;
  }
}