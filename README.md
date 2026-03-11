# RoboHand – Gesture Controlled Robotic Hand

A robotic hand that mirrors human finger movements using computer vision and Arduino controlled servo motors.

---

## Demo

![RoboHand Demo](images/robohand_demo.jpg)

---

## How It Works

1. A webcam captures the user's hand.
2. Python detects finger positions using MediaPipe.
3. Finger states are sent through serial communication.
4. Arduino reads the data.
5. Servo motors move the robotic fingers.

---

## Hardware

- Arduino Uno
- 5x MG90S Servo Motors
- Webcam
- Breadboard + power supply

---

## Software

- Python
- MediaPipe
- OpenCV
- Arduino IDE

---

## Project Structure
ROBOHAND
│
├── arduino
│   └── servocontrol.ino
│
├── python
│   ├── handtrack.py
│   └── hand_landmarker.task
│
├── images
│   ├── robohand_demo.jpg
│   └── wiring_diagram.png
│
└── README.md
