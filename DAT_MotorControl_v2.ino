/********************************************************************************************
* 	    	File:  DAT_MotorControl_v2.ino                                                    *
*		    Version: 1.0.0                                         						                  *
*      	Date: 	 July 18th, 2024 	                                    	  		              *
*       Author:  Daniel A. Taylor, Jonathan Hedges                                                          *
*  Description:                                                                             *
*                                                                                           *
*                                                                                           *
*********************************************************************************************
*	(C) 2023                                                                                  *
*                                                                                           *
*	uStepper ApS                                                                              *
*	www.ustepper.com                                                                          *
*	administration@ustepper.com                                                               *
*                                                                                           *
*	The code contained in this file is released under the following open source license:      *
*                                                                                           *
*			Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International               *
*                                                                                           *
* 	The code in this file is provided without warranty of any kind - use at own risk!       *
* 	neither uStepper ApS nor the author, can be held responsible for any damage             *
* 	caused by the use of the code contained in this file !                                  *
*                                                                                           *
*                                                                                           *
********************************************************************************************/

#include <UstepperS32.h>
#include <Arduino.h>
#include <ModbusSerial.h>

UstepperS32 stepper;

#define MySerial Serial // define serial port used, Serial most of the time, or Serial1, Serial2 ... if available

const int TxenPin = -1; // -1 disables the feature, change that if you are using an RS485 driver, this pin would be connected to the DE and /RE pins of the driver.
const byte SlaveId = 11;
const int mmSteps = 6400; // steps per mm

/* Motor parameters */
double runCurrent = 100; // Motor run current, % of maximum
double holdCurrent = 10;  // Motor hold current, % of maximum
double brakeCurrent = 100; // Motor brake current, % of maximum
float maxAcceleration = 23250; // Motor acceleration, steps/s^2
float maxDeceleration = 23250; // Motor deceleration, steps/s^2
int maxVelocity = 6500; // Motor maximum velocity, steps/s
int stallSensitivity = 0; // Stall sensitivity, arbitrary (-64 - +63), lower number = higher sensitivity

/* Motor standby parameters */
double standby_runCurrent = 0; // Standby run current, % of maximum
double standby_holdCurrent = 0; // Standby hold current, % of maximum
float standby_maxAcceleration = 0;  // Standby acceleration, steps/s^2
float standby_maxDeceleration = 0;  // Standby deceleration, steps/s^2
int standby_maxVelocity = 0;  // Standby maximum velocity, steps/s

/* Position definitions */
int bottomPosition;
int topPosition;
int currentPosition;
int downPosition;
int sixmTPosition;
int upPosition;
int setPosition;
int mapPositions;

/* Added params */
const unsigned long baudrate = 9600;

// ModbusSerial object
ModbusSerial mb (MySerial, SlaveId, TxenPin);

unsigned long mbTimeout = 2000; //timeout length for no comms
unsigned long mbLast = 0; //time of last modbus command

bool serialConnected = false;
bool initFlag = false;

const int intPin1 = 10; // This is the interrupt pin for the uStepper S32
const int intPin2 = 9; // This is the interrupt pin for the uStepper S32

// Steps/mm= 6400

// # +--------------------------+---------+-----------------------------------------+
// # |         Coil/reg         | Address |                 Purpose                 |
// # +--------------------------+---------+-----------------------------------------+
// # | Command Register         | 2       | Holds the command instruction           |
// # | Desired Position Reg     | 3-4     | two hold registers used to contain the  |
// # | ,                        | ,       | desired motor position                  |
// # | Current Position Reg     | 5-6     | two hold registers used to contain the  |
// # | ,                        | ,       | current motor position                  |
// # | Top Position Reg         | 7-8     | two hold registers used to contain the  |
// # | ,                        | ,       | top motor position                      |
// # | Speed Reg                | 9       | Contains the speed of the motor         |
// # | Accel Reg                | 10      | Contains the max accel and deccel       |
// # | Command Coil             | 1       | Flag to show if command is waiting      |                
// # | Calibration Coil         | 2       | Flag to show if motor is calibrated     |
// # | Init Coil                | 3       | Flag to show if serial comms established|                
// # +--------------------------+---------+-----------------------------------------+

void handleInput(char input);
void addCoils();

