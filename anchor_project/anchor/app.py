"""Anchor screens. A single 420x840 canvas scales cleanly to phones and desktop."""
import calendar
import random
import math
from datetime import date
from pathlib import Path
import pygame

from .config import W, H, FPS, THEMES, NEEDS, HELPFUL, AVOIDS, GUIDANCE
from .storage import load, save, record_session
from .journey import Journey, smooth
from .audio import Soundscape
from .visuals import Painter, blend


class Anchor:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption('Anchor')
        self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.ui = Painter()
        self.settings = load()
        self.page = 'home' if self.settings['onboarded'] else 'welcome'
        self.onboarding_index = 0
        self.journey = None
        self.running = True
        self.elapsed = 0.0
        self.week_offset = 0
        self.previous_stage = None
        self.stage_blend = 1.0
        self.audio = Soundscape()
        if not self.audio.available:
            print('[Anchor] Audio unavailable. Check your system output device.')
        self.last_page = 'home'
        self.visual_stage = None
        self.visual_from = (210.0, 323.0, .83)
        self.visual_current = (210.0, 323.0, .83)
        self.visual_transition = 1.0
        self.page_transition = 1.0
        self.old_frame = None
        self.fade_layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self.last_drawn_stage = None
        self.chapter_frame = None
        self.chapter_transition = 1.0
        # White curtain: bottom -> top -> bottom, with one smooth parabola.
        self.curtain_time = 0.0
        self.curtain_duration = 1.9
        self.curtain_active = False
        self.curtain_old_frame = None
        self.curtain_target = None
        self.curtain_stage = None
        self.curtain_color = (252, 251, 248)
        self.soft_fade_time = 0.0
        self.soft_fade_duration = 0.34
        self.soft_fade_frame = None

    @property
    def palette(self):
        return THEMES[self.settings['theme']]

    def set_page(self, page):
        """Keep settings interactions immediate; animate only primary navigation.

        Replaying a captured frame over a changing theme caused ghosting and
        a visible flash. Settings subpages now switch cleanly in one frame.
        """
        if page == self.page or self.curtain_active:
            return
        self.soft_fade_frame = None
        self.soft_fade_time = self.soft_fade_duration
        main = {'home', 'progress', 'settings'}
        if self.page in main and page in main:
            self.begin_curtain(target_page=page)
        else:
            self.page = page

    def begin_curtain(self, target_page=None, target_stage=None):
        """Cover the current frame, switch content at the apex, then reveal."""
        if self.curtain_active:
            return
        self.curtain_old_frame = self.canvas.copy()
        self.curtain_time = 0.0
        self.curtain_active = True
        self.curtain_target = target_page
        self.curtain_stage = target_stage
        # A soft tint drawn from the active landscape, never a white flash.
        theme = self.palette
        self.curtain_color = blend(theme['bottom'], theme['accent'], 0.22)

    def tick_curtain(self, dt):
        if not self.curtain_active:
            return
        self.curtain_time = min(self.curtain_duration, self.curtain_time + dt)
        if self.curtain_target is not None and self.curtain_time >= self.curtain_duration / 2:
            self.page = self.curtain_target
            self.curtain_target = None
            self.stage_blend = 0.0
        if self.curtain_time >= self.curtain_duration:
            self.curtain_active = False
            self.curtain_old_frame = None
            self.curtain_stage = None

    def paint_curtain(self):
        """Theme-tinted curtain: buoyant rise, gentle settle, smooth retreat.

        The page swaps only while the curtain fully covers the canvas.
        A tiny, decaying wave at the leading edge adds personality without
        shaking or flashing the entire scene.
        """
        if not self.curtain_active:
            return
        t = min(1.0, self.curtain_time / self.curtain_duration)
        if t <= 0.5:
            u = t * 2.0
            # Ease-out-back gives a small bounce as the curtain reaches the top.
            c = 1.30
            rise = 1.0 + (c + 1.0) * (u - 1.0)**3 + c * (u - 1.0)**2
            coverage = max(0.0, min(1.0, rise))
            if self.curtain_old_frame is not None:
                self.canvas.blit(self.curtain_old_frame, (0, 0))
        else:
            u = (t - 0.5) * 2.0
            # Smooth descent: no sudden drop in velocity at the reversal.
            fall = u * u * (3.0 - 2.0 * u)
            coverage = 1.0 - fall

        top = H - round(H * coverage)
        if top >= H:
            return

        # Gentle curved edge, strongest in mid-flight and invisible at the ends.
        # Keep it entirely offscreen when fully covered to prevent reveal flashes.
        if 2 <= top <= H - 2 and not self.settings.get('reduced_motion', False):
            envelope = math.sin(math.pi * coverage)**2
            amplitude = 9.0 * envelope
            points = [(0, H)]
            for x in range(0, W + 9, 8):
                x = min(x, W)
                y = top + amplitude * math.sin((x / W) * 2.0 * math.pi + t * 3.0)
                points.append((x, max(0, min(H, round(y)))))
            points.append((W, H))
            pygame.draw.polygon(self.canvas, self.curtain_color, points)
        else:
            pygame.draw.rect(self.canvas, self.curtain_color, (0, top, W, H - top))

    def save(self):
        save(self.settings)

    def start(self):
        self.journey = Journey(self.settings)
        self.visual_stage = None
        self.visual_current = (210.0, 306.0, .80)
        self.visual_transition = 1.0
        self.last_drawn_stage = None
        self.set_page('session')
        self.start_audio()

    def start_audio(self):
        self.audio.start(self.settings.get('sound', False)
                         and 'Sounds or spoken guidance' not in self.settings.get('avoid', []))

    def play_input_sound(self):
        """Click feedback works on menus as well as inside a session."""
        if self.settings.get('sound', False) and 'Sounds or spoken guidance' not in self.settings.get('avoid', []):
            self.audio.enabled = self.audio.available
            self.audio.ui_click()

    def stop_audio(self):
        self.audio.stop()

    def finish_session(self):
        record_session(self.settings)
        self.stop_audio()
        self.journey = None
        self.curtain_active = False
        self.curtain_old_frame = None
        self.curtain_target = None
        self.page = 'home'
        self.soft_fade_frame = None

    def abandon_session(self):
        self.stop_audio()
        self.journey = None
        self.curtain_active = False
        self.curtain_old_frame = None
        self.curtain_target = None
        self.page = 'home'
        self.soft_fade_frame = None

    def finish_onboarding(self):
        self.settings['onboarded'] = True
        self.save()
        self.set_page('home')

    def skip_onboarding(self):
        self.finish_onboarding()

    def toggle(self, key, value, exclusive=None):
        selected = list(self.settings[key])
        if value == exclusive:
            selected = [] if selected == [value] else [value]
        else:
            selected = [item for item in selected if item != exclusive]
            if value in selected:
                selected.remove(value)
            else:
                selected.append(value)
        self.settings[key] = selected
        self.save()

    def heading(self, title, subtitle='', top=110, size=29):
        p = self.palette
        y = self.ui.text(self.canvas, title, W//2, top, size, p['ink'], True, 358, 3)
        if subtitle:
            self.ui.text(self.canvas, subtitle, W//2, y + 8, 14,
                         blend(p['ink'], p['bottom'], .16), max_width=350, max_lines=3)

    def topbar(self, label=''):
        p = self.palette
        font = self.ui.font(25, True)
        img = font.render('anchor.', True, p['ink'])
        self.canvas.blit(img, (26, 32))
        if label:
            img = self.ui.font(12, True).render(label.upper(), True, p['ink'])
            self.canvas.blit(img, (W-25-img.get_width(), 42))

    def navigation(self):
        p = self.palette
        # Fixed mobile bottom bar; content stops above y=715.
        self.ui.panel(self.canvas, (16, 744, 388, 78), 248)
        for i, (label, page) in enumerate((('Home','home'),('Progress','progress'),('Settings','settings'))):
            x = 25 + i*128
            selected = self.page == page
            nav_rect = pygame.Rect(x, 755, 116, 54)
            hovered = nav_rect.collidepoint(self.ui.hover_position)
            if hovered:
                self.ui.hovering = True
            if selected or hovered:
                tint = .82 if selected and not hovered else .68 if selected else .89
                self.ui.rounded(self.canvas, nav_rect,
                                blend(p['accent'], (255,255,255), tint), 16)
            text_color = p['accent'] if selected or hovered else p['ink']
            self.ui.text(self.canvas, label, x+58, 772, 15, text_color, selected, 112, 1)
            self.ui.actions.append((pygame.Rect(x, 755, 116, 54),
                                    lambda dest=page: self.set_page(dest)))

    def draw_welcome(self):
        self.topbar('welcome')
        self.ui.cloud(self.canvas, 210, 310, 1.0, self.palette, self.elapsed,
                      self.settings['reduced_motion'])
        self.ui.panel(self.canvas, (25, 465, 370, 136))
        self.heading('You deserve a gentle moment.',
                     'One little step at a time. No pressure to get it perfect.', 481, 26)
        self.ui.button(self.canvas, 'Personalize Anchor', (35, 632, 350, 62),
                       lambda: self.set_page('needs'), self.palette)
        self.ui.button(self.canvas, 'Skip setup', (105, 706, 210, 50),
                       self.skip_onboarding, self.palette, False)

    def draw_onboarding(self):
        pages = [
            ('needs', 'When things feel like too much, what happens?',
             'Select anything familiar.', NEEDS, 'needs', "I'm not really sure"),
            ('helpful', 'What helps you feel grounded?',
             'Select as many as you like.', HELPFUL, 'helpful', 'I am still figuring that out'),
            ('avoid', 'Anything you would rather avoid?',
             'Optional. Your boundaries matter.', AVOIDS, 'avoid', 'Nothing in particular'),
        ]
        index = next(i for i, page in enumerate(pages) if page[0] == self.page)
        _, title, subtitle, options, key, exclusive = pages[index]
        self.topbar(f'{index+1} / 5')
        self.heading(title, subtitle, 101, 24)
        top = 251 if len(options) == 6 else 262
        gap = 65 if len(options) == 6 else 70
        for i, label in enumerate(options):
            self.ui.button(self.canvas, label, (30, top+i*gap, 360, 53),
                           lambda answer=label: self.toggle(key, answer, exclusive),
                           self.palette, False, label in self.settings[key])
        next_page = ['helpful', 'avoid', 'guidance'][index]
        self.ui.button(self.canvas, 'Continue', (30, 688, 238, 60),
                       lambda dest=next_page: self.set_page(dest), self.palette)
        self.ui.button(self.canvas, 'Skip', (281, 692, 109, 52),
                       lambda dest=next_page: self.set_page(dest), self.palette, False)
        self.ui.button(self.canvas, 'Start now', (122, 767, 176, 42),
                       self.skip_onboarding, self.palette, False)

    def draw_guidance(self):
        self.topbar('4 / 5')
        self.heading('How should I guide you?', 'You can change this anytime.', 117)
        for i, label in enumerate(GUIDANCE):
            self.ui.button(self.canvas, label, (28, 272+i*86, 364, 66),
                           lambda choice=label: self.choose_guidance(choice),
                           self.palette, False, label == self.settings['guidance'])
        self.ui.panel(self.canvas, (30, 554, 360, 79))
        self.ui.text(self.canvas, 'One gentle instruction at a time.', 210, 573, 16,
                     self.palette['ink'], max_width=335)
        self.ui.button(self.canvas, 'Continue', (30, 685, 360, 62),
                       lambda: self.set_page('theme'), self.palette)
        self.ui.button(self.canvas, 'Start now', (120, 768, 180, 44),
                       self.skip_onboarding, self.palette, False)

    def choose_guidance(self, value):
        self.settings['guidance'] = value
        self.save()

    def draw_theme(self):
        self.topbar('5 / 5')
        self.heading('Make Anchor yours.', 'Choose a landscape to come home to.', 112)
        for i, (name, theme) in enumerate(THEMES.items()):
            x, y = 25+(i%2)*192, 267+(i//2)*175
            r = pygame.Rect(x, y, 179, 157)
            self.ui.rounded(self.canvas, r, theme['bottom'], 19)
            pygame.draw.circle(self.canvas, theme['sky'], (x+90,y+59), 47)
            pygame.draw.ellipse(self.canvas, theme['hill2'], (x+5,y+70,170,70))
            pygame.draw.ellipse(self.canvas, theme['hill'], (x+85,y+86,100,57))
            self.ui.text(self.canvas, name, x+90, y+133, 14, theme['ink'], True, 164, 1)
            if self.settings['theme'] == name:
                pygame.draw.rect(self.canvas, theme['accent'], r, 4, border_radius=19)
            self.ui.actions.append((r, lambda chosen=name: self.select_theme(chosen)))
        self.ui.button(self.canvas, 'Finish setup', (30, 684, 360, 64),
                       self.finish_onboarding, self.palette)

    def select_theme(self, name):
        if name == self.settings['theme']:
            return
        self.settings['theme'] = name
        self.soft_fade_frame = None
        self.save()

    def draw_home(self):
        self.topbar()
        self.ui.cloud(self.canvas, 210, 304, 1.04, self.palette, self.elapsed,
                      self.settings['reduced_motion'])
        self.ui.panel(self.canvas, (24, 464, 372, 126))
        self.heading('A moment just for you.',
                     'You can begin whenever you are ready.', 482, 27)
        self.ui.button(self.canvas, 'START GROUNDING', (35, 615, 350, 78),
                       self.start, self.palette)
        self.navigation()

    def stage_words(self, j):
        if j.stage == 'BREATHE':
            cue, _, _, cycle = j.breath()
            return cue, f'Cycle {min(cycle,j.cycles)} of {j.cycles}'
        if j.stage == 'RELEASE':
            return 'Release', 'Watch the lightness unfold.'
        if j.stage == 'WATCH':
            return 'Follow', 'Let your eyes rest here.'
        if j.stage == 'RESET':
            return 'Stay', 'Listen to the calming music, if you have it playing.'
        return '', ''

    def draw_session(self):
        j, p = self.journey, self.palette
        self.topbar('your moment')
        self.ui.button(self.canvas, 'Leave', (304, 82, 88, 40),
                       self.abandon_session, p, False)
        self.ui.button(self.canvas, 'Resume' if j.paused else 'Pause',
                       (28, 82, 94, 40), self.toggle_pause, p, False)
        if j.stage == 'INTRO':
            self.draw_intro()
            return
        if j.stage == 'ENCOURAGE':
            self.draw_encouragement()
            return
        if j.stage == 'CHECKIN':
            self.draw_checkin()
            return
        if j.stage == 'AFTERCARE':
            self.draw_aftercare()
            return

        # All stages use the same art bounds: x=30..390, y=160..475.
        # The cloud stays in the same scene and eases into new movement.
        progress = min(1, j.time / j.duration[j.stage])
        x, y = 210.0, 323.0
        entry = smooth(min(1, j.time / 2.3))
        if (j.stage == 'WATCH' and not self.settings['reduced_motion']
                and 'Following moving objects' not in self.settings['avoid']):
            # Fill the entire safe illustration area, rather than a small orbit.
            # Figure-eight: wide horizontal sweep, smooth vertical crossover.
            x += 124 * math.sin(j.time * .41) * entry
            y += 89 * math.sin(j.time * .82) * entry
        if j.stage == 'RESET':
            x += 20 * math.sin(j.time*.18) * entry
        scale = j.cloud_scale()
        # The chapter handoff below interpolates from the actual previous pose.
        # Do not reset scale here: Release should finish small and Watch stay small.
        if self.settings['reduced_motion']:
            x, y = 210, 323
            if j.stage != 'BREATHE':
                scale = j.cloud_scale()
        # Follow a continuous position, never restart a stage-local tween.
        # The target can jump when a chapter changes; the visible cloud cannot.
        x, y, scale = self.follow_cloud(x, y, scale)
        if j.stage == 'BREATHE':
            pygame.draw.circle(self.canvas, blend(p['accent'],p['bottom'],.45),
                               (round(x),round(y)), int(117+22*j.breath()[1]), 3)
            for age in j.ripples:
                self.ui.ripple(self.canvas,x,y,age)
        elif j.stage == 'RELEASE':
            for i in range(16):
                seed = i * 2.399
                fraction = ((j.time*.052 + i/16) % 1)
                angle = seed
                px = 210 + math.cos(angle) * (87+fraction*96)
                py = 322 + math.sin(angle) * (68+fraction*73) - fraction*38
                color = blend(p['accent'],p['bottom'],.2+.7*fraction)
                pygame.draw.circle(self.canvas,color,(int(px),int(py)),max(2,int(7*(1-fraction))))
        elif (j.stage == 'WATCH' and not self.settings['reduced_motion']
              and 'Following moving objects' not in self.settings['avoid']):
            for i in range(5):
                px = 210 + 124*math.sin(max(0,j.time-i*.17)*.41)*entry
                py = 323 + 89*math.sin(max(0,j.time-i*.17)*.82)*entry
                pygame.draw.circle(self.canvas,blend(p['accent'],p['bottom'],.70+i*.045),
                                   (int(px),int(py)),max(2,5-i))
        self.ui.cloud(self.canvas,x,y,scale,p,self.elapsed,self.settings['reduced_motion'],
                      expression=('inhale' if j.stage == 'BREATHE' and j.breath()[2] == 0
                                  else 'exhale' if j.stage == 'BREATHE' and j.breath()[2] == (1 if j.hold_free else 2)
                                  else 'rest' if j.stage == 'BREATHE' else 'smile'))

        # Story chapter appears inside its own strip, away from the main cue.
        stage_title = 'STAY' if j.stage == 'RESET' else j.stage
        # A restrained chapter-label fade, not another screen-covering curtain.
        # Cloud movement remains uninterrupted between journey chapters.
        chapter_reveal = smooth(min(1.0, j.time / 1.1))
        title_color = blend(p['bottom'], p['ink'], .15 + .85*chapter_reveal)
        self.ui.text(self.canvas,stage_title,210,160,14,title_color,True,300,1)
        self.ui.panel(self.canvas,(25,522,370,134),245)
        heading, supporting = self.stage_words(j)
        # Breathing cue grows and shrinks, but within a fixed 33px maximum.
        cue_size = 25
        if j.stage == 'BREATHE':
            cue_size += round(7*j.breath()[1])
        cue_color = blend(p['bottom'], p['ink'], .32 + .68*chapter_reveal)
        self.ui.text(self.canvas,heading,210,539,cue_size,cue_color,True,336,1)
        self.ui.text(self.canvas,supporting,210,589,15,p['ink'],max_width=326,max_lines=2)
        if j.stage == 'BREATHE' and j.hold_free:
            self.ui.text(self.canvas,'No breath holds',210,635,11,p['ink'],max_width=300)
        # Gentle progress line, not a demand or a score.
        pygame.draw.rect(self.canvas,blend(p['ink'],p['bottom'],.83),(42,689,336,4),border_radius=3)
        pygame.draw.rect(self.canvas,p['accent'],(42,689,int(336*progress),4),border_radius=3)
        self.ui.text(self.canvas,'You can pause or leave at any time.',210,717,13,p['ink'],max_width=350)
        if j.paused:
            self.ui.panel(self.canvas,(78,370,264,64),252)
            self.ui.text(self.canvas,'Paused',210,387,24,p['ink'],True)

    def follow_cloud(self, target_x, target_y, target_scale):
        """Frame-rate independent, gentle pursuit of a new cloud pose.

        Every chapter uses the SAME tracked pose, including the interludes.
        This prevents teleports when stage-local clocks restart at zero.
        """
        dt = max(0.0, min(0.05, getattr(self, 'frame_dt', 1 / 60)))
        # A small time constant keeps motion responsive but cinematic.
        position_mix = 1.0 - math.exp(-dt / 0.68)
        size_mix = 1.0 - math.exp(-dt / 0.85)
        old_x, old_y, old_scale = self.visual_current
        pose = (old_x + (target_x - old_x) * position_mix,
                old_y + (target_y - old_y) * position_mix,
                old_scale + (target_scale - old_scale) * size_mix)
        self.visual_current = pose
        return pose

    def draw_intro(self):
        p = self.palette
        t = self.journey.time
        x, y, size = self.follow_cloud(210, 306, .76 + .055*math.sin(t*1.5))
        self.ui.cloud(self.canvas, x, y, size,
                      p, self.elapsed, self.settings['reduced_motion'], expression='excited')
        self.ui.panel(self.canvas, (25, 510, 370, 125), 242)
        self.ui.text(self.canvas, "Let's go, gently.", 210, 530, 27,
                     p['ink'], True, 340, 1)
        self.ui.text(self.canvas, 'One little moment at a time.', 210, 586, 16,
                     p['ink'], max_width=330, max_lines=2)

    def draw_encouragement(self):
        p = self.palette
        x, y, size = self.follow_cloud(210, 307, .83)
        self.ui.cloud(self.canvas, x, y, size, p, self.elapsed,
                      self.settings['reduced_motion'], expression='proud')
        self.ui.panel(self.canvas, (25, 500, 370, 145), 244)
        self.ui.text(self.canvas, 'A moment for you', 210, 520, 15,
                     p['accent'], True, 320, 1)
        self.ui.text(self.canvas, self.journey.encouragement, 210, 561, 24,
                     p['ink'], True, 330, 2)
        # A quiet transition, not a loading spinner or a fake progress bar.

    def draw_checkin(self):
        p = self.palette
        x, y, size = self.follow_cloud(210, 302, .86)
        self.ui.cloud(self.canvas,x,y,size,p,self.elapsed,self.settings['reduced_motion'], expression='kind')
        self.ui.panel(self.canvas,(24,462,372,124),246)
        self.heading('How are you feeling now?',
                     'You do not have to feel completely calm.',481,25)
        self.ui.button(self.canvas,'A little calmer',(30,609,360,57),
                       lambda: self.journey.checkin(True),p)
        self.ui.button(self.canvas,'Not yet',(30,679,360,57),
                       lambda: self.journey.checkin(False),p,False)
        self.ui.text(self.canvas,'Either answer is okay.',210,760,14,p['ink'])

    def draw_aftercare(self):
        p = self.palette
        x, y, size = self.follow_cloud(210, 289, .91)
        self.ui.cloud(self.canvas,x,y,size,p,self.elapsed,self.settings['reduced_motion'], expression='proud')
        self.ui.panel(self.canvas,(24,451,372,190),245)
        self.heading('A little kindness to take with you.',
                     'Unclench your hands if you like. Take your time getting up. A sip of water or a quiet moment can come next.',
                     466,23)
        self.ui.button(self.canvas,'Finish my moment',(30,676,360,64),
                       self.finish_session,p)
        self.ui.text(self.canvas,'You can return whenever you need.',210,757,13,p['ink'])

    def toggle_pause(self):
        if self.journey is not None:
            self.journey.paused = not self.journey.paused

    def draw_progress(self):
        self.topbar('progress')
        p = self.palette
        self.heading('Your little moments.',
                     'Every moment you made for yourself counts.', 108, 27)
        today = date.today()
        # Monday-based week; navigate whole weeks, not months.
        from datetime import timedelta
        monday = today - timedelta(days=today.weekday()) + timedelta(weeks=self.week_offset)
        sunday = monday + timedelta(days=6)
        self.ui.panel(self.canvas, (20, 239, 380, 315), 246)
        label = (f'{monday.strftime("%b %d")} – {sunday.strftime("%b %d, %Y")}')
        self.ui.text(self.canvas, label, 210, 265, 19, p['ink'], True, 245, 1)
        self.ui.button(self.canvas, '<', (34, 254, 43, 44),
                       lambda: self.change_week(-1), p, False)
        self.ui.button(self.canvas, '>', (343, 254, 43, 44),
                       lambda: self.change_week(1), p, False)
        for i in range(7):
            day = monday + timedelta(days=i)
            x = 51 + i*53
            count = max(0, int(self.settings['history'].get(day.isoformat(), 0)))
            self.ui.text(self.canvas, day.strftime('%a')[0], x, 336, 13,
                         p['ink'], True, 42, 1)
            if count:
                pygame.draw.circle(self.canvas, p['accent'], (x, 400), 21)
            else:
                pygame.draw.circle(self.canvas,
                    blend(p['accent'], p['bottom'], .79), (x, 400), 21)
            color = (255,255,255) if count else p['ink']
            self.ui.text(self.canvas, str(day.day), x, 390, 17,
                         color, True, 43, 1)
            self.ui.text(self.canvas, str(count) if count else '·', x, 454, 17,
                         p['accent'] if count else p['ink'], bool(count), 40, 1)
        self.ui.text(self.canvas, 'Sessions per day', 210, 499, 13,
                     p['ink'], max_width=300, max_lines=1)
        week_count = sum(max(0, int(self.settings['history'].get(
            (monday + timedelta(days=i)).isoformat(), 0))) for i in range(7))
        total = sum(max(0, int(v)) for v in self.settings['history'].values())
        self.ui.panel(self.canvas, (22, 577, 376, 135), 245)
        self.ui.text(self.canvas, f'{week_count} this week', 210, 596, 25,
                     p['ink'], True, 330, 1)
        self.ui.text(self.canvas, f'{total} grounding moments in total',
                     210, 654, 15, p['ink'], max_width=330, max_lines=1)
        self.navigation()

    def change_week(self, amount):
        self.week_offset += amount

    def draw_settings(self):
        self.topbar('settings')
        self.heading('Make this space yours.', 'All preferences stay on your device.',110,27)
        rows = [
            ('Theme',self.settings['theme'],lambda:self.set_page('theme_settings')),
            ('Reduced motion','On' if self.settings['reduced_motion'] else 'Off',lambda:self.flip('reduced_motion')),
            ('Ambient sound','On' if self.settings['sound'] else 'Off',lambda:self.flip('sound')),
            ('Comfort preferences','Edit',lambda:self.set_page('avoid_settings')),
            ('Replay onboarding','Start',lambda:self.set_page('welcome')),
            ('Emergency resources','View',lambda:self.set_page('resources')),
        ]
        for i,(label,value,action) in enumerate(rows):
            y = 245+i*72
            self.ui.panel(self.canvas,(22,y,376,61),249)
            font=self.ui.font(16,True)
            img=font.render(label,True,self.palette['ink'])
            self.canvas.blit(img,(37,y+21))
            # Value is right-aligned and clipped by available width.
            size=14
            while self.ui.font(size).size(value)[0] > 143 and size > 11:
                size-=1
            img=self.ui.font(size).render(value,True,self.palette['accent'])
            self.canvas.blit(img,(383-img.get_width(),y+22))
            self.ui.actions.append((pygame.Rect(22,y,376,61),action))
        self.navigation()

    def flip(self,key):
        self.settings[key]=not self.settings[key]
        self.save()
        if key == 'sound':
            if self.settings[key]:
                self.audio.enabled = self.audio.available
                self.audio.preview_click()
            else:
                self.audio.stop()

    def draw_theme_settings(self):
        self.topbar('appearance')
        self.heading('Your landscape.', 'Tap a theme to preview it instantly.', 112, 27)
        for i, (name, theme) in enumerate(THEMES.items()):
            x, y = 25+(i%2)*192, 260+(i//2)*177
            r = pygame.Rect(x, y, 179, 157)
            self.ui.rounded(self.canvas, r, theme['bottom'], 19)
            pygame.draw.circle(self.canvas, theme['sky'], (x+90,y+59), 47)
            pygame.draw.ellipse(self.canvas, theme['hill2'], (x+5,y+70,170,70))
            pygame.draw.ellipse(self.canvas, theme['hill'], (x+85,y+86,100,57))
            self.ui.text(self.canvas, name, x+90, y+133, 14, theme['ink'], True, 164, 1)
            if self.settings['theme'] == name:
                pygame.draw.rect(self.canvas, theme['accent'], r, 4, border_radius=19)
            if r.collidepoint(self.ui.hover_position):
                self.ui.hovering = True
                pygame.draw.rect(self.canvas, theme['accent'], r, 2, border_radius=19)
            self.ui.actions.append((r, lambda chosen=name: self.select_theme(chosen)))
        self.ui.button(self.canvas, 'Done', (30, 686, 360, 60),
                       lambda: self.set_page('settings'), self.palette)

    def draw_avoid_settings(self):
        self.topbar('comfort')
        self.heading('Anything to avoid?', 'Your comfort comes first.',111,27)
        for i,label in enumerate(AVOIDS):
            self.ui.button(self.canvas,label,(30,254+i*62,360,51),
                           lambda value=label:self.toggle('avoid',value,'Nothing in particular'),
                           self.palette,False,label in self.settings['avoid'])
        self.ui.button(self.canvas,'Done',(30,676,360,60),
                       lambda:self.set_page('settings'),self.palette)

    def draw_resources(self):
        self.topbar('resources')
        self.ui.panel(self.canvas,(22,198,376,380),245)
        self.heading('If you need urgent help',
                     'Anchor is a grounding tool, not an emergency service.',225,26)
        p=self.palette
        self.ui.text(self.canvas,'In the United States:',210,357,18,p['ink'],True)
        self.ui.text(self.canvas,'Call 911 for immediate danger.',210,405,17,p['ink'])
        self.ui.text(self.canvas,'Call or text 988 for crisis support.',210,466,17,p['ink'])
        self.ui.button(self.canvas,'Back to settings',(30,651,360,62),
                       lambda:self.set_page('settings'),p)

    def draw(self):
        self.ui.hover_position = self.to_canvas(pygame.mouse.get_pos())
        self.ui.hovering = False
        self.ui.actions=[]
        p=self.palette
        self.ui.background(self.canvas,p,self.elapsed,self.settings['reduced_motion'])
        if self.page == 'welcome':self.draw_welcome()
        elif self.page in ('needs','helpful','avoid'):self.draw_onboarding()
        elif self.page == 'guidance':self.draw_guidance()
        elif self.page == 'theme':self.draw_theme()
        elif self.page == 'home':self.draw_home()
        elif self.page == 'session' and self.journey is not None:self.draw_session()
        elif self.page == 'progress':self.draw_progress()
        elif self.page == 'settings':self.draw_settings()
        elif self.page == 'theme_settings':self.draw_theme_settings()
        elif self.page == 'avoid_settings':self.draw_avoid_settings()
        elif self.page == 'resources':self.draw_resources()
        # Chapter changes are continuous: no curtain or flashing overlay.
        # The existing cloud-pose interpolation handles the gentle handoff.
        self.last_drawn_stage = self.journey.stage if self.page == 'session' and self.journey else None
        # Settings and onboarding subpages render directly: no ghost frames.
        self.paint_curtain()
        # Letterbox to preserve the phone aspect ratio on a desktop window.
        screen_w,screen_h=self.screen.get_size()
        scale=min(screen_w/W,screen_h/H)
        target_w,target_h=round(W*scale),round(H*scale)
        self.screen.fill((24,36,48))
        if target_w and target_h:
            picture=pygame.transform.smoothscale(self.canvas,(target_w,target_h))
            self.screen.blit(picture,((screen_w-target_w)//2,(screen_h-target_h)//2))
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self.ui.hovering
                                else pygame.SYSTEM_CURSOR_ARROW)
        pygame.display.flip()

    def to_canvas(self,pos):
        sw,sh=self.screen.get_size()
        scale=min(sw/W,sh/H)
        if scale <= 0:return (-1,-1)
        x=(pos[0]-(sw-W*scale)/2)/scale
        y=(pos[1]-(sh-H*scale)/2)/scale
        return (int(x),int(y))

    def run(self):
        while self.running:
            dt=min(self.clock.tick(FPS)/1000,.05)
            self.elapsed+=dt
            self.frame_dt=dt
            self.tick_curtain(dt)
            if self.page=='session' and self.journey and not self.curtain_active:
                self.journey.tick(dt)
                self.audio.update(self.journey, self.settings, dt)
            for event in pygame.event.get():
                if event.type==pygame.QUIT:self.running=False
                elif event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                    if self.page=='session':self.abandon_session()
                    elif self.page not in ('home','welcome'):self.set_page('home')
                elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    if self.curtain_active:
                        continue
                    action=self.ui.hit(self.to_canvas(event.pos))
                    if action:
                        self.play_input_sound()
                        action()
                elif event.type==pygame.FINGERDOWN:
                    if self.curtain_active:
                        continue
                    pos=(event.x*self.screen.get_width(),event.y*self.screen.get_height())
                    action=self.ui.hit(self.to_canvas(pos))
                    if action:
                        self.play_input_sound()
                        action()
            self.draw()
        self.stop_audio()
        pygame.quit()
