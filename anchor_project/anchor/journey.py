"""A small state machine: one continuous session with a real check-in."""
import math
import random


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Journey:
    def __init__(self, preferences):
        self.preferences = preferences
        self.stage = 'INTRO'
        self.time = 0.0
        self.paused = False
        self.retries = 0
        self.ripples = []
        self.last_phase = None
        self.cycles = self._cycles()
        self.hold_free = 'Holding my breath' in preferences['avoid']
        self.cycle_seconds = 12.0 if self.hold_free else 16.0
        self.duration = {
            'BREATHE': self.cycles * self.cycle_seconds,
            'RELEASE': 24.0,
            'WATCH': 32.0,
            'RESET': 36.0,
        }
        self.sequence = ['BREATHE', 'RELEASE', 'WATCH']
        self.sequence_index = 0
        self.transition_age = 1.0
        self.checkin_selection = None
        self.encouragement = random.choice([
            'One moment at a time.',
            'You deserve a little gentleness.',
            'There is no perfect way to feel.',
            'Thank you for giving yourself this moment.',
            'A small pause can matter.',
        ])

    def _cycles(self):
        needs = self.preferences['needs']
        if 'Everything feels overwhelming' in needs:
            return 4
        if 'Slowing things down' in self.preferences['helpful']:
            return 6
        return 5

    def breath(self):
        """Return cue, expansion, phase index, and cycle number."""
        period = self.cycle_seconds
        t = self.time % period
        if self.hold_free:
            phase = int(t // 6)
            fraction = (t % 6) / 6
            expansion = smooth(fraction) if phase == 0 else 1 - smooth(fraction)
            return ('Breathe in' if phase == 0 else 'Breathe out', expansion, phase,
                    int(self.time // period) + 1)
        phase = int(t // 4)
        fraction = (t % 4) / 4
        if phase == 0:
            return 'Breathe in', smooth(fraction), phase, int(self.time // period) + 1
        if phase == 1:
            return 'Hold gently', 1.0, phase, int(self.time // period) + 1
        if phase == 2:
            return 'Breathe out', 1 - smooth(fraction), phase, int(self.time // period) + 1
        return 'Rest a moment', 0.0, phase, int(self.time // period) + 1

    def enter(self, stage):
        self.stage = stage
        self.time = 0.0
        self.last_phase = None
        self.transition_age = 0.0
        self.ripples = []

    def tick(self, dt):
        if self.paused or self.stage in ('CHECKIN', 'AFTERCARE'):
            return
        previous = self.time
        self.time += dt
        self.transition_age = min(1.0, self.transition_age + dt / 2.0)
        if self.stage == 'BREATHE':
            cue, expansion, phase, cycle = self.breath()
            # One golden ripple at the start of each inhale and exhale.
            if phase != self.last_phase and phase in (0, 2):
                self.ripples.append(0.0)
            self.last_phase = phase
        self.ripples = [age + dt for age in self.ripples if age + dt < 1.5]
        if self.stage == 'INTRO' and self.time >= 4.0:
            self.enter('BREATHE')
            return
        if self.stage == 'ENCOURAGE' and self.time >= 3.5:
            self.enter('CHECKIN')
            return
        if self.time >= self.duration.get(self.stage, float('inf')):
            if self.stage == 'RESET':
                self.enter('CHECKIN')
            elif self.stage == 'WATCH':
                self.enter('ENCOURAGE')
            else:
                self.sequence_index += 1
                self.enter(self.sequence[self.sequence_index])

    def checkin(self, calmer):
        self.checkin_selection = calmer
        if calmer:
            self.enter('AFTERCARE')
        else:
            self.retries += 1
            self.enter('RESET')

    def cloud_scale(self):
        if self.stage == 'BREATHE':
            return 0.73 + 0.20 * self.breath()[1]
        if self.stage == 'WATCH':
            return 0.69 + 0.018 * math.sin(self.time * 0.52)
        if self.stage == 'RELEASE':
            return 0.86 - 0.17 * smooth(self.time / self.duration['RELEASE'])
        if self.stage == 'RESET':
            return 0.81 + 0.055 * math.sin(self.time * 0.43)
        return 0.84
