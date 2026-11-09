"""
HUD: información superpuesta, dibujada con Pillow en una textura.

Se redibuja unas 8 veces por segundo (no hace falta más para texto). Todos los textos
salen del traductor (ui/i18n.py), así que cambian al momento con la tecla L.
"""
import math

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from viewer import scale

FONT_CANDIDATES = ["consola.ttf", "CascadiaMono.ttf", "DejaVuSansMono.ttf",
                   "LiberationMono-Regular.ttf", "Menlo.ttc"]

DEPTH_MARKS = [(1.5e-10, "atom"), (5e-15, "nucleus"), (8.4e-16, "proton"), (1e-18, "quarks")]
BAR_TOP, BAR_BOTTOM = 1e-8, 1e-19
MODE_COLORS = {"didactic": (255, 210, 120, 255), "realistic": (140, 230, 200, 255),
               "plastic": (255, 140, 170, 255)}

VERT = """#version 330
in vec2 in_pos; out vec2 v_uv;
void main(){ v_uv = vec2(in_pos.x*0.5+0.5, 0.5-in_pos.y*0.5); gl_Position = vec4(in_pos,0,1); }"""
FRAG = """#version 330
uniform sampler2D tex; in vec2 v_uv; out vec4 f;
void main(){ f = texture(tex, v_uv); }"""


def _font(size):
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