void setup(){
  stepper.setup(NORMAL, 200);				     // Initialize uStepper S32
  MySerial.begin(baudrate);
  
  mb.config(baudrate); // Set up modbus communication
  mb.setAdditionalServerData("uStepper S32"); // Give it a name

  addCoils(); // Add coils and registers to modbus

  pinMode(intPin1, INPUT_PULLUP);
  pinMode(intPin2, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(intPin1), topInterrupt, RISING);
  attachInterrupt(digitalPinToInterrupt(intPin2), botInterrupt, RISING);

  delay(500);
  stepper.setCurrent(standby_runCurrent);	       // Set motor run current
  stepper.setHoldCurrent(standby_holdCurrent);   // Set motor hold current
  stepper.setMaxAcceleration(standby_maxAcceleration);  // Set maximum acceleration of motor
  stepper.setMaxDeceleration(standby_maxDeceleration);  // Set maximum deceleration of motor
  stepper.setBrakeMode(FREEWHEELBRAKE);
  stepper.setMaxVelocity(standby_maxVelocity); // Set maximum velocity of motor
  delay(500);
  //Serial.println("Motor ready! First calibrate positions using character 'i'.");

  mb.setHreg(9, 4000);
  mb.setHreg(10, 23250);
}

void loop() {
  if (MySerial.available() > 0) { mbLast = millis(); serialConnected = true; }//update serial connection state
  else{
    if ((long)(millis() - mbLast) > (long)(mbTimeout)){//If no serial activity for longer than mbTimeout, declare disconnection
      stepper.stop(HARD);
      mb.setCoil(2, 0); //Reset init flag
      mb.setHreg(9, 4000); //Reset speed and accel
      mb.setHreg(10, 23250);
      setCustomSpeed(); //Apply settings
      serialConnected = false;
      }  
    }  

  mb.task(); // Modbus task, call early

  getCurrentPosition(); // Get current position

  //char input = MySerial.read();
  if (initFlag == false) {
    uint16_t input = mb.Hreg(2);
    if (input != 0) {
      handleInput(static_cast<char>(input));
      mb.setHreg(2, 0);
    }
  }
  else if (mb.coil(2) == 1) {
    int32_t currentPos = combine(mb.Hreg(5), mb.Hreg(6));
    int32_t desiredPos = combine(mb.Hreg(3), mb.Hreg(4));
    if (currentPos == desiredPos) {
        noSpeed();
    }
  }
}

