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
const unsigned long baudrate = 115200;

// ModbusSerial object
ModbusSerial mb (MySerial, SlaveId, TxenPin);

unsigned long mbTimeout = 2000; //timeout length for no comms
unsigned long mbLast = 0; //time of last modbus command

bool serialConnected = false;
bool initFlag = false;

// Flag for interrupt handling
bool topInterruptActive = false;

const int intPin1 = 10; // This is the interrupt pin for the uStepper S32
const int intPin2 = 9; // This is the interrupt pin for the uStepper S32

// Add these global variables to track last set values
int lastSpeed = 0;
int lastAccel = 0;
bool lastBrakeMode = false;
double lastRunCurrent = 0;
double lastHoldCurrent = 0;

// Add a simple command buffer
#define CMD_BUFFER_SIZE 5
struct Command {
  char type;
  int32_t value;
  bool active;
};
Command cmdBuffer[CMD_BUFFER_SIZE];
uint8_t cmdBufferHead = 0;
uint8_t cmdBufferTail = 0;

// Add a function to queue commands
bool queueCommand(char type, int32_t value) {
  uint8_t nextHead = (cmdBufferHead + 1) % CMD_BUFFER_SIZE;
  if (nextHead == cmdBufferTail) return false; // Buffer full
  
  cmdBuffer[cmdBufferHead].type = type;
  cmdBuffer[cmdBufferHead].value = value;
  cmdBuffer[cmdBufferHead].active = true;
  cmdBufferHead = nextHead;
  return true;
}

// Process commands from buffer in main loop
void processCommandBuffer() {
  if (cmdBufferHead == cmdBufferTail) return; // Buffer empty
  
  if (!cmdBuffer[cmdBufferTail].active) {
    cmdBufferTail = (cmdBufferTail + 1) % CMD_BUFFER_SIZE;
    return;
  }
  
  // Process the command
  handleInput(cmdBuffer[cmdBufferTail].type);
  
  // Mark as processed
  cmdBuffer[cmdBufferTail].active = false;
  cmdBufferTail = (cmdBufferTail + 1) % CMD_BUFFER_SIZE;
}

// Add these global variables for calibration state machine
enum CalibrationState {
  CAL_IDLE,
  CAL_MOVING_UP,
  CAL_FOUND_TOP,
  CAL_RETURNING_HOME
};

CalibrationState calibrationState = CAL_IDLE;
unsigned long lastCalibrationTime = 0;

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
      noSpeed(); //Apply settings
      serialConnected = false;
    }  
  }  

  mb.task(); // Modbus task, call early

  // Update current position
  getCurrentPosition();
  
  // Process command buffer
  processCommandBuffer();
  
  // Handle non-blocking calibration state machine
  handleCalibration();
  
  // Handle interrupts
  //handleInterrupts();

  // Direct command handling for calibration
  if (mb.coil(1) == 1) {
    char input = mb.Hreg(2);
    
    // Handle calibration command directly
    if (input == 'c') {
      // Reset calibration state
      mb.setCoil(2, 0); // Set calibration flag to false
      
      // Force motor to be enabled with proper settings
      stepper.setCurrent(runCurrent);
      stepper.setHoldCurrent(holdCurrent);
      stepper.setMaxAcceleration(maxAcceleration);
      stepper.setMaxDeceleration(maxDeceleration);
      stepper.setBrakeMode(COOLBRAKE);
      stepper.setMaxVelocity(maxVelocity/4);
      
      // Start the calibration state machine
      calibrationState = CAL_IDLE;
      initFlag = 1;
      
      // Reset command flag
      mb.setCoil(1, 0);
      
      // Debug output
      mb.setHreg(13, 0xC0DE); // Magic number to indicate calibration command received
    } else {
      // Queue other commands
      queueCommand(input, getTargetPosition());
      mb.setHreg(2, 0);
      mb.setCoil(1, 0); // Reset command flag
    }
  }
  else if (mb.coil(2) == 1) {
    int32_t currentPos = combine(mb.Hreg(5), mb.Hreg(6));
    int32_t desiredPos = combine(mb.Hreg(3), mb.Hreg(4));
    if (currentPos == desiredPos) {
      mb.setCoil(1, 0);
    }
  }
}

