# -*- coding: utf-8 -*-
"""
BUTTONS: 
Y: 3
X: 2
B: 1
A: 0
Start: 7
Back: 6
RB: 5
LB: 4
RJS: 9
LJS: 8
"""
import pygame
import threading
import time

from ip_init import (
    DEFAULT_NAO_IP,
    DEFAULT_NAO_PORT,
)
from audio_init import initialize_audio
from naoqi import ALBroker, ALModule, ALProxy

try:
    import fail
except ImportError:
    fail = None

NAO_IP = DEFAULT_NAO_IP
PORT = DEFAULT_NAO_PORT
FALL_EVENT_NAME = "robotHasFallen"
LISTENER_MODULE_NAME = "SoroFallStandListener"
ENABLE_FALL_STAND_LISTENER = False

motion = ALProxy("ALMotion", NAO_IP, PORT)
motion.setStiffnesses("Body", 1.0)
tts = ALProxy("ALTextToSpeech", NAO_IP, PORT)
audio = ALProxy("ALAudioDevice", NAO_IP, PORT)
posture = ALProxy("ALRobotPosture", NAO_IP, PORT)

event_broker = None
fall_listener = None
joy = None
button_states = []
hat_states = []


class FallStandListener(ALModule):
    def __init__(self, module_name, nao_ip, port):
        ALModule.__init__(self, module_name)
        self.memory = ALProxy("ALMemory", nao_ip, port)
        self.last_fallen = False
        try:
            self.last_fallen = bool(self.memory.getData(FALL_EVENT_NAME))
        except Exception:
            pass
        self.memory.subscribeToEvent(FALL_EVENT_NAME, self.getName(), "on_robot_has_fallen")

    def _run_async(self, target, *args):
        task = threading.Thread(target=target, args=args)
        task.daemon = True
        task.start()

    def on_robot_has_fallen(self, event_key, event_value, subscriber_name):
        del event_key
        del subscriber_name
        fallen = bool(event_value)

        if not fail:
            self.last_fallen = fallen
            return

        if fallen and not self.last_fallen:
            self._run_async(fail.trigger_fallen_response, 0.3)
        elif (not fallen) and self.last_fallen:
            self._run_async(fail.trigger_standing_up_response, 1.0)

        self.last_fallen = fallen

    def stop(self):
        try:
            self.memory.unsubscribeToEvent(FALL_EVENT_NAME, self.getName())
        except Exception:
            pass


def start_fall_stand_listener():
    global event_broker
    global fall_listener

    if not ENABLE_FALL_STAND_LISTENER:
        print("Fall/stand listener disabled")
        return False

    if not fail:
        print("Fail module not available, skipping fall/stand listener")
        return False

    try:
        event_broker = ALBroker("SoroEventBroker", "0.0.0.0", 0, NAO_IP, PORT)
        fall_listener = FallStandListener(LISTENER_MODULE_NAME, NAO_IP, PORT)
        print("Subscribed to ALMemory event: {}".format(FALL_EVENT_NAME))
        return True
    except Exception as exc:
        print("Failed to start fall/stand listener:", exc)
        return False


def stop_fall_stand_listener():
    global event_broker
    global fall_listener

    if not ENABLE_FALL_STAND_LISTENER:
        return

    if fall_listener is not None:
        try:
            fall_listener.stop()
        except Exception:
            pass
        fall_listener = None

    if event_broker is not None:
        try:
            event_broker.shutdown()
        except Exception:
            pass
        event_broker = None

BUTTON_A = 0
BUTTON_B = 1
BUTTON_X = 2
BUTTON_Y = 3
BUTTON_LB = 4
BUTTON_RB = 5
BUTTON_BACK = 6
BUTTON_START = 7
BUTTON_LEFT_JOYSTICK = 8
BUTTON_RIGHT_JOYSTICK = 9

AXIS_LEFT_TRIGGER = 4
AXIS_RIGHT_TRIGGER = 5
AXIS_JOYSTICK1_X = 0
AXIS_JOYSTICK1_Y = 1
AXIS_JOYSTICK2_X = 2
AXIS_JOYSTICK2_Y = 3