void handleInput(char input) {

  switch(input) {

/*    These functions are blocking, so they are not suitable for use with Modbus.
    case 'u': // Move upwards continuously
      stepper.runContinous(CW);
      //Serial.println("Moving upwards!");
      break;

    case 'd': // Move downwards continuously
      stepper.runContinous(CCW);
      //Serial.println("Moving downwards!");
      break;
*/
    case 's': // Stop
      stepper.stop(HARD);
      //Serial.println("Stop!");
      currentPosition = stepper.getPosition();
      //Serial.print("Current position: "); Serial.println(currentPosition);
      break;

    case 'i': // Calibrate positions
      stepper.setCurrent(runCurrent);
      stepper.setHoldCurrent(holdCurrent);
      stepper.setMaxAcceleration(maxAcceleration);
      stepper.setMaxDeceleration(maxDeceleration);
      stepper.setBrakeMode(COOLBRAKE);
      stepper.setMaxVelocity(maxVelocity/4);
      //Serial.println("Finding top position!");

      
      stepper.moveToEnd(CW, 50, stallSensitivity);  //This is blocking and needs to be changed
      mbLast = millis(); //update last comm time

      topPosition  = stepper.getPosition();
      //Serial.print("Top position: "); Serial.println(topPosition);
      upPosition = topPosition - 100000;
      downPosition = topPosition - 2475000; // define down pos once calibrated
      setPosition = upPosition;
      stepper.movePosition(setPosition);
      mb.setCoil(2, 1); // Set calibration flag to true
      break;

    case 'b': // Sample to down position
      //Serial.println("Sample down!");
      setCustomSpeed();
      downPosition = topPosition - 100000 - 2332160;
      setPosition = downPosition;
      stepper.movePosition(setPosition);
      break;

    case '6': // Sample to 6 mT position
      //Serial.println("6 mT position!");
      sixmTPosition = topPosition - 2475000 + 1284300;
      setPosition = sixmTPosition;
      stepper.movePosition(setPosition);
      break;

    case 't': // Sample to up position
      //Serial.println("Sample up!");
      setCustomSpeed();
      upPosition = topPosition - 100000;
      setPosition = upPosition;
      stepper.movePosition(setPosition);
      break;

/*  Now handled by modbus registers
    case 'r': // Read position
      currentPosition = stepper.getPosition();
      //Serial.print("Current position: "); Serial.println(currentPosition);
      break;
*/

    case 'e': // Shutdown
      //Serial.println("Shutting down!");
      upPosition = topPosition - 100000;
      setPosition = upPosition;
      stepper.movePosition(setPosition);
      delay(10000);
      stepper.setCurrent(standby_runCurrent);
      stepper.setHoldCurrent(standby_holdCurrent);
      stepper.setMaxAcceleration(standby_maxAcceleration);
      stepper.setMaxDeceleration(standby_maxDeceleration);
      stepper.setBrakeMode(FREEWHEELBRAKE);
      stepper.setMaxVelocity(standby_maxVelocity);
      break;

    case 'y': // Move upwards by 5 mm
      //Serial.println("Moving upwards by 5 mm!");
      slowSpeed();
      stepper.moveAngle(225);
      break;

    case 'z': // Move downwards by 5 mm
      //Serial.println("Moving downwards by 5 mm!");
      slowSpeed();
      stepper.moveAngle(-225);
      break;

    case 'm': // Perform field map
      //Serial.println("Performing field map!");
      //Serial.println("Mapping 75 points in 5 mm intervals.");
      downPosition = topPosition - 2475000;
      setPosition = downPosition;
      stepper.movePosition(setPosition);
      delay(5000);
      mapPositions = 75;
      for (int i = 0; i < mapPositions; i++) {
        delay(5000);
        stepper.moveAngle(225);
        currentPosition = stepper.getPosition();
        //Serial.print("Current position: "); Serial.println(currentPosition);
      }
      break;
    case 'x': // Move to position
      //Serial.println("Moving to position!");
      //stepper.setCurrent(runCurrent);
      //stepper.setHoldCurrent(holdCurrent);
      //stepper.setMaxAcceleration(maxAcceleration);
      //stepper.setMaxDeceleration(maxDeceleration);
      //stepper.setBrakeMode(COOLBRAKE);
      //stepper.setMaxVelocity(maxVelocity);
      setCustomSpeed();
      setPosition = getTargetPosition();
      setPosition = min(upPosition, (upPosition - setPosition));
      setPosition = max(downPosition, setPosition);
      stepper.movePosition(setPosition);
      break;
    case 'c': // Calibrate
      mb.setCoil(2, 0); // Set calibration flag to false
      fastSpeed();
      stepper.setMaxVelocity(maxVelocity/4);
      stepper.moveSteps(10000000);
      initFlag = 1;
      break;
    case 'u': // Slow ascent
      stepper.setCurrent(runCurrent);
      stepper.setHoldCurrent(holdCurrent);
      stepper.setMaxAcceleration(maxAcceleration/2);
      stepper.setMaxDeceleration(maxDeceleration);
      stepper.setBrakeMode(COOLBRAKE);
      stepper.setMaxVelocity(maxVelocity/2);
      //setPosition = upPosition;
      stepper.moveSteps(10000000);
      break;
    case 'q': // Large step up
      setCustomSpeed();
      stepper.moveSteps(50*mmSteps);
      break;
    case 'w': // Medium step up
      setCustomSpeed();
      stepper.moveSteps(10*mmSteps);
      break;
    case 'd': // Small step up
      setCustomSpeed();
      stepper.moveSteps(mmSteps);
      break;
    case 'r': // Small step down
      setCustomSpeed();
      stepper.moveSteps(-1 * mmSteps);
      break;
    case 'f': // Medium step down
      setCustomSpeed();
      stepper.moveSteps(-10 * mmSteps);
      break;
    case 'v': // Large step down
      setCustomSpeed();
      stepper.moveSteps(-50 * mmSteps);
      break;
    default:
      //Serial.println("LOG: Invalid input");
      break;
  }
}