// Add a non-blocking calibration state machine
void handleCalibration() {
  // Only process if we're in calibration mode
  if (calibrationState == CAL_IDLE && !initFlag) {
    return;
  }
  
  // State machine for calibration
  switch (calibrationState) {
    case CAL_IDLE:
      if (initFlag) {
        // Start calibration - make sure motor is running at proper speed
        stepper.setCurrent(runCurrent);
        stepper.setHoldCurrent(holdCurrent);
        stepper.setMaxAcceleration(maxAcceleration);
        stepper.setMaxDeceleration(maxDeceleration);
        stepper.setBrakeMode(COOLBRAKE);
        stepper.setMaxVelocity(maxVelocity/4);
        
        // Start moving up
        stepper.moveSteps(10000000); // Move up until we hit the limit switch
        calibrationState = CAL_MOVING_UP;
        lastCalibrationTime = millis();
        
        // Debug output - make sure to write to register 13
        mb.setHreg(13, 0xCAFE); // Magic number to indicate calibration started
      }
      break;
      
    case CAL_MOVING_UP:
      // Check if we've hit the top limit switch
      if (topInterruptActive) {
        topInterruptActive = false;
        //stepper.stop(HARD);
        topPosition = stepper.getPosition();
        upPosition = topPosition - 100000; // Simplified - just 100000 steps below top
        setTopPosition(upPosition);
        
        // Wait a moment before continuing
        lastCalibrationTime = millis();
        calibrationState = CAL_FOUND_TOP;
        
        // Debug output
        mb.setHreg(11, 0xBEEF); // Magic number to indicate top found
      }
      
      // Safety timeout - if we've been moving too long, stop
      if (millis() - lastCalibrationTime > 10000) {
        stepper.stop(HARD);
        calibrationState = CAL_IDLE;
        initFlag = 0;
        
        // Debug output
        mb.setHreg(11, 0xDEAD); // Magic number to indicate timeout
      }
      break;
      
    case CAL_FOUND_TOP:
      // Small delay to let things settle
      if (millis() - lastCalibrationTime > 0 && digitalRead(intPin1) == LOW) {
        // Return to home position (10000 steps below top)
        fastSpeed();
        stepper.movePosition(upPosition);
        setPosition = upPosition;
        setTargetPosition(0);
        calibrationState = CAL_RETURNING_HOME;
        lastCalibrationTime = millis();
      }
      break;
      
    case CAL_RETURNING_HOME:
      // Check if we've reached home position
      if (abs(stepper.getPosition() - upPosition) < 100 || 
          millis() - lastCalibrationTime > 5000) {
        // Calibration complete
        mb.setCoil(2, 1); // Set calibration flag to true
        calibrationState = CAL_IDLE;
        initFlag = 0;
      }
      break;
  }
}

// Modify the handleInput function to handle 'c' command
void handleInput(char input) {
  switch(input) {
    case 'x': // Move to position - optimized
      // Only update speed parameters if needed
      setCustomSpeed();
      
      // Get target position once
      setPosition = getTargetPosition();
      
      // Apply limits more efficiently
      if (setPosition > upPosition) {
        setPosition = upPosition;
      } else if (setPosition < downPosition) {
        setPosition = downPosition;
      }
      
      // Move to position
      stepper.movePosition(setPosition);
      break;
      
    case 'c': // Calibrate - non-blocking
      // This is now handled directly in the loop
      // but we keep it here for completeness
      mb.setCoil(2, 0); // Set calibration flag to false
      fastSpeed();
      stepper.setMaxVelocity(maxVelocity/4);
      
      // Start the calibration state machine
      calibrationState = CAL_IDLE;
      initFlag = 1;
      break;
      
    case 'q': // +50mm
      stepper.moveSteps(50 * mmSteps);
      break;
      
    case 'w': // +10mm
      stepper.moveSteps(10 * mmSteps);
      break;
      
    case 'd': // +1mm
      stepper.moveSteps(1 * mmSteps);
      break;
      
    case 'r': // -1mm
      stepper.moveSteps(-1 * mmSteps);
      break;
      
    case 'f': // -10mm
      stepper.moveSteps(-10 * mmSteps);
      break;
      
    case 'v': // -50mm
      stepper.moveSteps(-50 * mmSteps);
      break;
      
    case 's': // Stop
      stepper.stop(HARD);
      break;
  }
}

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

void topInterrupt() {
  topInterruptActive = true;
  stepper.stop(HARD);
  fastSpeed();
  while(digitalRead(intPin1) == HIGH){
    stepper.moveAngle(-1);
  }
  stepper.stop(HARD);
  //downPosition = stepper.getPosition();
  noSpeed();
}

// Handle interrupts in main loop
void handleInterrupts() {
  if (topInterruptActive) {
    // Handle top interrupt without blocking
    fastSpeed();
    if (digitalRead(intPin1) == HIGH) {
      stepper.moveAngle(-1);
    } else {
      topInterruptActive = false;
      topPosition = stepper.getPosition();
      
      if (initFlag == 1){
        topPosition = stepper.getPosition();
        
        //Serial.print("Top position: "); Serial.println(topPosition);
        upPosition = topPosition - 100000;
        setTopPosition(upPosition);
        downPosition = topPosition - 2475000; // define down pos once calibrated
        setPosition = upPosition;
        delay(10);
        setTargetPosition(upPosition);
        mb.setCoil(1, 1); // New Command - Move to setPosition
        mb.setHreg(2, 'x'); // Reset command register
        mb.setCoil(2, 1); // Set calibration flag to true
        initFlag = 0;
      }
      noSpeed();
    }
  }
}