class HUD:
    def __init__(self, ctx: moderngl.Context, tr):
        self.ctx = ctx
        self.tr = tr
        self.prog = ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
        quad = np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4")
        self.vbo = ctx.buffer(quad.tobytes())
        self.vao = ctx.vertex_array(self.prog, [(self.vbo, "2f", "in_pos")])
        self.tex = None
        self.size = (0, 0)
        self.show_help = True
        self.message = ""
        self.message_until = 0.0
        self._fonts = {}

    def flash(self, text, now, seconds=2.5):
        self.message, self.message_until = text, now + seconds

    def fonts(self, k):
        key = round(k, 2)
        if key not in self._fonts:
            self._fonts[key] = (_font(int(22 * k)), _font(int(16 * k)), _font(int(13 * k)))
        return self._fonts[key]

    # ------------------------------------------------------------ composición
    def compose(self, st: dict, w: int, h: int, now: float) -> Image.Image:
        tr = self.tr
        dec = tr.dec
        k = max(h / 900, 0.75)
        f_big, f, f_small = self.fonts(k)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        pad = int(16 * k)
        lh = int(21 * k)

        # --- panel superior izquierdo
        lvl = st["level"]
        lines = [
            (f_big, tr.t("viewer.hud.level", n=lvl.depth + 1, name=lvl.name), (255, 255, 255, 255)),
            (f, tr.t("viewer.hud.visible", width=scale.length(st["visible_width_m"], dec),
                     sci=tr.sci(st["visible_width_m"])), (190, 215, 255, 255)),
            (f, tr.t("viewer.hud.distance", d=scale.length(st["depth_m"], dec)), (190, 215, 255, 255)),
            (f, tr.t("viewer.hud.speed", v=scale.length(st["speed_m_s"], dec),
                     mult=f"{st['speed_mult']:.2g}".replace(".", dec)), (190, 215, 255, 255)),
            (f_small, tr.t("viewer.hud.time", t=st["time"]), (150, 170, 200, 255)),
            (f_small, tr.t(f"viewer.hud.mode_{st['mode']}"), MODE_COLORS[st["mode"]]),
        ]
        y = pad
        box_w = max(int(560 * k), int(max(d.textlength(t, font=fo) for fo, t, _ in lines)) + pad)
        d.rounded_rectangle([pad // 2, pad // 2, pad + box_w, pad + lh * len(lines) + lh // 2],
                            radius=int(8 * k), fill=(5, 10, 25, 150))
        for font, text, col in lines:
            d.text((pad, y), text, font=font, fill=col)
            y += lh + (6 if font is f_big else 0)

        # --- objeto delante
        foc = st["focus"]
        if foc:
            y += lh // 2
            fl = [(f, "▶ " + foc.title, (255, 255, 255, 255))]
            if foc.detail:
                fl.append((f_small, foc.detail, (200, 210, 230, 255)))
            for e in foc.explanation:
                fl.append((f_small, e, (255, 220, 140, 255)))
            fw = max(int(620 * k), int(max(d.textlength(t, font=fo) for fo, t, _ in fl)) + pad)
            d.rounded_rectangle([pad // 2, y - pad // 3, pad + fw, y + lh * len(fl) + 4],
                                radius=int(8 * k), fill=(5, 10, 25, 150))
            for font, text, col in fl:
                d.text((pad, y), text, font=font, fill=col)
                y += lh

        # --- ficha del elemento y del isótopo, arriba en el centro
        self._element_card(d, st, w, pad, f, f_small, lh, k)

        # --- barra de profundidad a la derecha
        self._depth_bar(d, st["depth_m"], w, h, k, f_small)

        # --- nombres de los ejes (al ver un subnivel con la tecla O)
        axis_rgb = {"x": (255, 120, 120, 230), "y": (120, 255, 120, 230), "z": (120, 170, 255, 230)}
        for (px, py), name in st.get("axis_labels", []):
            if 0 <= px < w and 0 <= py < h:
                d.text((px + 4, py - 10 * k), name, font=f_big, fill=axis_rgb[name])

        # --- mira central
        cx, cy, r = w // 2, h // 2, int(9 * k)
        for a, b in (((cx - r, cy), (cx - 3, cy)), ((cx + 3, cy), (cx + r, cy)),
                     ((cx, cy - r), (cx, cy - 3)), ((cx, cy + 3), (cx, cy + r))):
            d.line([a, b], fill=(255, 255, 255, 140))

        if self.show_help:
            help_lines = tr.lines("viewer.hud.help")
            for i, text in enumerate(help_lines):
                d.text((pad, h - pad - lh * (len(help_lines) - i)), text, font=f_small,
                       fill=(160, 175, 200, 220))
        if now < self.message_until:
            tw = d.textlength(self.message, font=f_big)
            d.text(((w - tw) / 2, h * 0.72), self.message, font=f_big, fill=(255, 255, 255, 230))
        return img

    def _element_card(self, d, st, w, pad, f, f_small, lh, k):
        tr, el, iso = self.tr, st["element"], st["isotope"]
        all_isotopes = st.get("isotopes") or []
        index = next((i for i, x in enumerate(all_isotopes, 1) if x.a == iso.a), 1)
        lines = [
            (f, tr.t("viewer.card.element", symbol=el.symbol, name=tr.element(el.number), z=el.number),
             (255, 255, 255, 255)),
            (f_small, tr.t("viewer.card.isotope", symbol=el.symbol, a=iso.a,
                           protons=tr.count(el.protons, "proton"),
                           neutrons=tr.count(iso.neutrons, "neutron"),
                           i=index, total=len(all_isotopes) or 1), (200, 215, 240, 255)),
        ]
        summary = scale.isotope_summary(iso, tr)
        if iso.abundance:
            summary = tr.t("viewer.card.natural", abundance=tr.num(iso.abundance, 2)) + " · " + summary
        lines.append((f_small, summary, (255, 220, 140, 255) if not iso.is_stable else (140, 230, 200, 255)))
        # arriba a la derecha, alineada a la derecha (a la izquierda queda el panel del nivel)
        width = max(d.textlength(t, font=fo) for fo, t, _ in lines)
        right = w - pad
        d.rounded_rectangle([right - width - pad, pad // 2, right + pad // 2, pad + lh * len(lines)],
                            radius=int(8 * k), fill=(5, 10, 25, 150))
        y = pad
        for font, text, col in lines:
            d.text((right - d.textlength(text, font=font), y), text, font=font, fill=col)
            y += lh

    def _depth_bar(self, d, depth_m, w, h, k, font):
        x = w - int(40 * k)
        top, bot = int(150 * k), h - int(80 * k)
        lt, lb = math.log10(BAR_TOP), math.log10(BAR_BOTTOM)

        def y_of(m):
            return top + (lt - math.log10(m)) / (lt - lb) * (bot - top)

        d.line([x, top, x, bot], fill=(120, 140, 170, 160), width=2)
        for m, key in DEPTH_MARKS:
            label = self.tr.t(f"viewer.depth_marks.{key}")
            y = y_of(m)
            d.line([x - 6, y, x + 6, y], fill=(150, 170, 200, 200), width=2)
            tw = d.textlength(label, font=font)
            d.text((x - 14 - tw, y - 8 * k), label, font=font, fill=(150, 170, 200, 220))
        y = y_of(min(max(depth_m, BAR_BOTTOM), BAR_TOP))
        d.polygon([(x + 8, y), (x + 20, y - 7), (x + 20, y + 7)], fill=(255, 220, 120, 255))

    # ------------------------------------------------------------ GPU
    def upload(self, img: Image.Image):
        if self.tex is None or self.size != img.size:
            if self.tex:
                self.tex.release()
            self.tex = self.ctx.texture(img.size, 4)
            self.size = img.size
        self.tex.write(img.tobytes())

    def draw(self):
        if not self.tex:
            return
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.tex.use(0)
        self.vao.render(moderngl.TRIANGLE_STRIP)
