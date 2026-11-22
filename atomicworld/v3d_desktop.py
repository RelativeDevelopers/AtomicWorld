"""
Piezas compartidas de los visores 3D de escritorio (pyglet + moderngl): Átomo en 3D de
AtomicWorld (viewer/) y Microscopio 3D / Proteína 3D de DNAinvent (microscope/).

    FondoClaro: el «fondo claro» (tecla B) de los visores de nave.

Las partículas brillan con mezcla aditiva sobre negro, que no funciona sobre blanco. Con el fondo
claro, la escena se dibuja igual en una imagen aparte y al final se pasa a la pantalla invertida y
con el tono girado 180°: el negro pasa a blanco y cada color conserva su tono. Es la misma
transformación que la web (CSS `invert(1) hue-rotate(180deg)`, ver web_assets/v3d-controls.js).
Las bolas del modo plástico se dibujan ya invertidas (LIGHT_GLSL en su shader): como la
transformación es su propia inversa, vuelven a su color exacto.

moderngl se importa al usarlo: el núcleo no depende de él.
"""

# CSS hue-rotate(180deg) (filter effects, W3C) aplicado después de invert(1); en columnas (GLSL)
LIGHT_GLSL = """
vec3 v3dLight(vec3 c) {
    c = 1.0 - c;
    return clamp(mat3(-0.574, 0.426, 0.426,  1.430, 0.430, 1.430,  0.144, 0.144, -0.856) * c, 0.0, 1.0);
}
"""

_QUAD_VS = """
#version 330
in vec2 in_pos;
out vec2 v_uv;
void main() { v_uv = in_pos * 0.5 + 0.5; gl_Position = vec4(in_pos, 0.0, 1.0); }
"""

_QUAD_FS = """
#version 330
uniform sampler2D u_scene;
in vec2 v_uv;
out vec4 f_color;
""" + LIGHT_GLSL + """
void main() { f_color = vec4(v3dLight(texture(u_scene, v_uv).rgb), 1.0); }
"""


class LightBackground:
    """Dibujar la escena en una imagen aparte y pasarla invertida a la pantalla.

        light = LightBackground(ctx)
        with light.scene(width, height):     # framebuffer en píxeles reales
            engine.render(...)
        hud.draw()                           # el HUD se dibuja encima, sin invertir
    """

    def __init__(self, ctx, samples: int = 4):
        import moderngl
        self.ctx, self._mgl = ctx, moderngl
        self.samples = min(samples, getattr(ctx, "max_samples", 0) or 0)
        self.size = None
        self.prog = ctx.program(vertex_shader=_QUAD_VS, fragment_shader=_QUAD_FS)
        import array
        quad = ctx.buffer(array.array("f", [-1, -1, 1, -1, -1, 1, 1, 1]).tobytes())
        self.vao = ctx.vertex_array(self.prog, [(quad, "2f", "in_pos")])

    def _ensure(self, size):
        if size == self.size:
            return
        self.release()
        ctx = self.ctx
        self.texture = ctx.texture(size, 4)
        self.resolved = ctx.framebuffer(color_attachments=[self.texture])
        if self.samples:
            self.fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer(size, 4, samples=self.samples)],
                                       depth_attachment=ctx.depth_renderbuffer(size, samples=self.samples))
        else:
            self.fbo = ctx.framebuffer(color_attachments=[self.texture], depth_attachment=ctx.depth_renderbuffer(size))
        self.size = size

    def release(self):
        for name in ("fbo", "resolved", "texture"):
            obj = getattr(self, name, None)
            if obj is not None:
                obj.release()
                setattr(self, name, None)
        self.size = None

    def scene(self, width: int, height: int):
        return _Scene(self, (max(1, int(width)), max(1, int(height))))


class _Scene:
    def __init__(self, light, size):
        self.light, self.size = light, size

    def __enter__(self):
        light = self.light
        light._ensure(self.size)
        self.screen = light.ctx.fbo
        light.fbo.use()
        return light

    def __exit__(self, *exc):
        light, ctx, mgl = self.light, self.light.ctx, self.light._mgl
        if light.samples:
            ctx.copy_framebuffer(light.resolved, light.fbo)
        self.screen.use()
        ctx.disable(mgl.DEPTH_TEST | mgl.BLEND)
        light.texture.use(0)
        light.prog["u_scene"].value = 0
        light.vao.render(mgl.TRIANGLE_STRIP)
        return False
