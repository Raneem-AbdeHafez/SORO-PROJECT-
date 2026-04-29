# SORO-PROJECT
Control a NAO robot using an Xbox controller with smooth movement, speech, and expressive actions.

---

## ✨ Features

* 🏃 Walking and turning control via left joystick
* 🤖 Head tracking via right joystick
* 💪 Independent arm control 
* ✋ Hand open/close with triggers
* 🗣️ Text-to-speech (B/X/Y buttons)
* 💡 LED eye color switching
* 🦵 Kick action 

---

## 🎮 Controls

| Input              | Action             |
| ------------------ | ------------------ |
| Left Joystick      | Move and turn robot|
| Right Joystick     | Move head          |
| LB + Right Stick   | Control left arm   |
| RB + Right Stick   | Control right arm  |
| Triggers  LT/ RT   | Open/close hands   |
| A                  | Kick               |
| B / X / Y          | Speech actions     |
| Right Stick Button | Change eye color   |

---

## ⚙️ Requirements

* Python 2.7
* NAOqi SDK
* Pygame

---

## 🚀 Setup & Run

1. Connect to NAO robot network
2. Set your robot IP in the ip_init.py script:

   ```python
   NAO_IP = "your.nao.ip.here"
   ```
3. Plug in the Xbox controller
4. Run:

```bash
python nao_complete_V2.0.py
```
