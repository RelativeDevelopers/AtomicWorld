/* Modo plástico 3D de los visores (WebGL 2): partículas como bolas de plástico brillante.
 *
 *   protón (+, rojo)   neutrón (0, azul grisáceo)   electrón (e⁻, verde)
 *   quark up (u)       quark down (d)               gluón (g, naranja)
 *
 * Es la versión web de microscope/render/sprites.py y microscope/levels/plastic.py (DNAinvent)
 * y de viewer/render/sprites.py y viewer/levels/plastic.py (AtomicWorld): mismas imágenes,
 * mismos tamaños y mismas órbitas. Vive en el núcleo de AtomicWorld (atomicworld/web_assets/) y
 * las dos webs lo sirven desde ahí, en /static/v3d/: hay un solo archivo.
 *
 * Cada partícula es un cuadrado que mira a la cámara con su imagen (img/plastic/*.webp), pero
 * con la profundidad de una esfera de verdad: las bolas que se solapan se cortan bien. Se usan
 * cuadrados con instancias y no puntos porque muchas tarjetas limitan el tamaño de un punto, y al
 * acercarse a un protón la bola ocupa toda la pantalla.
 *
 * Es un modelo de juguete: los electrones giran como en el modelo de Bohr y ni ellos ni los
 * quarks tienen tamaño. Los textos del HUD lo explican.
 */
"use strict";

