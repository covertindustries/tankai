# CovertIndustries - TankAI

Autonomous-capable Raspberry Pi Tank with:

- Manual WASD control
- Ultrasonic collision prevention
- YOLOv8 object detection (e.g. dog)
- Event recording when a dog is in scene
- Optional WhatsApp notification when a recording is saved (free via CallMeBot)
- Live camera overlay and automatic braking

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
pip install -r requirements.txt
python3 tank_ai.py
```

---

## WhatsApp notifications (optional, free)

When a dog recording is saved, the app can send you a WhatsApp message (e.g. *"Tank AI: dog recording saved — dog_2025-03-02_14-30-45.avi"*). This uses **CallMeBot**, which is free and does not require Twilio.

1. **Get an API key**  
   - Add **+34 644 66 32 62** to your phone contacts.  
   - In WhatsApp, send this contact: **"I allow callmebot to send me messages"**.  
   - You’ll receive a reply with your API key.

2. **Configure**  
   Set these in your environment (or copy `.env.example` to `.env` and fill in; load with `python-dotenv` if you use it):

   - `CALLMEBOT_WHATSAPP_APIKEY` — the key from step 1  
   - `CALLMEBOT_WHATSAPP_PHONE` — your number in E.164 (e.g. `+15551234567`)

   Example:

   ```bash
   export CALLMEBOT_WHATSAPP_APIKEY="your_api_key_here"
   export CALLMEBOT_WHATSAPP_PHONE="+15551234567"
   ```

3. **Run**  
   If both are set, you’ll get a WhatsApp message each time a dog recording is saved. If either is unset, recordings still save to `recordings/`; notifications are simply skipped.

Reference: [CallMeBot WhatsApp API](https://www.callmebot.com/blog/free-api-whatsapp-messages/).

---

## Project layout

- `tank_ai.py` — main script (camera, YOLO, motors, recording, keyboard).
- `notifications/` — notification backends (e.g. WhatsApp via CallMeBot).
- `recordings/` — saved dog clips (created automatically).
- `.env.example` — example env vars for WhatsApp (copy and set values as needed).
