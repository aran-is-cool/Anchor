"""Phone-sized illustration, readable typography and simple touch targets."""
import math
import os
import pygame
from .config import W, H
from .journey import smooth


def blend(a, b, t):
    t = max(0, min(1, t))
    return tuple(round(x + (y-x)*t) for x, y in zip(a, b))


class Painter:
    def __init__(self):
        self.fonts = {}
        self.font_name = self._font_name()
        self.actions = []
        self.hover_position = (-1, -1)
        self.hovering = False

    def _font_name(self):
        # The reference uses a heavy, geometric display sans. Inter Display
        # is preferred; no font files are required or redistributed.
        for name in ('Inter Display', 'Inter', 'Aptos Display',
                     'Segoe UI', 'Arial', 'DejaVu Sans'):
            match = pygame.font.match_font(name)
            if match:
                return match
        return None

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            font = pygame.font.Font(self.font_name, size) if self.font_name else pygame.font.Font(None, size)
            font.set_bold(bold)
            self.fonts[key] = font
        return self.fonts[key]

    def text(self, surface, content, center_x, top, size, color, bold=False,
             max_width=360, max_lines=3, line_gap=4):
        """Render centered text inside a fixed width, with a guaranteed line limit.

        Long labels shrink until they fit; remaining overflow is ellipsized.
        This prevents drawing over adjacent cards or outside the viewport.
        """
        content = str(content)
        size = max(11, int(size))
        for candidate_size in range(size, 10, -1):
            font = self.font(candidate_size, bold)
            words = content.split()
            lines, line = [], ''
            for word in words:
                candidate = (line + ' ' + word).strip()
                if font.size(candidate)[0] <= max_width:
                    line = candidate
                else:
                    if line:
                        lines.append(line)
                        line = ''
                    if font.size(word)[0] <= max_width:
                        line = word
                    else:
                        # Rare unbroken text: fit character by character.
                        part = ''
                        for char in word:
                            if font.size(part + char)[0] > max_width and part:
                                lines.append(part)
                                part = ''
                            part += char
                        line = part
            if line:
                lines.append(line)
            if len(lines) <= max_lines:
                break
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            while last and font.size(last + '…')[0] > max_width:
                last = last[:-1]
            lines[-1] = last.rstrip() + '…'
        for line in lines:
            image = font.render(line, True, color)
            surface.blit(image, (round(center_x-image.get_width()/2), round(top)))
            top += font.get_linesize() + line_gap
        return top

    def rounded(self, surface, rect, color, radius=18, width=0):
        pygame.draw.rect(surface, color, rect, width, border_radius=radius)

    def button(self, surface, label, rect, callback, palette, primary=True, selected=False):
        r = pygame.Rect(rect)
        hovered = r.collidepoint(self.hover_position)
        if hovered:
            self.hovering = True
        fill = palette['accent'] if primary or selected else (255, 253, 249)
        if hovered:
            fill = blend(fill, (255, 255, 255) if primary or selected else palette['accent'], .17 if primary or selected else .11)
        self.rounded(surface, r, fill, min(22, r.h//3))
        if not primary and not selected:
            pygame.draw.rect(surface, blend(palette['accent'], (255,255,255), .55), r, 2,
                             border_radius=min(22, r.h//3))
        if hovered:
            pygame.draw.rect(surface, blend(palette['accent'], (255, 255, 255), .32), r, 2,
                             border_radius=min(22, r.h//3))
        color = (255,255,255) if primary or selected else palette['ink']
        size = 18 if r.h >= 55 else 15
        while self.font(size, True).size(label)[0] > r.w - 26 and size > 12:
            size -= 1
        img = self.font(size, True).render(label, True, color)
        surface.blit(img, img.get_rect(center=r.center))
        self.actions.append((r, callback))

    def hit(self, position):
        for rect, callback in reversed(self.actions):
            if rect.collidepoint(position):
                return callback
        return None

    def background(self, surface, palette, t, reduced=False):
        """Slow parallax landscape. More presence, never flashing or jittering."""
        for y in range(0, H, 4):
            pygame.draw.rect(surface, blend(palette['sky'], palette['bottom'], y/H), (0,y,W,5))
        motion = 0 if reduced else 1
        # Gentle sun / moon glow, with slow concentric atmospheric halos.
        halo = pygame.Surface((W,H), pygame.SRCALPHA)
        pulse = math.sin(t*.22)*6*motion
        for radius, alpha in ((118,15),(94,20),(70,32)):
            pygame.draw.circle(halo, (255,247,214,alpha), (314,192), round(radius+pulse))
        surface.blit(halo,(0,0))
        pygame.draw.circle(surface, blend(palette['bottom'], (255,242,183), .52), (314,192), 53)
        # Three independent, softly animated layers make the scene feel alive.
        far = math.sin(t*.23)*13*motion
        mid = math.sin(t*.31+1.1)*11*motion
        near = math.sin(t*.18+2.0)*8*motion
        pygame.draw.ellipse(surface, blend(palette['hill2'],palette['bottom'],.32),
                            (-170+round(far), 480, 560, 290))
        pygame.draw.ellipse(surface, palette['hill2'],
                            (-185+round(mid), 551, 530, 320))
        pygame.draw.ellipse(surface, palette['hill'],
                            (168+round(-mid*.75), 569, 470, 290))
        pygame.draw.ellipse(surface, blend(palette['bottom'],palette['hill2'],.18),
                            (-45+round(near), 701, 540, 180))
        # Floating distant motes: slow, tiny, and outside the text-heavy region.
        if not reduced:
            for i in range(7):
                x = 24+i*62+6*math.sin(t*.27+i)
                y = 220+(i%3)*61+9*math.sin(t*.37+i*1.9)
                color = blend(palette['bottom'],palette['accent'],.20)
                pygame.draw.circle(surface,color,(round(x),round(y)),2+(i%2))

    def cloud(self, surface, x, y, scale, palette, t, reduced=False, expression='smile'):
        """The companion expresses the breathing cue without distracting motion."""
        if not reduced:
            y += 3 * math.sin(t)
        shadow = pygame.Surface((280, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (46, 48, 55, 24), (32, 20, 216, 22))
        surface.blit(shadow, (int(x - 140), int(y + 70 * scale)))

        def circle(dx, dy, radius, color):
            pygame.draw.circle(surface, color,
                               (round(x + dx * scale), round(y + dy * scale)),
                               max(1, round(radius * scale)))

        edge = blend(palette['cloud'], palette['ink'], .12)
        lobes = [(-67, 13, 46), (-31, -18, 55), (25, -25, 59), (73, 10, 47), (0, 28, 68)]
        for dx, dy, r in lobes:
            circle(dx, dy, r + 2, edge)
        for dx, dy, r in lobes:
            circle(dx, dy, r, palette['cloud'])

        ink = palette['ink']
        # Inhale: eyes gently open, surprised little O-mouth.
        # Exhale: relaxed closed eyes, tiny peaceful smile.
        # Rest: neutral, closed eyes. Intro: happy excited expression.
        if expression in ('exhale', 'rest', 'proud'):
            for ex in (-28, 30):
                eye_rect = pygame.Rect(round(x + (ex - 9) * scale),
                                       round(y + 13 * scale),
                                       max(3, round(18 * scale)), max(3, round(12 * scale)))
                pygame.draw.arc(surface, ink, eye_rect, math.pi, 2 * math.pi,
                                max(2, round(3 * scale)))
        elif expression in ('excited', 'inhale'):
            # Wide, expressive eyes. On inhale the cloud looks gently curious;
            # during the intro it perks up with a tiny animated sparkle.
            eye_radius = 6.0 if expression == 'inhale' else 5.2
            for ex in (-28, 30):
                circle(ex, 17, eye_radius, ink)
                circle(ex - 1.6, 14.8, 1.9, palette['cloud'])
            if expression == 'excited' and not reduced:
                lift = 3.0 * math.sin(t * 2.4)
                circle(64, -40 + lift, 3.3, palette['accent'])
        else:
            circle(-28, 17, 3.7, ink)
            circle(30, 17, 3.7, ink)

        if expression == 'inhale':
            # Small round inhaling mouth, not an exaggerated gasp.
            pygame.draw.ellipse(surface, ink,
                                (round(x - 5 * scale), round(y + 25 * scale),
                                 max(3, round(10 * scale)), max(3, round(13 * scale))))
        elif expression == 'exhale':
            # A longer, relaxed smile accompanies the slow exhale.
            pygame.draw.arc(surface, ink,
                            (round(x - 17 * scale), round(y + 18 * scale),
                             max(5, round(34 * scale)), max(4, round(21 * scale))),
                            math.pi, 2 * math.pi, max(2, round(3 * scale)))
        elif expression == 'rest':
            pygame.draw.line(surface, ink,
                             (round(x - 8 * scale), round(y + 30 * scale)),
                             (round(x + 8 * scale), round(y + 30 * scale)),
                             max(2, round(2 * scale)))
        else:
            height = 21 if expression in ('excited', 'proud') else 15
            pygame.draw.arc(surface, ink,
                            (round(x - 12 * scale), round(y + 20 * scale),
                             max(4, round(24 * scale)), max(4, round(height * scale))),
                            math.pi, 2 * math.pi, max(2, round(3 * scale)))
        blush = blend(palette['accent'], palette['cloud'], .65)
        circle(-47, 29, 8, blush)
        circle(50, 29, 8, blush)

    def panel(self, surface, rect, alpha=230):
        r = pygame.Rect(rect)
        layer = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (255,253,248,alpha), layer.get_rect(), border_radius=23)
        surface.blit(layer, r.topleft)

    def ripple(self, surface, x, y, age):
        # Transparent golden ring expanding outward from the cloud.
        layer = pygame.Surface((W, H), pygame.SRCALPHA)
        opacity = round(175 * (1 - age/1.5))
        radius = round(105 + age * 72)
        pygame.draw.circle(layer, (255,193,57,max(0,opacity)), (int(x),int(y)),radius,4)
        surface.blit(layer,(0,0))