void topInterrupt(){
  stepper.stop(HARD);
  fastSpeed();
  while(digitalRead(intPin1) == HIGH){
    stepper.moveAngle(-1);
  }
  stepper.stop(HARD);
  //topPosition  = stepper.getPosition();
  //upPosition = topPosition - 100000;
  if (initFlag == 1){
    topPosition  = stepper.getPosition();
    
    //Serial.print("Top position: "); Serial.println(topPosition);
    upPosition = topPosition - 100000;
    setTopPosition(upPosition);
    downPosition = topPosition - 2475000; // define down pos once calibrated
    setPosition = upPosition;
    delay(10);
    setTargetPosition(0);
    mb.setHreg(2, 'x'); // Reset command register
    mb.setCoil(2, 1); // Set calibration flag to true
    initFlag = 0;
  }
  noSpeed();
}

void botInterrupt(){
  stepper.stop(HARD);
  fastSpeed();
  while(digitalRead(intPin2) == HIGH){
    stepper.moveAngle(1);
  }
  stepper.stop(HARD);
  downPosition = stepper.getPosition();
  noSpeed();
}

int32_t getTargetPosition(){
  uint16_t high = mb.Hreg(3);
  uint16_t low = mb.Hreg(4);
  return combine(high, low);
}

void setTargetPosition(int32_t targetPosition){
  int16_t high;
  uint16_t low;
  disassemble(targetPosition, high, low);
  mb.setHreg(3, static_cast<uint16_t>(high));
  mb.setHreg(4, low);
}

void getCurrentPosition(){
  int32_t currentPosition = stepper.getPosition();  // Get current position
  int16_t high;
  uint16_t low; // Declare high and low words
  disassemble(currentPosition, high, low);  // Disassemble current position
  mb.setHreg(5, static_cast<uint16_t>(high)); 
  mb.setHreg(6, low);  // Add low word to input register 6
}

void addCoils(){
  mb.addHreg(2, 0);
  mb.addHreg(3, 0);
  mb.addHreg(4, 0);
  mb.addHreg(5, 0);
  mb.addHreg(6, 0);
  mb.addHreg(7, 0);
  mb.addHreg(8, 0);
  mb.addHreg(9, 0);
  mb.addHreg(10, 0);
  mb.addCoil(1, 0);
  mb.addCoil(2, 0);
  mb.addCoil(3, 0);
}

// Doing high word first
// Function to combine two uint16_t into a signed 32-bit int
int32_t combine(int16_t high, uint16_t low) {
    return (static_cast<int32_t>(high) << 16) | low;
}

// Function to disassemble a signed 32-bit int into two uint16_t
void disassemble(int32_t combined, int16_t &high, uint16_t &low) {
    high = static_cast<int16_t>(combined >> 16);
    low = static_cast<uint16_t>(combined & 0xFFFF);
}

void setTopPosition(int32_t topPosition){
  int16_t high;
  uint16_t low;
  disassemble(topPosition, high, low);
  mb.setHreg(7, static_cast<uint16_t>(high));
  mb.setHreg(8, low);
}

void noSpeed() {
  stepper.setCurrent(standby_runCurrent);
  stepper.setHoldCurrent(standby_holdCurrent);
  stepper.setMaxAcceleration(standby_maxAcceleration);
  stepper.setMaxDeceleration(standby_maxDeceleration);
  stepper.setBrakeMode(FREEWHEELBRAKE);
  stepper.setMaxVelocity(standby_maxVelocity);
}

void fastSpeed() {
  stepper.setCurrent(runCurrent);
  stepper.setHoldCurrent(holdCurrent);
  stepper.setMaxAcceleration(maxAcceleration);
  stepper.setMaxDeceleration(maxDeceleration);
  stepper.setBrakeMode(COOLBRAKE);
  stepper.setMaxVelocity(maxVelocity);
}

void slowSpeed() {
  stepper.setCurrent(runCurrent);
  stepper.setHoldCurrent(holdCurrent);
  stepper.setMaxAcceleration(maxAcceleration/2);
  stepper.setMaxDeceleration(maxDeceleration);
  stepper.setBrakeMode(COOLBRAKE);
  stepper.setMaxVelocity(maxVelocity/2);
}

void setCustomSpeed() {
  stepper.setCurrent(runCurrent);
  stepper.setHoldCurrent(holdCurrent);
  stepper.setMaxAcceleration(mb.Hreg(10));
  stepper.setMaxDeceleration(mb.Hreg(10));
  stepper.setBrakeMode(COOLBRAKE);
  stepper.setMaxVelocity(mb.Hreg(9));
}