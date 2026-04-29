# -*- coding: utf-8 -*-
import os
import random
import time

from ip_init import ( #edit IP address in ip_init.py or set NAO_IP and NAO_PORT environment variables
    DEFAULT_NAO_IP,
    DEFAULT_NAO_PORT,
)
from audio_init import initialize_audio
from naoqi import ALProxy

NAO_IP = DEFAULT_NAO_IP
PORT = DEFAULT_NAO_PORT

motion = ALProxy("ALMotion", NAO_IP, PORT)
motion.setStiffnesses("Body", 1.0)
tts = ALProxy("ALTextToSpeech", NAO_IP, PORT)
audio = ALProxy("ALAudioDevice", NAO_IP, PORT)

DEADPAN_TTS_VOLUME = 0.80
DEADPAN_TTS_SPEED = 62.0
DEADPAN_TTS_PITCH_SHIFT = 0.68


def _set_tts_parameter(tts_proxy, name, value):
    try:
        tts_proxy.setParameter(name, value)
        return True
    except Exception:
        return False


def apply_deadpan_voice_style(tts_proxy):
    try:
        tts_proxy.setVolume(DEADPAN_TTS_VOLUME)
    except Exception:
        pass
    _set_tts_parameter(tts_proxy, "speed", DEADPAN_TTS_SPEED)
    _set_tts_parameter(tts_proxy, "pitchShift", DEADPAN_TTS_PITCH_SHIFT)
    _set_tts_parameter(tts_proxy, "doubleVoice", 0.0)
    _set_tts_parameter(tts_proxy, "doubleVoiceLevel", 0.0)
    _set_tts_parameter(tts_proxy, "doubleVoiceTimeShift", 0.0)


def ensure_audio_output(audio_proxy, volume=100):
    try:
        audio_proxy.muteAudioOut(False)
    except Exception:
        pass
    try:
        audio_proxy.setOutputVolume(volume)
    except Exception:
        pass


def configure_deadpan_audio(tts_proxy=None, audio_proxy=None):
    if audio_proxy is None:
        audio_proxy = audio
    if tts_proxy is None:
        tts_proxy = tts
    ensure_audio_output(audio_proxy, volume=100)
    apply_deadpan_voice_style(tts_proxy)


def say_deadpan(message, tts_proxy=None, audio_proxy=None, asynchronous=True):
    if tts_proxy is None:
        tts_proxy = tts
    configure_deadpan_audio(tts_proxy=tts_proxy, audio_proxy=audio_proxy)
    try:
        if asynchronous:
            tts_proxy.post.say(message)
        else:
            tts_proxy.say(message)
        return True
    except Exception:
        return False

CHECK_INTERVAL_SECONDS = 0.5

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "sounds")
FAILURE_SOUNDS_DIR = os.path.join(SOUNDS_DIR, "failure_sounds")
ROBOT_SOUNDS_DIR = os.environ.get("NAO_ROBOT_SOUNDS_DIR", "/home/nao/sounds")
ROBOT_FAILURE_SOUNDS_DIR = os.path.join(ROBOT_SOUNDS_DIR, "failure_sounds")
SUPPORTED_SOUND_EXTENSIONS = (".wav", ".mp3", ".ogg")

CATEGORY_ALIASES = {
    "general": ["general"],
    "falling": ["falling"],
    "standing_up": ["standing_up", "standing up"],
}


def _list_sound_files(folder_path):
    if not os.path.isdir(folder_path):
        return []
    return [
        os.path.join(folder_path, file_name)
        for file_name in os.listdir(folder_path)
        if file_name.lower().endswith(SUPPORTED_SOUND_EXTENSIONS)
    ]


def _collect_local_category_sounds(category):
    sounds = []
    aliases = CATEGORY_ALIASES.get(category, [category])
    for category_name in aliases:
        sounds.extend(_list_sound_files(os.path.join(SOUNDS_DIR, category_name)))
        sounds.extend(_list_sound_files(os.path.join(FAILURE_SOUNDS_DIR, category_name)))
    return sounds


GENERAL_SOUNDS = _collect_local_category_sounds("general")
FALLING_SOUNDS = _collect_local_category_sounds("falling")
STANDING_UP_SOUNDS = _collect_local_category_sounds("standing_up")
FALLING_AND_GENERAL_SOUNDS = list(FALLING_SOUNDS) + list(GENERAL_SOUNDS)

# Compatibility fallback: support flat sounds directly under /sounds
LEGACY_ROOT_SOUNDS = _list_sound_files(SOUNDS_DIR)
if not GENERAL_SOUNDS:
    GENERAL_SOUNDS = list(LEGACY_ROOT_SOUNDS)


