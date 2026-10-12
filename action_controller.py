import json
import math
import os
import struct
import subprocess
import time
import wave
from typing import List, Optional, Tuple

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import winsound
except ImportError:
    winsound = None

try:
    import pyaudio
except ImportError:
    pyaudio = None


class ActionController:
    """Dispatches physical motion, PyBullet light, speaker sound effects, music, and TTS."""

    def __init__(self, simulation=None):
        self.sim = simulation
        self.tts_engine = None
        if pyttsx3:
            try:
                self.tts_engine = pyttsx3.init()
                voices = self.tts_engine.getProperty("voices")
                if voices:
                    self.tts_engine.setProperty("voice", voices[0].id)
            except Exception as exc:
                print(f"Warning: TTS initialization failed: {exc}")
                self.tts_engine = None

        self._pa: Optional["pyaudio.PyAudio"] = None

        # Define basic animations as joint target arrays
        # [base_yaw, shoulder_pitch, elbow_pitch, neck_yaw, head_pitch]
        self.animations = {
            "neutral": [0.0, 0.0, -0.5, 0.0, 0.0],
            "nod": [0.0, 0.2, -0.5, 0.0, -0.4],
            "shake_head": [0.0, 0.0, -0.5, 0.5, 0.0],
            "look_left": [0.5, 0.0, -0.5, 0.0, 0.0],
            "look_right": [-0.5, 0.0, -0.5, 0.0, 0.0],
            "search": [0.0, -0.3, -0.2, 0.8, -0.2],
        }
        self.light_colors = {
            "off": (0.03, 0.03, 0.03),
            "warm": (1.0, 0.86, 0.45),
            "thinking": (0.30, 0.62, 1.0),
            "success": (0.35, 1.0, 0.45),
            "error": (1.0, 0.20, 0.14),
        }

    def execute_command(self, command):
        """Executes full multi-modal command enforcing whole-command timeout budget."""
        start = time.monotonic()
        deadline = start + command.timeout_s
        timed_out = False

        # 1. Visual light cue
        if command.light and time.monotonic() < deadline:
            self.set_light(command.light)
        elif time.monotonic() >= deadline:
            timed_out = True

        # 2. Music cue
        if command.music != "none" and not timed_out:
            remaining_s = max(0.0, deadline - time.monotonic())
            if remaining_s > 0:
                self.play_music(command.music, max_duration_s=remaining_s)
            if time.monotonic() >= deadline:
                timed_out = True

        # 3. Sound effect
        if command.sound != "none" and not timed_out:
            remaining_s = max(0.0, deadline - time.monotonic())
            if remaining_s > 0:
                self.play_sound(command.sound, max_duration_s=remaining_s)
            if time.monotonic() >= deadline:
                timed_out = True

        # 4. Joint Motion settling
        motion_done = False
        if command.action in self.animations and self.sim and not timed_out:
            remaining_s = max(0.0, deadline - time.monotonic())
            if remaining_s > 0:
                print(f"Executing action: {command.action}")
                self.sim.set_joint_angles(self.animations[command.action])
                self._settle_motion(command.action, remaining_s)
                motion_done = self._motion_reached(command.action)
            if time.monotonic() >= deadline:
                timed_out = True
        else:
            motion_done = True

        # 5. Spoken response (TTS)
        if command.speech and not timed_out:
            remaining_s = max(0.0, deadline - time.monotonic())
            if remaining_s > 0:
                print(f"Robot says: {command.speech}")
                self._speak_bounded(command.speech, max_duration_s=remaining_s)
            if time.monotonic() >= deadline:
                timed_out = True

        # Return robot joint angles to neutral rest pose
        if self.sim:
            self.sim.set_joint_angles(self.animations["neutral"])

        duration_ms = int((time.monotonic() - start) * 1000)
        completed = not timed_out and (motion_done or not self.sim)

        return {
            "completed": completed,
            "timed_out": timed_out,
            "action": command.action,
            "duration_ms": duration_ms,
            "joint_error_rad": self._joint_error(command.action),
            "light": command.light,
            "sound": command.sound,
            "music": command.music,
        }

    def set_light(self, cue: str) -> None:
        print(f"Light cue: {cue}")
        if self.sim:
            self.sim.set_light(self.light_colors.get(cue, self.light_colors["warm"]))

    def play_sound(self, cue: str, max_duration_s: float = 5.0) -> None:
        print(f"Sound effect: {cue}")
        tones = {
            "chirp": [(880, 80), (1175, 90)],
            "confirm": [(660, 100), (990, 100)],
            "error": [(220, 160), (185, 180)],
        }
        self._play_tones(tones.get(cue, []), max_duration_s=max_duration_s)

    def play_music(self, cue: str, max_duration_s: float = 5.0) -> None:
        print(f"Music cue: {cue}")
        tunes = {
            "curious": [(523, 90), (659, 90), (784, 130)],
            "success": [(523, 90), (659, 90), (1046, 160)],
        }
        self._play_tones(tunes.get(cue, []), max_duration_s=max_duration_s)

    def _play_tones(self, tones: List[Tuple[int, int]], max_duration_s: float = 5.0) -> None:
        deadline = time.monotonic() + max_duration_s
        for frequency, duration_ms in tones:
            if time.monotonic() >= deadline:
                break
            # Play tone
            if winsound:
                winsound.Beep(frequency, duration_ms)
            else:
                played = self._play_pcm_tone_linux(frequency, duration_ms / 1000.0)
                if not played:
                    time.sleep(duration_ms / 1000.0)

    def _play_pcm_tone_linux(self, frequency: int, duration_s: float) -> bool:
        """Synthesizes and plays sine wave PCM audio on Linux/macOS."""
        sample_rate = 16000
        num_samples = int(sample_rate * duration_s)
        fade_len = min(int(sample_rate * 0.01), num_samples // 2)
        raw_samples = []
        for i in range(num_samples):
            envelope = 1.0
            if fade_len > 0:
                if i < fade_len:
                    envelope = i / fade_len
                elif i > num_samples - fade_len:
                    envelope = (num_samples - i) / fade_len
            val = int(0.4 * envelope * 32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            raw_samples.append(struct.pack("<h", max(-32768, min(32767, val))))
        pcm_data = b"".join(raw_samples)

        if pyaudio:
            try:
                if self._pa is None:
                    self._pa = pyaudio.PyAudio()
                stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=sample_rate,
                    output=True,
                )
                stream.write(pcm_data)
                stream.stop_stream()
                stream.close()
                return True
            except Exception:
                pass

        # Fallback to aplay or paplay if available on Linux
        try:
            p = subprocess.Popen(
                ["aplay", "-r", str(sample_rate), "-f", "S16_LE", "-t", "raw", "-q"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            p.communicate(input=pcm_data, timeout=duration_s + 1.0)
            return True
        except Exception:
            pass

        return False

    def _speak_bounded(self, speech: str, max_duration_s: float) -> None:
        if not self.tts_engine:
            return
        try:
            self.tts_engine.say(speech)
            self.tts_engine.runAndWait()
        except Exception as exc:
            print(f"TTS error: {exc}")

    def _settle_motion(self, action: str, timeout_s: float) -> None:
        if not self.sim:
            return
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            self.sim.step()
            if self._motion_reached(action):
                return

    def _motion_reached(self, action: str) -> bool:
        return self._joint_error(action) < 0.12

    def _joint_error(self, action: str) -> float:
        if not self.sim or action not in self.animations:
            return 0.0
        current = self.sim.get_joint_angles()
        target = self.animations[action]
        if not current:
            return 0.0
        return max(abs(a - b) for a, b in zip(current, target))

    def cleanup(self) -> None:
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except Exception:
                pass
