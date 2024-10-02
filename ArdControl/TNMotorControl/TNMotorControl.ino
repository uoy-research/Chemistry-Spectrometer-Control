#include <Arduino.h>
#include "HAL/spi.h"
#include "HAL/gpio.h"
#include "peripherals/TMC5130.h"
#include "peripherals/TLE5012B.h"
#include "HAL/timer.h"
#include "callbacks.h"
#include "utils/dropin.h"
#include <UstepperS32.h>

const unsigned long DEFHeartBeatTime = 5000;
const int maxRPM = 500;
const int maxAcc = 2000;
const int inverted = 0;

int topPosition = 0;
bool calibrationFlag = false;
bool moveFlag = false;
UstepperS32 motor;

void setup(){
    Serial.begin(9600);
    motor.setup(mode = NORMAL, stepsPerRevolution = 200, pTerm = 10, iTerm = 0.2, dTerm = 0, dropinStepSize = 16, setHome = true, invert = inverted, runCurrent = 50, holdCurrent = 30);
    motor.setBrakeMode(COOLBRAKE);
    motor.setMaxAcceleration(maxAcc); //use an acceleration of 2000 fullsteps/s^2
    motor.setRPM(maxRPM);
    tStart = millis();  //begin polling timer
    heartBeat = millis();
    started = 0;
}

void loop(){
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

  tNow = millis();

  if(Serial.available()){handleSerial();}

  if(calibrationFlag == true && motor.getState(STANDSTILL) == true) {setHome();} //set the home position when calibration is finished

  if((long)(tNow - heartBeat) >= (long)DEFHeartbeatTime) {reset();} //reset if no heartbeat for 5 seconds
}

void handleSerial(){
  char input = Serial.read();
  if (isAlpha(input))
  {
    switch(input)
    {
      case 's':
        Serial.println("LOG: Shutting down motor");
        reset();
        break;
      case 'y':
        Serial.println("HEARTBEATACK");
        heartBeat = millis();
        break;
      case 'u':
        Serial.println("LOG: Moving continusously up");
        break;
      case 'c':
        Serial.println("LOG: Calibrating");
        motor.checkOritentation(10);
        motor.moveToEnd(dir=CW, rpm=50, threshold=4, timeOut=100000);
        calibrationFlag = true;
        break;
      default:
        Serial.println("LOG: Invalid input");
        break;
    }
  }
}

void reset(){ //called when error - stop hard
  motor.stop(HARD);
  started = 0;
}

void setHome(){
  calibrationFlag = false;
  topPosition = motor.getPosition();
}