def _to_robot_sound_path(local_sound_path):
    """Map a local workspace sound path to a robot-local absolute path."""
    try:
        relative_path = os.path.relpath(local_sound_path, SOUNDS_DIR)
        if not relative_path.startswith(".."):
            return os.path.join(ROBOT_SOUNDS_DIR, relative_path).replace("\\", "/")
    except Exception:
        pass

    try:
        relative_failure_path = os.path.relpath(local_sound_path, FAILURE_SOUNDS_DIR)
        if not relative_failure_path.startswith(".."):
            return os.path.join(ROBOT_FAILURE_SOUNDS_DIR, relative_failure_path).replace("\\", "/")
    except Exception:
        pass

    return local_sound_path.replace("\\", "/")


def _robot_path_candidates(local_sound_path, category=None):
    candidates = []
    file_name = os.path.basename(local_sound_path)
    if category:
        for category_name in CATEGORY_ALIASES.get(category, [category]):
            candidates.append(os.path.join(ROBOT_SOUNDS_DIR, category_name, file_name).replace("\\", "/"))
            candidates.append(os.path.join(ROBOT_FAILURE_SOUNDS_DIR, category_name, file_name).replace("\\", "/"))

    candidates.append(_to_robot_sound_path(local_sound_path))

    deduped_candidates = []
    for path in candidates:
        if path and path not in deduped_candidates:
            deduped_candidates.append(path)
    return deduped_candidates

FALLEN_PHRASES = [
    "As planned.",
    "We’re good. We’re so... good.",
    "Just testing gravity.",
    "Nothing to see here.",
    "I meant... to do that.",
    "Thought that would go differently.",
    "I miscalculated.",
    "That’s on me, actually.",
    "Nailed it.",
    "This is fine.",
    "Anyway—",
    "The ground attacked me.",
    "I’ll be taking no further questions at this time.",
    "Parkoooour!",
    "LAG",
    "Physics said no.",
    
]

GENERIC_PHRASES = [
    "I’ll be taking no further questions at this time.",
    "This... is fine.",
    "Anywayyy—",
    "Processing…",
    "Buffering…",
    "Who coded this?!",
    "This build is buggy.",
    "Anyway...",
]


class NaoFallback(object):
    def __init__(self, nao_ip=NAO_IP, port=PORT, voice_style="deadpan"):
        self.motion = ALProxy("ALMotion", nao_ip, port)
        self.tts = ALProxy("ALTextToSpeech", nao_ip, port)
        self.audio = ALProxy("ALAudioDevice", nao_ip, port)
        self.posture = ALProxy("ALRobotPosture", nao_ip, port)
        self.memory = ALProxy("ALMemory", nao_ip, port)
        self.voice_style = voice_style
        ensure_audio_output(self.audio, volume=100)
        self.apply_voice_style()

    def apply_voice_style(self):
        if self.voice_style == "deadpan":
            apply_deadpan_voice_style(self.tts)
        else:
            try:
                self.tts.setVolume(1.0)
            except Exception:
                pass
            _set_tts_parameter(self.tts, "speed", 100.0)
            _set_tts_parameter(self.tts, "pitchShift", 1.0)
            _set_tts_parameter(self.tts, "doubleVoiceLevel", 0.0)

    def is_fallen(self):
        try:
            if self.memory.getData("robotHasFallen"):
                return True
        except Exception:
            pass

        try:
            posture_name = self.posture.getPostureFamily()
            return posture_name in ("LyingBack", "LyingBelly")
        except Exception:
            return False

    def say_random(self, fallen=False):
        ensure_audio_output(self.audio, volume=100)

        if fallen:
            sound_pool = FALLING_AND_GENERAL_SOUNDS
            phrase_pool = FALLEN_PHRASES + GENERIC_PHRASES
            category = "falling"
        else:
            sound_pool = GENERAL_SOUNDS
            phrase_pool = GENERIC_PHRASES
            category = "general"

        if random.random() < 0.3:
            played = play_random_sound_from_list(sound_pool, category=category)
            if played:
                return played
        
        phrase = random.choice(phrase_pool)
        say_deadpan(phrase, tts_proxy=self.tts, audio_proxy=self.audio, asynchronous=True)
        return phrase

    def safe_stand_up(self):
        try:
            self.motion.setStiffnesses("Body", 1.0)
            self.motion.wakeUp()
            time.sleep(1.0)
            self.posture.goToPosture("StandInit", 0.5)
            return True
        except Exception:
            try:
                self.motion.rest()
            except Exception:
                pass
            return False

    def handle_failure(self):
        fallen = self.is_fallen()
        spoken = self.say_random(fallen=fallen)
        stood_up = False
        standing_up = None

        if fallen:
            try:
                stood_up = self.safe_stand_up()
                if stood_up:
                    standing_up = trigger_standing_up_response(sound_probability=1.0)
            except Exception:
                stood_up = False

        return {
            "fallen": fallen,
            "spoken": spoken,
            "stood_up": stood_up,
            "standing_up": standing_up,
        }


