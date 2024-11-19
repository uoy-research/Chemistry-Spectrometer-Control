/********************************************************************************************
* 	    	File:  DAT_MotorControl_v1.ino                                                    *
*		    Version: 1.0.0                                         						                  *
*      	Date: 	 July 18th, 2024 	                                    	  		              *
*       Author:  Daniel A. Taylor.                                                          *
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

UstepperS32 stepper;

/* Motor parameters */
double runCurrent = 100; // Motor run current, % of maximum
double holdCurrent = 10;  // Motor hold current, % of maximum
double brakeCurrent = 10; // Motor brake current, % of maximum
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

void setup(){
  stepper.setup(NORMAL, 200);				     // Initialize uStepper S32
  Serial.begin(9600);
  delay(1000);
  stepper.setCurrent(standby_runCurrent);	       // Set motor run current
  stepper.setHoldCurrent(standby_holdCurrent);   // Set motor hold current
  stepper.setMaxAcceleration(standby_maxAcceleration);  // Set maximum acceleration of motor
  stepper.setMaxDeceleration(standby_maxDeceleration);  // Set maximum deceleration of motor
  stepper.setBrakeMode(FREEWHEELBRAKE);
  stepper.setMaxVelocity(standby_maxVelocity); // Set maximum velocity of motor
  delay(1000);
  Serial.println("Motor ready! First calibrate positions using character 'i'.");
}

void loop() {
  char input;
  input = Serial.read();

  switch(input) {
    case 'u': // Move upwards continuously
      stepper.runContinous(CW);
      Serial.println("Moving upwards!");
      break;

    case 'd': // Move downwards continuously
      stepper.runContinous(CCW);
      Serial.println("Moving downwards!");
      break;

    case 's': // Stop
      stepper.stop(HARD);
      Serial.println("Stop!");
      currentPosition = stepper.getPosition();
      Serial.print("Current position: "); Serial.println(currentPosition);
      break;

    case 'i': // Calibrate positions
      stepper.setCurrent(runCurrent);
      stepper.setHoldCurrent(holdCurrent);
      stepper.setMaxAcceleration(maxAcceleration);
      stepper.setMaxDeceleration(maxDeceleration);
      stepper.setBrakeMode(COOLBRAKE);
      stepper.setMaxVelocity(maxVelocity);
      Serial.println("Finding top position!");
      stepper.moveToEnd(CW, 50, stallSensitivity);
      topPosition  = stepper.getPosition();
      Serial.print("Top position: "); Serial.println(topPosition);
      upPosition = topPosition - 100000;
      setPosition = upPosition;
      stepper.movePosition(setPosition);
      break;

    case 'b': // Sample to down position
      Serial.println("Sample down!");
      downPosition = topPosition - 2475000;
      setPosition = downPosition;
      stepper.movePosition(setPosition);
      break;

    case '6': // Sample to 6 mT position
      Serial.println("6 mT position!");
      sixmTPosition = topPosition - 2475000 + 1284300;
      setPosition = sixmTPosition;
      stepper.movePosition(setPosition);
      break;

    case 't': // Sample to up position
      Serial.println("Sample up!");
      upPosition = topPosition - 100000;
      setPosition = upPosition;
      stepper.movePosition(setPosition);
      break;

    case 'r': // Read position
      currentPosition = stepper.getPosition();
      Serial.print("Current position: "); Serial.println(currentPosition);
      break;

    case 'e': // Shutdown
      Serial.println("Shutting down!");
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
      Serial.println("Moving upwards by 5 mm!");
      stepper.moveAngle(225);
      break;

    case 'z': // Move downwards by 5 mm
      Serial.println("Moving downwards by 5 mm!");
      stepper.moveAngle(-225);
      break;

    case 'm': // Perform field map
      Serial.println("Performing field map!");
      Serial.println("Mapping 75 points in 5 mm intervals.");
      downPosition = topPosition - 2475000;
      setPosition = downPosition;
      stepper.movePosition(setPosition);
      delay(5000);
      mapPositions = 75;
      for (int i = 0; i < mapPositions; i++) {
        delay(5000);
        stepper.moveAngle(225);
        currentPosition = stepper.getPosition();
        Serial.print("Current position: "); Serial.println(currentPosition);
      }
    break;
  }
}