EVENT_LEFT_TRIGGER_PRESS = "LEFT_TRIGGER_PRESS"
EVENT_LEFT_TRIGGER_RELEASE = "LEFT_TRIGGER_RELEASE"
EVENT_RIGHT_TRIGGER_PRESS = "RIGHT_TRIGGER_PRESS"
EVENT_RIGHT_TRIGGER_RELEASE = "RIGHT_TRIGGER_RELEASE"

BUTTON_NAMES = {
    BUTTON_A: "Xbox A",
    BUTTON_X: "Xbox X",
    BUTTON_B: "Xbox B",
    BUTTON_Y: "Xbox Y",
    BUTTON_LB: "LB",
    BUTTON_RB: "RB",
    BUTTON_BACK: "Back",
    BUTTON_START: "Start",
    BUTTON_LEFT_JOYSTICK: "Left joystick button",
    BUTTON_RIGHT_JOYSTICK: "Right joystick button",
}

DPAD_DIRECTION_NAMES = {
    (0, 1): "DPad Up",
    (0, -1): "DPad Down",
    (-1, 0): "DPad Left",
    (1, 0): "DPad Right",
    (-1, 1): "DPad Up-Left",
    (1, 1): "DPad Up-Right",
    (-1, -1): "DPad Down-Left",
    (1, -1): "DPad Down-Right",
}

EYE_COLORS = [
    (0xFF, 0x00, 0x00),
    (0x00, 0xFF, 0x00),
    (0x00, 0x00, 0xFF),
    (0xFF, 0xFF, 0x00),
    (0xFF, 0x00, 0xFF),
    (0x00, 0xFF, 0xFF),
    (0xFF, 0xFF, 0xFF),
]


def button_just_pressed(button_index):
    pressed = bool(joy.get_button(button_index))
    just_pressed = pressed and not button_states[button_index]
    button_states[button_index] = pressed
    if just_pressed:
        print("button_just_pressed returning True for button {}".format(button_index))
    return just_pressed


def get_button_name(button_index):
    return BUTTON_NAMES.get(button_index, "Button {}".format(button_index))


# Thresholds and control tuning
PRESS_THRESHOLD = 0.7
RELEASE_THRESHOLD = 0.2
WALK_DEADZONE = 0.2
WALK_SPEED_SCALE = 0.4
WALK_REVERSE_BLOCK_TIME = 0.2
HEAD_DEADZONE = 0.2
MAX_HEAD_YAW = 0.9
MAX_HEAD_PITCH = 0.5
HEAD_SPEED = 0.15
HEAD_SMOOTH_FACTOR = 0.3


def trigger_fail_response(fallen=False):
    if not fail:
        print("Fail module not available")
        return None

    try:
        fail.configure_deadpan_audio(tts_proxy=tts, audio_proxy=audio)
    except Exception as exc:
        print("Fail deadpan reconfigure failed:", exc)

    if fallen:
        return fail.trigger_fallen_response(sound_probability=0.0)
    return fail.trigger_generic_response(sound_probability=0.0)

# -------------------------
# KICKING FUNCTION
# -------------------------
FRAME_TORSO = 0