void botInterrupt(){
  stepper.stop(HARD);
  fastSpeed();
  while(digitalRead(intPin2) == HIGH){
    stepper.moveAngle(1);
  }
  stepper.stop(HARD);
  //downPosition = stepper.getPosition();
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

// Optimize the getCurrentPosition function
void getCurrentPosition() {
  static int32_t lastReportedPosition = 0;
  int32_t currentPosition = stepper.getPosition();
  
  // Only update registers if position has changed
  if (currentPosition != lastReportedPosition) {
    int16_t high;
    uint16_t low;
    disassemble(currentPosition, high, low);
    mb.setHreg(5, static_cast<uint16_t>(high));
    mb.setHreg(6, low);
    lastReportedPosition = currentPosition;
  }
}

// Add a non-blocking velocity reporting function
void updateVelocityRegisters() {
  // Get current velocity - use position difference instead of getVelocity()
  static int32_t lastPos = 0;
  static unsigned long lastTime = 0;
  unsigned long currentTime = millis();
  int32_t currentPos = stepper.getPosition();
  
  // Calculate velocity only if enough time has passed
  if (currentTime - lastTime >= 50) { // 50ms minimum interval
    // Calculate velocity in steps per second
    float timeDiff = (currentTime - lastTime) / 1000.0; // Convert to seconds
    int32_t posDiff = currentPos - lastPos;
    int32_t velocity = 0;
    
    if (timeDiff > 0) {
      velocity = posDiff / timeDiff;
    }
    
    // Disassemble into high and low words
    int16_t high;
    uint16_t low;
    disassemble(velocity, high, low);
    
    // Update velocity registers (11-12)
    mb.setHreg(11, static_cast<uint16_t>(high));
    mb.setHreg(12, low);
    
    // Update last values
    lastPos = currentPos;
    lastTime = currentTime;
  }
}

void addCoils(){
  mb.addHreg(2, 0);  // Command register
  mb.addHreg(3, 0);  // Target position high word
  mb.addHreg(4, 0);  // Target position low word
  mb.addHreg(5, 0);  // Current position high word
  mb.addHreg(6, 0);  // Current position low word
  mb.addHreg(7, 0);  // Top position high word
  mb.addHreg(8, 0);  // Top position low word
  mb.addHreg(9, 0);  // Motor speed setting
  mb.addHreg(10, 0); // Motor acceleration setting
  mb.addHreg(11, 0); // Motor velocity high word (read-only)
  mb.addHreg(12, 0); // Motor velocity low word (read-only)
  mb.addHreg(13, 0); // Debug register
  mb.addCoil(1, 0);  // Command flag
  mb.addCoil(2, 0);  // Calibration flag
  mb.addCoil(3, 0);  // Connection test flag
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

// Replace setCustomSpeed() with this optimized version
void setCustomSpeed() {
  // Only update parameters that have changed
  uint16_t newSpeed = mb.Hreg(9);
  uint16_t newAccel = mb.Hreg(10);
  
  bool needUpdate = false;
  
  if (lastRunCurrent != runCurrent) {
    stepper.setCurrent(runCurrent);
    lastRunCurrent = runCurrent;
    needUpdate = true;
  }
  
  if (lastHoldCurrent != holdCurrent) {
    stepper.setHoldCurrent(holdCurrent);
    lastHoldCurrent = holdCurrent;
    needUpdate = true;
  }
  
  if (newAccel != lastAccel) {
    stepper.setMaxAcceleration(newAccel);
    stepper.setMaxDeceleration(newAccel);
    lastAccel = newAccel;
    needUpdate = true;
  }
  
  if (!lastBrakeMode) {
    stepper.setBrakeMode(COOLBRAKE);
    lastBrakeMode = true;
    needUpdate = true;
  }
  
  if (newSpeed != lastSpeed) {
    stepper.setMaxVelocity(newSpeed);
    lastSpeed = newSpeed;
    needUpdate = true;
  }
  
  // If nothing changed, don't waste time with updates
  if (needUpdate) {
    // Small delay only if parameters were actually changed
    delayMicroseconds(5);
  }
}

void noSpeed() {
  stepper.setCurrent(standby_runCurrent);
  stepper.setHoldCurrent(standby_holdCurrent);
  stepper.setMaxAcceleration(standby_maxAcceleration);
  stepper.setMaxDeceleration(standby_maxDeceleration);
  stepper.setBrakeMode(FREEWHEELBRAKE);
  stepper.setMaxVelocity(standby_maxVelocity);

  stepper.setMaxVelocity(0);
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

// Add acceleration profiles for different movement types
void setAccelerationProfile(uint8_t profile) {
  switch(profile) {
    case 1: // Fast long movements
      mb.setHreg(9, 6500);  // Max speed
      mb.setHreg(10, 23250); // Max accel
      break;
    case 2: // Medium precision movements
      mb.setHreg(9, 4000);  // Medium speed
      mb.setHreg(10, 23250); // Max accel
      break;
    case 3: // Slow precise movements
      mb.setHreg(9, 2000);  // Slow speed
      mb.setHreg(10, 23250);  // Max accel
      break;
  }
  setCustomSpeed();
}