const V3DPlastic = (() => {
  const KINDS = ["proton", "neutron", "electron", "up", "down", "gluon"];
  const LAYER = Object.fromEntries(KINDS.map((k, i) => [k, i]));
  const BALL_FRACTION = 0.92;       // en las imágenes, la bola ocupa el 92 % del ancho
  const SIZE = 256;

  // Tamaños (los mismos que en el escritorio)
  const NUCLEON_BALL_FM = 0.75;     // radio de carga del protón: 0,84 fm (un poco menos para verlos separados)
  const ELECTRON_BALL_FRACTION = 0.03;   // bola del electrón / radio del subnivel más externo
  const ELECTRON_MIN_PX = 4.5;
  const NUCLEON_MIN_PX = 2.0;       // el núcleo visto desde el átomo: un puntito de colores
  const QUARK_BALL = 0.45;          // en décimas de fm (unidades del nivel del nucleón)
  const GLUON_BALL = 0.3;
  const QUARK_MIN_PX = 8.0;
  const QUARK_HALO = 1.6;           // diámetro del halo de la carga de color
  const FERMI_WOBBLE_FM = 0.12;     // temblor de los nucleones
  const NEAR_FADE = 2.0;            // la bola se vuelve transparente a menos de 2 radios
  const OUTER_PERIOD_S = 7.0, INNER_PERIOD_S = 1.4;

  const VS = `#version 300 es
  precision highp float;
  in vec2 in_corner; in vec3 in_center; in float in_radius; in float in_layer; in float in_alpha; in float in_min_px;
  uniform mat4 u_view; uniform mat4 u_proj; uniform float u_viewport_h, u_ball, u_near_fade;
  out vec2 v_uv; out float v_layer; out float v_alpha; out vec3 v_eye_center; out float v_radius;
  void main() {
    vec4 eye = u_view * vec4(in_center, 1.0);
    float dist = max(-eye.z, 1e-9);
    float px = in_radius * u_proj[1][1] * u_viewport_h * 0.5 / dist;
    float r = in_radius * max(1.0, in_min_px / max(px, 1e-6));   // tamaño mínimo en píxeles
    gl_Position = u_proj * vec4(eye.xyz + vec3(in_corner * (r / u_ball), 0.0), 1.0);
    float a = in_alpha;
    if (u_near_fade > 0.0) a *= clamp((dist / r - 1.2) / (u_near_fade - 1.2), 0.0, 1.0);
    v_uv = in_corner; v_layer = in_layer; v_alpha = a; v_eye_center = eye.xyz; v_radius = r;
  }`;
  const FS = `#version 300 es
  precision highp float;
  precision highp sampler2DArray;
  uniform sampler2DArray u_tex; uniform mat4 u_proj; uniform float u_ball, u_fade;
  in vec2 v_uv; in float v_layer; in float v_alpha; in vec3 v_eye_center; in float v_radius;
  out vec4 f_color;
  void main() {
    vec4 c = texture(u_tex, vec3(v_uv.x * 0.5 + 0.5, 0.5 - v_uv.y * 0.5, v_layer));
    float a = c.a * v_alpha * u_fade;
    if (a < 0.03) discard;
    vec2 q = v_uv / u_ball;
    float nz = sqrt(max(1.0 - dot(q, q), 0.0));
    vec4 clip = u_proj * vec4(v_eye_center + vec3(q, nz) * v_radius, 1.0);
    gl_FragDepth = clamp(clip.z / clip.w * 0.5 + 0.5, 0.0, 1.0);
    f_color = vec4(c.rgb, a);
  }`;

  function compile(gl) {
    const make = (type, src) => {
      const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const p = gl.createProgram();
    gl.attachShader(p, make(gl.VERTEX_SHADER, VS)); gl.attachShader(p, make(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    const loc = {};
    for (const name of ["u_view", "u_proj", "u_viewport_h", "u_ball", "u_near_fade", "u_tex", "u_fade"])
      loc[name] = gl.getUniformLocation(p, name);
    return { p, loc, attr: (name) => gl.getAttribLocation(p, name) };
  }

  /** Programa, cuadrado y textura (las 6 imágenes en capas). Las imágenes se cargan aparte: hasta
   *  que llegan no se dibuja ninguna bola (ready = false). Se crea la primera vez que hace falta. */
  class SpriteRenderer {
    constructor(gl, base = "/static/v3d/img/plastic/") {
      this.gl = gl; this.prog = compile(gl); this.ready = false;
      this.quad = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, this.quad);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      this.texture = gl.createTexture();
      this.loaded = Promise.all(KINDS.map((k) => new Promise((resolve, reject) => {
        const img = new Image(); img.onload = () => resolve(img); img.onerror = reject; img.src = `${base}${k}.webp`;
      }))).then((images) => {
        if (gl.isContextLost()) return;
        gl.bindTexture(gl.TEXTURE_2D_ARRAY, this.texture);
        gl.texImage3D(gl.TEXTURE_2D_ARRAY, 0, gl.RGBA8, SIZE, SIZE, images.length, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
        const canvas = document.createElement("canvas"); canvas.width = canvas.height = SIZE;
        const ctx = canvas.getContext("2d");
        images.forEach((img, i) => {
          ctx.clearRect(0, 0, SIZE, SIZE); ctx.drawImage(img, 0, 0, SIZE, SIZE);
          gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, SIZE, SIZE, 1, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
        });
        gl.generateMipmap(gl.TEXTURE_2D_ARRAY);
        gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
        gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        this.ready = true;
      }).catch((error) => console.warn("V3DPlastic: no se pudieron cargar las imágenes", error));
    }

    /** Dibuja un SpriteSet. cam: { view, proj (Float32Array en columnas), h }. */
    draw(set, cam, fade, nearFade = 0) {
      if (!this.ready || !set.count || fade <= 0.001) return;
      const gl = this.gl, { p, loc } = this.prog, v = cam.view;
      // de atrás hacia delante: así salen bien los bordes transparentes y el fundido
      const n = set.count, d = set.data, order = Array.from({ length: n }, (_, i) => i);
      const z = order.map((i) => v[2] * d[i * 6] + v[6] * d[i * 6 + 1] + v[10] * d[i * 6 + 2] + v[14]);
      order.sort((a, b) => z[a] - z[b]);
      const sorted = set.sorted;
      order.forEach((i, k) => sorted.set(d.subarray(i * 6, i * 6 + 6), k * 6));
      gl.bindBuffer(gl.ARRAY_BUFFER, set.vbo); gl.bufferSubData(gl.ARRAY_BUFFER, 0, sorted);

      gl.useProgram(p);
      gl.uniformMatrix4fv(loc.u_view, false, cam.view); gl.uniformMatrix4fv(loc.u_proj, false, cam.proj);
      gl.uniform1f(loc.u_viewport_h, cam.h); gl.uniform1f(loc.u_ball, BALL_FRACTION);
      gl.uniform1f(loc.u_near_fade, nearFade); gl.uniform1f(loc.u_fade, fade);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D_ARRAY, this.texture); gl.uniform1i(loc.u_tex, 0);

      // cada nivel tiene sus unidades: profundidad nueva (solo en su mitad, con pantalla partida)
      const vp = gl.getParameter(gl.VIEWPORT);
      gl.enable(gl.SCISSOR_TEST); gl.scissor(vp[0], vp[1], vp[2], vp[3]);
      gl.depthMask(true); gl.clearDepth(1); gl.clear(gl.DEPTH_BUFFER_BIT);
      gl.disable(gl.SCISSOR_TEST);
      gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LESS);
      // el alfa del lienzo se queda en 1 (si no, con premultipliedAlpha: false se vería la página detrás)
      gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      gl.bindVertexArray(set.vao);
      gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, n);
      gl.bindVertexArray(null);
      gl.disable(gl.DEPTH_TEST);
      gl.blendFunc(gl.ONE, gl.ONE);                          // vuelve la mezcla aditiva
    }

    release() {
      const gl = this.gl;
      gl.deleteBuffer(this.quad); gl.deleteTexture(this.texture); gl.deleteProgram(this.prog.p);
    }
  }

  /** Un grupo de bolas: posición (3), radio, capa (imagen), alfa y radio mínimo en px.
   *  kinds: nombres de KINDS. Las posiciones se cambian con setPositions (cada frame si se mueven). */
  class SpriteSet {
    constructor(sr, kinds, radius, minPx = 0, alpha = 1) {
      const gl = sr.gl, prog = sr.prog, n = kinds.length;
      this.gl = gl; this.count = n;
      this.data = new Float32Array(n * 6); this.sorted = new Float32Array(n * 6);
      kinds.forEach((k, i) => {
        const o = i * 6;
        this.data[o + 3] = Array.isArray(radius) ? radius[i] : radius;
        this.data[o + 4] = LAYER[k];
        this.data[o + 5] = Array.isArray(alpha) ? alpha[i] : alpha;
      });
      this.minPx = new Float32Array(n).fill(0).map((_, i) => (Array.isArray(minPx) ? minPx[i] : minPx));
      this.vao = gl.createVertexArray(); gl.bindVertexArray(this.vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, sr.quad);
      const corner = prog.attr("in_corner");
      gl.enableVertexAttribArray(corner); gl.vertexAttribPointer(corner, 2, gl.FLOAT, false, 8, 0);
      // mínimo en px: en su propio búfer (no cambia), así el que se reordena es más corto
      this.minVbo = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, this.minVbo);
      gl.bufferData(gl.ARRAY_BUFFER, this.minPx, gl.STATIC_DRAW);
      const minAttr = prog.attr("in_min_px");
      gl.enableVertexAttribArray(minAttr); gl.vertexAttribPointer(minAttr, 1, gl.FLOAT, false, 4, 0);
      gl.vertexAttribDivisor(minAttr, 1);
      this.vbo = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, this.vbo);
      gl.bufferData(gl.ARRAY_BUFFER, this.data.byteLength, gl.DYNAMIC_DRAW);
      [["in_center", 3, 0], ["in_radius", 1, 3], ["in_layer", 1, 4], ["in_alpha", 1, 5]].forEach(([name, size, off]) => {
        const a = prog.attr(name); gl.enableVertexAttribArray(a);
        gl.vertexAttribPointer(a, size, gl.FLOAT, false, 24, off * 4); gl.vertexAttribDivisor(a, 1);
      });
      gl.bindVertexArray(null);
      this.kinds = kinds;
    }
    setPositions(points) {
      points.forEach((p, i) => { this.data[i * 6] = p[0]; this.data[i * 6 + 1] = p[1]; this.data[i * 6 + 2] = p[2]; });
    }
    setAlpha(i, a) { this.data[i * 6 + 5] = a; }
    release() {
      const gl = this.gl;
      gl.deleteBuffer(this.vbo); gl.deleteBuffer(this.minVbo); gl.deleteVertexArray(this.vao);
    }
  }

  // ------------------------------------------------------------------ física de la ilustración

  /** Una órbita por electrón, del radio medio de su subnivel, en un plano al azar (modelo de Bohr).
   *  subshells: los de describe (n, l, electrons, mean_radius_pm). r: el azar del visor (r(), r.normal()). */
  function electronOrbits(subshells, r) {
    const outer = Math.max(...subshells.map((s) => s.mean_radius_pm)), orbits = [];
    for (const sh of subshells) {
      // 3.ª ley de Kepler (ω ∝ r^-1,5), entre los dos periodos de pantalla
      const period = Math.min(OUTER_PERIOD_S, Math.max(INNER_PERIOD_S, OUTER_PERIOD_S * (sh.mean_radius_pm / outer) ** 1.5));
      for (let e = 0; e < sh.electrons; e++) {
        const nrm = unit([r.normal(), r.normal(), r.normal()]);
        const u = unit(cross(nrm, Math.abs(nrm[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0]));
        orbits.push({
          radius: sh.mean_radius_pm * (0.92 + 0.16 * r()), u, v: cross(nrm, u),
          omega: 2 * Math.PI / period * (e % 2 === 0 ? 1 : -1),           // espín ↑ / ↓
          phase: 2 * Math.PI * e / Math.max(sh.electrons, 1) + 0.6 * r(), n: sh.n,
        });
      }
    }
    return orbits;
  }
  function orbitPositions(orbits, t, center = [0, 0, 0]) {
    return orbits.map((o) => {
      const a = o.omega * t + o.phase, c = Math.cos(a) * o.radius, s = Math.sin(a) * o.radius;
      return [0, 1, 2].map((k) => center[k] + c * o.u[k] + s * o.v[k]);
    });
  }
  const electronBallPm = (subshells) => ELECTRON_BALL_FRACTION * Math.max(...subshells.map((s) => s.mean_radius_pm));
  const nucleonKinds = (kinds) => [...kinds].map((k) => (k === "p" ? "proton" : "neutron"));

  /** Temblor de los nucleones alrededor de su sitio (movimiento de Fermi): t -> desplazamientos. */
  function wobble(count, r) {
    const f = Array.from({ length: count * 3 }, () => 2 + 2 * r());
    const ph = Array.from({ length: count * 3 }, () => 2 * Math.PI * r());
    return (t, centers) => centers.map((c, i) => [0, 1, 2].map((k) => c[k] + FERMI_WOBBLE_FM * Math.sin(f[i * 3 + k] * t + ph[i * 3 + k])));
  }

  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const unit = (a) => { const n = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / n, a[1] / n, a[2] / n]; };

  return {
    KINDS, SpriteRenderer, SpriteSet, electronOrbits, orbitPositions, electronBallPm, nucleonKinds, wobble,
    NUCLEON_BALL_FM, ELECTRON_MIN_PX, NUCLEON_MIN_PX, QUARK_BALL, GLUON_BALL, QUARK_MIN_PX, QUARK_HALO, NEAR_FADE,
  };
})();