def simple_kick():
    """Execute a simple kick motion using balance control"""
    print("KICK START")

    motion.wbEnable(True)
    motion.wbFootState("Fixed", "Legs")

    time.sleep(0.5)
    print("WEIGHT SHIFTING...1")

    motion.wbGoToBalance("LLeg", 0.6)
    # print("WEIGHT SHIFTING...2")
    motion.wbFootState("Free", "RLeg")
    # print("WEIGHT SHIFTING...3")

    time.sleep(0.3)
    print("WEIGHT REBALANCED")

    motion.positionInterpolation(
        "RLeg",
        FRAME_TORSO,
        [
            [-0.02, 0.0, 0.03, 0.0, 0.0, 0.0],
            [0.06, 0.01, 0.02, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ],
        63,
        [1.0, 1.6, 2.2],
        False
    )

    time.sleep(0.2)


    print("RECOVERY: lock support and rebalance")
    motion.wbFootState("Fixed", "RLeg")
    motion.wbGoToBalance("Legs", 1.0)
    time.sleep(0.1)

    motion.wbEnable(False)
    time.sleep(0.1)  # Allow balance control to fully disengage

    # Use slower speed for safer posture recovery
    print("posture.goToPosture('StandInit', 0.8)")
    posture.goToPosture("StandInit", 0.8)
    time.sleep(0.5)  # Allow extra time for stable standing

    print("KICK END")

def setup_controller():
    global joy
    global button_states
    global hat_states

    pygame.init()
    pygame.joystick.init()

    joystick_count = pygame.joystick.get_count()
    if joystick_count < 1:
        raise RuntimeError("No joystick detected. Connect a controller and retry.")

    joy = pygame.joystick.Joystick(0)
    joy.init()
    button_states = [False] * joy.get_numbuttons()
    hat_states = [(0, 0)] * joy.get_numhats()
    print("Controller:", joy.get_name())


def run_control_loop():
    motion.moveInit()
    motion.wakeUp()
    posture.goToPosture("StandInit", 0.6)

    walk_reverse_block_until = 0.0
    last_walk_command = (0.0, 0.0)
    head_is_neutral = True
    current_head_yaw = 0.0
    current_head_pitch = 0.0
    target_head_yaw = 0.0
    target_head_pitch = 0.0
    current_eye_color_index = 0
    left_closed = False
    right_closed = False
    leds = ALProxy("ALLeds", NAO_IP, PORT)

    while True:
        pygame.event.pump()

        # ╔════════════════════════════════════════════════════════════╗
        # ║         WALKING / TURNING (Left Joystick 1 )               ║
        # ╚════════════════════════════════════════════════════════════╝

        # Normalize trigger values first.
        left_trigger = (joy.get_axis(AXIS_LEFT_TRIGGER) + 1) / 2.0
        right_trigger = (joy.get_axis(AXIS_RIGHT_TRIGGER) + 1) / 2.0

        requested_forward = -joy.get_axis(AXIS_JOYSTICK1_Y)
        requested_turn = -joy.get_axis(AXIS_JOYSTICK1_X)

        head_x = joy.get_axis(AXIS_JOYSTICK2_X)
        head_y = joy.get_axis(AXIS_JOYSTICK2_Y)

        if abs(requested_forward) < WALK_DEADZONE:
            requested_forward = 0.0
        if abs(requested_turn) < WALK_DEADZONE:
            requested_turn = 0.0

        requested_forward *= WALK_SPEED_SCALE
        requested_turn *= WALK_SPEED_SCALE

        now = time.time()
        current_forward, current_turn = last_walk_command
        opposite_forward = (
            current_forward != 0.0 and
            requested_forward != 0.0 and
            (current_forward > 0 > requested_forward or current_forward < 0 < requested_forward)
        )

        if opposite_forward:
            if now >= walk_reverse_block_until:
                motion.post.stopMove()
                last_walk_command = (0.0, 0.0)
                walk_reverse_block_until = now + WALK_REVERSE_BLOCK_TIME

        if now < walk_reverse_block_until:
            requested_forward = 0.0
            requested_turn = 0.0

        if (requested_forward, requested_turn) != last_walk_command:
            if requested_forward != 0.0 or requested_turn != 0.0:
                motion.post.move(requested_forward, 0, requested_turn)
            else:
                motion.post.stopMove()
            last_walk_command = (requested_forward, requested_turn)

        # ╔════════════════════════════════════════════════════════════╗
        # ║           HEAD CONTROL (Right Joystick 2)                  ║
        # ║      (DISABLED DURING ARM MODE - LB/RB Active)            ║
        # ╚════════════════════════════════════════════════════════════╝

        lb = joy.get_button(BUTTON_LB)
        rb = joy.get_button(BUTTON_RB)

        arm_mode_active = (lb or rb)

        if not arm_mode_active:
            head_x = joy.get_axis(AXIS_JOYSTICK2_X)
            head_y = joy.get_axis(AXIS_JOYSTICK2_Y)

            if abs(head_x) < HEAD_DEADZONE:
                head_x = 0.0
            if abs(head_y) < HEAD_DEADZONE:
                head_y = 0.0

            if abs(head_x) > 0 or abs(head_y) > 0:
                target_head_yaw = head_x * MAX_HEAD_YAW
                target_head_pitch = head_y * MAX_HEAD_PITCH
                head_is_neutral = False
            else:
                if not head_is_neutral:
                    target_head_yaw = 0.0
                    target_head_pitch = 0.0
                    head_is_neutral = True

        else:
            if not head_is_neutral:
                target_head_yaw = 0.0
                target_head_pitch = 0.0
                head_is_neutral = True

        current_head_yaw += (target_head_yaw - current_head_yaw) * HEAD_SMOOTH_FACTOR
        current_head_pitch += (target_head_pitch - current_head_pitch) * HEAD_SMOOTH_FACTOR
        motion.post.setAngles(["HeadYaw", "HeadPitch"], [current_head_yaw, current_head_pitch], HEAD_SPEED)

        # ╔════════════════════════════════════════════════════════════╗
        # ║      ARMS CONTROL (LB / RB Bumpers + Right Joystick)       ║
        # ║   (LB = Left Arm, RB = Right Arm, Triggers = Hand Open)    ║
        # ╚════════════════════════════════════════════════════════════╝

        just_activated_inputs = []
        for button_index in range(joy.get_numbuttons()):
            if button_just_pressed(button_index):
                just_activated_inputs.append(button_index)
                print("button {} detected".format(get_button_name(button_index)))

        if left_trigger > PRESS_THRESHOLD and not left_closed:
            print("left trigger detected")
            just_activated_inputs.append(EVENT_LEFT_TRIGGER_PRESS)
            left_closed = True
        elif left_trigger < RELEASE_THRESHOLD and left_closed:
            print("left trigger released")
            just_activated_inputs.append(EVENT_LEFT_TRIGGER_RELEASE)
            left_closed = False

        if right_trigger > PRESS_THRESHOLD and not right_closed:
            print("right trigger detected")
            just_activated_inputs.append(EVENT_RIGHT_TRIGGER_PRESS)
            right_closed = True
        elif right_trigger < RELEASE_THRESHOLD and right_closed:
            print("right trigger released")
            just_activated_inputs.append(EVENT_RIGHT_TRIGGER_RELEASE)
            right_closed = False

        # =========================
        # ARM MIRROR CONTROL (FIXED)
        # =========================

        arm_x = joy.get_axis(AXIS_JOYSTICK2_X)
        arm_y = joy.get_axis(AXIS_JOYSTICK2_Y)

        # deadzone
        if abs(arm_x) < 0.15:
            arm_x = 0.0
        if abs(arm_y) < 0.15:
            arm_y = 0.0

        # invert Y so up/down feels natural
        arm_y = -arm_y

        # clamp safety
        arm_x = max(-1.0, min(1.0, arm_x))
        arm_y = max(-1.0, min(1.0, arm_y))

        lb = joy.get_button(BUTTON_LB)
        rb = joy.get_button(BUTTON_RB)

        arm_mode_active = (lb or rb)

        # -------------------------
        # JOINT LIMIT CONFIG (NAO SAFE RANGE)
        # -------------------------
        PITCH_DOWN = 1.4     # arms fully down (rest)
        PITCH_UP = -1.3      # arms up
        ROLL_RANGE = 0.6     # side movement

        # map joystick Y → shoulder pitch full range
        pitch = PITCH_DOWN + arm_y * (PITCH_UP - PITCH_DOWN)

        # map joystick X → shoulder roll
        roll = arm_x * ROLL_RANGE

        if arm_mode_active:

            # LEFT ARM
            if lb and not rb:
                motion.post.setAngles(
                    ["LShoulderPitch", "LShoulderRoll"],
                    [
                        pitch,
                        0.3 + roll
                    ],
                    0.2
                )

            # RIGHT ARM
            elif rb and not lb:
                motion.post.setAngles(
                    ["RShoulderPitch", "RShoulderRoll"],
                    [
                        pitch,
                        -0.3 - roll
                    ],
                    0.2
                )

        else:
            # =========================
            # RETURN TO NATURAL REST POSE
            # =========================
            motion.post.setAngles(
                ["LShoulderPitch", "LShoulderRoll",
                "RShoulderPitch", "RShoulderRoll"],
                [
                    1.4,   # left down
                    0.2,
                    1.4,   # right down
                    -0.2
                ],
                0.15
            )

        # ╔════════════════════════════════════════════════════════════╗
        # ║               BUTTON INPUT HANDLING                        ║
        # ║  A=Kick  B=Fail  X=Fail  Y=Fall                            ║
        # ║  Back=Fall  Start=Fail  LJS=Placeholder  RJS=Eye Cycle     ║
        # ║  LT=Close Left Hand  RT=Close Right Hand                   ║
        # ╚════════════════════════════════════════════════════════════╝

        for input_id in just_activated_inputs:
            if input_id == BUTTON_A:
                print("KICK TRIGGERED")
                simple_kick()
            elif input_id == BUTTON_X:
                trigger_fail_response(fallen=False)
            elif input_id == BUTTON_B:
                trigger_fail_response(fallen=False)
            elif input_id == BUTTON_Y:
                trigger_fail_response(fallen=True)
            
            elif input_id == BUTTON_BACK:
                trigger_fail_response(fallen=True)
            elif input_id == BUTTON_START:
                trigger_fail_response(fallen=False)
            elif input_id == BUTTON_LEFT_JOYSTICK:
                print("ACTION: BUTTON_LEFT_JOYSTICK placeholder")
            elif input_id == BUTTON_RIGHT_JOYSTICK:
                current_eye_color_index = (current_eye_color_index + 1) % len(EYE_COLORS)
                r, g, b = EYE_COLORS[current_eye_color_index]
                try:
                    leds.fadeRGB("FaceLeds", (r << 16) | (g << 8) | b, 0.5)
                    print("Eye color cycled to RGB({}, {}, {})" .format(r, g, b))
                except Exception as e:
                    print("Eye color change failed:", e)
            elif input_id == EVENT_LEFT_TRIGGER_PRESS:
                motion.post.closeHand("LHand")
            elif input_id == EVENT_LEFT_TRIGGER_RELEASE:
                motion.post.openHand("LHand")
            elif input_id == EVENT_RIGHT_TRIGGER_PRESS:
                motion.post.closeHand("RHand")
            elif input_id == EVENT_RIGHT_TRIGGER_RELEASE:
                motion.post.openHand("RHand")

        for hat_index in range(joy.get_numhats()):
            current_hat = joy.get_hat(hat_index)
            previous_hat = hat_states[hat_index]
            if current_hat != previous_hat:
                print("dpad hat {} changed: {} -> {}".format(hat_index, previous_hat, current_hat))
                if current_hat in DPAD_DIRECTION_NAMES:
                    print("dpad {} detected".format(DPAD_DIRECTION_NAMES[current_hat]))
                elif current_hat == (0, 0):
                    print("dpad released")
                else:
                    print("dpad custom state detected: {}".format(current_hat))
                hat_states[hat_index] = current_hat

        time.sleep(0.05)


def main():
    initialize_audio(audio, tts, NAO_IP, PORT, label="NAO Complete audio ready")
    if fail:
        try:
            fail.configure_deadpan_audio(tts_proxy=tts, audio_proxy=audio)
            print("Fail module deadpan voice configured")
        except Exception as exc:
            print("Fail deadpan configuration failed:", exc)

    start_fall_stand_listener()

    try:
        setup_controller()
        run_control_loop()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        stop_fall_stand_listener()
        try:
            motion.post.stopMove()
        except Exception:
            pass
        try:
            motion.setStiffnesses("Body", 1.0)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())