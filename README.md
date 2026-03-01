# CovertIndustries - TankAI

Autonomous-capable Raspberry Pi Tank with:

- Manual WASD control
- Ultrasonic collision prevention
- YOLOv8 object detection
- Live camera overlay
- Automatic braking system

---

## Hardware

- Raspberry Pi 5
- Freenove Tank V2.0
- HC-SR04 Ultrasonic Sensor
- OV5647 Pi Camera

---

## Controls

| Key | Action |
|-----|--------|
| W | Forward |
| S | Backward |
| A | Turn Left |
| D | Turn Right |
| Q | Quit |

---

## Setup

```bash
python3 -m venv tankai --system-site-packages
source tankai/bin/activate
pip install ultralytics opencv-python gpiozero lgpio
python3 tank_ai.py