def get_random_fallen_phrase():
    """Return a random fallen-state phrase."""
    return random.choice(FALLEN_PHRASES)


def get_random_generic_phrase():
    """Return a random generic-state phrase."""
    return random.choice(GENERIC_PHRASES)


def play_random_sound_from_list(sound_list, category=None):
    """Play a random sound from a provided list. Returns filename or None if no sound."""
    if not sound_list:
        return None
    ensure_audio_output(audio, volume=100)
    sound_file = random.choice(sound_list)
    for robot_sound_file in _robot_path_candidates(sound_file, category=category):
        try:
            player = ALProxy("ALAudioPlayer", NAO_IP, PORT)
            player.playFile(robot_sound_file)
            return os.path.basename(sound_file)
        except Exception as e:
            print("robot path play failed ({}): {}".format(robot_sound_file, e))

    try:
        player = ALProxy("ALAudioPlayer", NAO_IP, PORT)
        player.playFile(sound_file)
        return os.path.basename(sound_file)
    except Exception as e:
        print("local path play failed ({}): {}".format(sound_file, e))
        return None


def probe_mp3_playback():
    """Try one known general sound and report whether playback succeeded."""
    if not GENERAL_SOUNDS:
        print("probe_mp3_playback: no general sounds found in workspace list")
        return False
    candidate = GENERAL_SOUNDS[0]
    robot_candidate = _to_robot_sound_path(candidate)
    ensure_audio_output(audio, volume=100)
    try:
        player = ALProxy("ALAudioPlayer", NAO_IP, PORT)
        player.playFile(robot_candidate)
        print("probe_mp3_playback: robot path OK -> {}".format(robot_candidate))
        return True
    except Exception as exc:
        print("probe_mp3_playback: robot path failed -> {}".format(exc))

    try:
        player = ALProxy("ALAudioPlayer", NAO_IP, PORT)
        player.playFile(candidate)
        print("probe_mp3_playback: local path OK -> {}".format(candidate))
        return True
    except Exception as exc:
        print("probe_mp3_playback: local path failed -> {}".format(exc))
        return False


def play_random_sound():
    """Backward-compatible generic sound playback."""
    return play_random_sound_from_list(GENERAL_SOUNDS, category="general")


def play_random_falling_sound():
    """Play a random sound from falling and general sounds."""
    return play_random_sound_from_list(FALLING_AND_GENERAL_SOUNDS, category="falling")


def play_random_standing_up_sound():
    """Play a random sound from standing_up sounds."""
    return play_random_sound_from_list(STANDING_UP_SOUNDS, category="standing_up")


def trigger_generic_response(sound_probability=0.3):
    """Play a generic sound or say a deadpan generic phrase. Returns played file or spoken text."""
    if random.random() < sound_probability:
        played = play_random_sound()
        if played:
            return played
    phrase = get_random_generic_phrase()
    say_deadpan(phrase, tts_proxy=tts, audio_proxy=audio, asynchronous=True)
    return phrase


def trigger_fallen_response(sound_probability=0.3):
    """Play a falling sound or say a deadpan fallen phrase. Returns played file or spoken text."""
    if random.random() < sound_probability:
        played = play_random_falling_sound()
        if played:
            return played
    phrase = get_random_fallen_phrase()
    say_deadpan(phrase, tts_proxy=tts, audio_proxy=audio, asynchronous=True)
    return phrase


def trigger_standing_up_response(sound_probability=1.0):
    """Play standing-up sound, or deadpan generic phrase if no standing sound is available."""
    if random.random() < sound_probability:
        played = play_random_standing_up_sound()
        if played:
            return played
    phrase = get_random_generic_phrase()
    say_deadpan(phrase, tts_proxy=tts, audio_proxy=audio, asynchronous=True)
    return phrase


def main():
    initialize_audio(audio, tts, NAO_IP, PORT, label="Fail module audio ready")
    fallback = NaoFallback(nao_ip=NAO_IP, port=PORT, voice_style="deadpan")
    last_fallen_state = None
    print("Running fallback monitor. Press Ctrl+C to stop.")

    try:
        while True:
            fallen = fallback.is_fallen()

            if fallen and last_fallen_state is not True:
                result = fallback.handle_failure()
                print(
                    "fallen=True spoken={!r} stood_up={} standing_up={!r}".format(
                        result["spoken"],
                        result["stood_up"],
                        result["standing_up"],
                    )
                )
            elif (not fallen) and last_fallen_state is not False:
                spoken = fallback.say_random(fallen=False)
                print("fallen=False spoken={!r} stood_up=False".format(spoken))

            last_fallen_state = fallen
            time.sleep(CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("Stopping fallback monitor.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())