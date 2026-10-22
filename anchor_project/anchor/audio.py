"""Stage-locked offline soundscape with smooth two-deck ambient crossfades."""
from pathlib import Path
import wave
import pygame

SOUNDS = Path(__file__).resolve().parent.parent / "assets" / "sounds"

class Soundscape:
    FADE_SECONDS = 1.9

    def __init__(self):
        self.available = False
        self.error = None
        self.enabled = False
        self.stage = None
        self.phase = None
        self.paused = False
        self.sounds = {}
        self.channels = {}
        self.decks = {}
        self.crossfades = {}
        self.current_beds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
            pygame.mixer.set_num_channels(max(12, pygame.mixer.get_num_channels()))
            for index, name in enumerate(("ambient_a", "ambient_b", "music_a", "music_b", "breath", "effect", "ui")):
                self.channels[name] = pygame.mixer.Channel(index)
            self.decks = {"ambient": "a", "music": "a"}
            self.crossfades = {}
            for path in SOUNDS.glob("*.wav"):
                self.sounds[path.stem] = pygame.mixer.Sound(str(path))
            self.available = True
        except (pygame.error, OSError) as exc:
            self.error = str(exc)
            print("[Anchor audio] Initialization failed:", exc)

    def _stop(self, fade=300):
        for channel in self.channels.values():
            channel.fadeout(fade)
        self.crossfades.clear()
        self.current_beds.clear()

    def start(self, enabled):
        self.enabled = bool(enabled) and self.available
        self.stage = None
        self.phase = None
        self.paused = False
        if not self.enabled:
            self._stop(200)

    def stop(self):
        self._stop(500)
        self.enabled = False
        self.stage = None
        self.phase = None

    def _change_bed(self, kind, name, volume):
        """Play new loop on alternate channel while the old loop fades out."""
        sound = self.sounds.get(name)
        if sound is None:
            return
        if self.current_beds.get(kind) == name:
            # Keep the same continuous recording running across chapters.
            if kind in self.crossfades:
                self.crossfades[kind]["target"] = volume
            else:
                self.channels[f"{kind}_{self.decks[kind]}"].set_volume(volume)
            return
        self.current_beds[kind] = name
        old = self.decks[kind]
        new = "b" if old == "a" else "a"
        old_ch = self.channels[f"{kind}_{old}"]
        new_ch = self.channels[f"{kind}_{new}"]
        # If another transition was underway, settle it before reusing a deck.
        new_ch.stop()
        old_volume = old_ch.get_volume() if old_ch.get_busy() else 0.0
        new_ch.set_volume(0.0)
        new_ch.play(sound, loops=-1)
        self.crossfades[kind] = {
            "old": old, "new": new, "old_volume": old_volume,
            "target": volume, "age": 0.0,
        }
        self.decks[kind] = new

    def _tick_fades(self, dt):
        for kind, f in list(self.crossfades.items()):
            f["age"] = min(self.FADE_SECONDS, f["age"] + max(0.0, dt))
            x = f["age"] / self.FADE_SECONDS
            # Equal-power curves maintain perceived loudness in the middle.
            import math
            self.channels[f"{kind}_{f['old']}"].set_volume(f["old_volume"] * math.cos(x * math.pi / 2))
            self.channels[f"{kind}_{f['new']}"].set_volume(f["target"] * math.sin(x * math.pi / 2))
            if x >= 1.0:
                self.channels[f"{kind}_{f['old']}"].stop()
                del self.crossfades[kind]

    def _cue_from_offset(self, name, elapsed, volume):
        path = SOUNDS / (name + ".wav")
        if not path.exists():
            return
        try:
            with wave.open(str(path), "rb") as f:
                position = min(f.getnframes(), int(max(0, elapsed) * f.getframerate()))
                f.setpos(position)
                frames = f.readframes(f.getnframes() - position)
            if frames:
                sound = pygame.mixer.Sound(buffer=frames)
                ch = self.channels["breath"]
                ch.stop()
                ch.set_volume(volume)
                ch.play(sound)
                self._active_breath = sound
        except (pygame.error, OSError, EOFError, wave.Error):
            pass

    def update(self, journey, settings, dt=1/60):
        enabled = settings.get("sound", False) and "Sounds or spoken guidance" not in settings.get("avoid", [])
        if not enabled or not self.available:
            if self.enabled:
                self.stop()
            return
        if not self.enabled:
            self.start(True)
        if journey.paused:
            if not self.paused:
                self._stop(200)
                self.paused = True
            return
        if self.paused:
            self.paused = False
            self.stage = None
            self.phase = None
        stage = journey.stage
        if stage != self.stage:
            self.stage = stage
            self.phase = None
            self.channels["breath"].fadeout(160)
            # Rain starts in the motivational interlude and stays through extended rest.
            if stage in ("ENCOURAGE", "RESET"):
                ambient, avol, mvol = "rain", .67, .45
            elif stage == "WATCH":
                ambient, avol, mvol = "watch", .51, .35
            elif stage in ("BREATHE", "RELEASE", "INTRO"):
                ambient, avol, mvol = "air", .44, .30
            else:
                ambient, avol, mvol = "air", .32, .32
            self._change_bed("ambient", ambient, avol)
            self._change_bed("music", "music", mvol)
            if stage == "INTRO":
                self.effect("chime", .28)
        self._tick_fades(dt)
        if stage == "BREATHE":
            length = 6 if journey.hold_free else 4
            phase = int(journey.time // length) % (2 if journey.hold_free else 4)
            if phase != self.phase:
                self.phase = phase
                elapsed = journey.time % length
                if journey.hold_free:
                    name = ("inhale_no_hold", "exhale_no_hold")[phase]
                else:
                    name = ("inhale", None, "exhale", None)[phase]
                if name is None:
                    # True silence for breath holds; background ambience remains soft.
                    self.channels["breath"].stop()
                else:
                    self._cue_from_offset(name, elapsed, .83)
        elif stage == "RELEASE":
            phase = int(journey.time / 3.0)
            if phase != self.phase:
                self.phase = phase
                if phase > 0:
                    self.effect("particle", .32)

    def effect(self, name, volume=.2):
        if self.enabled and name in self.sounds:
            channel = self.channels["effect"]
            if not channel.get_busy():
                channel.set_volume(volume)
                channel.play(self.sounds[name])

    def ui_click(self):
        if self.enabled and "ui_click" in self.sounds:
            channel = self.channels["ui"]
            channel.set_volume(.55)
            channel.play(self.sounds["ui_click"])

    def preview_click(self):
        if self.available:
            self.enabled = True
            self.ui_click()
