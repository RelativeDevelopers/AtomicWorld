/* Controles de los visores 3D de Relative Developers en el navegador: Átomo en 3D (AtomicWorld),
 * Microscopio 3D, Proteína 3D y Cuerpo humano (DNAinvent). Vive en el núcleo de AtomicWorld
 * (atomicworld/web_assets/) y las dos webs lo sirven desde ahí, en /static/v3d/.
 *
 * El estándar (qué tecla hace qué) es controls.json; aquí va una copia exacta en STANDARD (un test
 * del núcleo comprueba que son iguales) y los visores de escritorio leen el mismo archivo.
 *
 *   const ctl = V3DControls.attach({ viewer: "atom3d", canvas, scope: container, on: { action, rotate, pan, zoom, pick } });
 *   ctl.axis("forward", "back")      // teclas mantenidas, en cada fotograma: -1, 0 o 1
 *   ctl.held("turbo")
 *   ctl.destroy()
 *
 * Convención de los gestos: lo que arrastras sigue al dedo (o al ratón), como en Google Earth.
 *   rotate(dx, dy)   un dedo o arrastrar con el botón izquierdo (px de pantalla; dy > 0 = hacia abajo)
 *   pan(dx, dy)      dos dedos, o arrastrar con el botón derecho o con Mayús
 *   zoom(f)          pellizcar o la rueda: f > 1 = acercarse
 *   pick(x, y)       tocar o hacer clic sin mover (px dentro del lienzo)
 *   action(name, e)  teclas y doble toque/doble clic ("go"); si el visor no la tiene, unavailable(name)
 * Las teclas de flechas, en cambio, mueven la cámara (→ = mirar a la derecha).
 */
"use strict";

const V3DControls = (() => {
  // BEGIN STANDARD (copia exacta de controls.json)
  const STANDARD = {
    "format": "relativedevelopers-v3d-controls",
    "version": 1,
    "about": "El estándar de controles de los visores 3D de Relative Developers: Átomo en 3D (AtomicWorld), Microscopio 3D, Proteína 3D y Cuerpo humano (DNAinvent), en la consola y en la web. Una tecla = una sola acción en los cuatro. Las teclas son KeyboardEvent.code; {\"text\": \"[\"} es un carácter (así funciona en cualquier teclado). Ver docs/CONTROLES.md.",
    "held": {
      "forward": ["KeyW"],
      "back": ["KeyS"],
      "left": ["KeyA"],
      "right": ["KeyD"],
      "up": ["Space"],
      "down": ["KeyC"],
      "roll_left": ["KeyQ"],
      "roll_right": ["KeyE"],
      "look_left": ["ArrowLeft"],
      "look_right": ["ArrowRight"],
      "look_up": ["ArrowUp"],
      "look_down": ["ArrowDown"],
      "turbo": ["ShiftLeft", "ShiftRight"]
    },
    "press": {
      "go": ["Enter", "NumpadEnter"],
      "go_back": ["Backspace"],
      "reset": ["KeyR"],
      "mode": ["KeyM"],
      "light": ["KeyB"],
      "more": ["KeyL"],
      "help": ["KeyH"],
      "fullscreen": ["KeyF", "F11"],
      "escape": ["Escape"],
      "subshell": ["KeyO"],
      "orbital": ["KeyI"],
      "next_element": ["KeyN"],
      "previous_element": ["KeyP"],
      "next_isotope": [{"text": "]"}],
      "previous_isotope": [{"text": "["}],
      "layout": ["KeyU"],
      "side": ["KeyV"],
      "isolate": ["KeyX"],
      "all_layers": ["KeyT"]
    },
    "shift": {
      "go": "go_full",
      "mode": "mode_back"
    },
    "pointer": {
      "drag": "rotate",
      "drag_right": "pan",
      "drag_shift": "pan",
      "wheel": "zoom",
      "double_click": "go",
      "click": "pick"
    },
    "touch": {
      "one_finger": "rotate",
      "two_fingers": "pan",
      "pinch": "zoom",
      "double_tap": "go",
      "tap": "pick"
    },
    "common": ["forward", "back", "left", "right", "up", "down", "roll_left", "roll_right",
               "look_left", "look_right", "look_up", "look_down", "turbo",
               "go", "go_back", "reset", "mode", "light", "more", "help", "fullscreen", "escape"],
    "viewers": {
      "atom3d": ["subshell", "orbital", "next_element", "previous_element", "next_isotope", "previous_isotope"],
      "microscope": ["subshell", "orbital", "layout", "side"],
      "protein3d": ["subshell", "orbital", "layout", "side"],
      "body": ["isolate", "all_layers"]
    },
    "buttons": {
      "about": "Cuadrícula de botones de la web, en filas de 3 y en este orden. null = hueco. La fila de layout/side solo sale al comparar dos proteínas. Proteína 3D es el Microscopio 3D con una proteína: mismas teclas.",
      "atom3d": [["go", "go_back", "go_full"], ["mode", "light", "reset"], ["subshell", "orbital", null], ["more", "help", "fullscreen"]],
      "microscope": [["go", "go_back", "go_full"], ["mode", "light", "reset"], ["subshell", "orbital", null], ["layout", "side", null], ["more", "help", "fullscreen"]],
      "protein3d": [["go", "go_back", "go_full"], ["mode", "light", "reset"], ["subshell", "orbital", null], ["layout", "side", null], ["more", "help", "fullscreen"]],
      "body": [["go", "go_back", "isolate"], ["mode", "light", "reset"], ["all_layers", null, null], ["more", "help", "fullscreen"]]
    }
  };
  // END STANDARD

  const TAP_PX = 8, TAP_MS = 450, DOUBLE_MS = 320, DOUBLE_PX = 30, WHEEL_STEP = 1.15;
  const LIGHT_KEY = "relativedevelopers.v3d.light";

  /** Las acciones de un visor: las comunes, las suyas y sus variantes con Mayús. */
  function actionsOf(viewer) {
    const own = STANDARD.viewers[viewer];
    if (!own) throw new Error(`unknown viewer: ${viewer}`);
    const names = new Set([...STANDARD.common, ...own]);
    for (const [base, alt] of Object.entries(STANDARD.shift)) if (names.has(base)) names.add(alt);
    return names;
  }

  const HELD = {}, PRESS = {}, TEXT = {};
  for (const [action, keys] of Object.entries(STANDARD.held)) keys.forEach((k) => { HELD[k] = action; });
  for (const [action, keys] of Object.entries(STANDARD.press))
    keys.forEach((k) => { if (typeof k === "string") PRESS[k] = action; else TEXT[k.text] = action; });

  /** El nombre corto de la primera tecla de una acción, para dibujarla: "↵", "⌫", "M"… */
  function keyLabel(action) {
    const base = Object.entries(STANDARD.shift).find(([, alt]) => alt === action)?.[0];
    const k = (STANDARD.press[base ?? action] ?? STANDARD.held[action] ?? [])[0];
    if (k === undefined) return [];
    const name = typeof k !== "string" ? k.text
      : ({ Enter: "↵", Backspace: "⌫", Escape: "Esc", Space: "␣", ArrowLeft: "←", ArrowRight: "→", ArrowUp: "↑",
           ArrowDown: "↓", ShiftLeft: "⇧", ShiftRight: "⇧" })[k] ?? k.replace(/^Key/, "");
    return base ? ["⇧", name] : [name];
  }

  const typing = (el) => el && (el.isContentEditable || /^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName));

  /**
   * Conecta el teclado, el ratón y el tacto de un visor.
   *   viewer: "atom3d" | "microscope" | "protein3d" | "body"
   *   canvas: el lienzo · scope: dónde vale el teclado (el visor y sus botones; el teclado
   *           funciona mientras el foco esté dentro). Puede ser una función, si el visor cambia
   *           de página (Cuerpo humano). Por defecto, el padre del lienzo.
   *   isBlocked(): true mientras haya una ventana abierta (la ayuda), que gestiona sus teclas
   *   on: { action(name, event), unavailable(name), rotate(dx, dy), pan(dx, dy), zoom(f, x, y),
   *         pick(x, y), held(code, down) }
   */
  function attach({ viewer, canvas, scope = () => canvas.parentElement, isBlocked = () => false, on = {} }) {
    const available = actionsOf(viewer);
    const keys = new Set(), listeners = [];
    const listen = (target, type, fn, opts) => { target.addEventListener(type, fn, opts); listeners.push([target, type, fn, opts]); };
    const scopeEl = () => (typeof scope === "function" ? scope() : scope);
    const active = () => !!scopeEl()?.contains(document.activeElement) && !typing(document.activeElement);
    canvas.style.touchAction = "none";                      // los gestos son nuestros, no del navegador
    if (!canvas.hasAttribute("tabindex")) canvas.tabIndex = 0;

    function fire(name, event) {
      if (!name) return false;
      if (!available.has(name)) { on.unavailable?.(name); return true; }
      on.action?.(name, event);
      return true;
    }

    listen(window, "keydown", (e) => {
      if (isBlocked() || !active()) return;
      const altgr = e.ctrlKey && e.altKey;                 // AltGr en Windows: [ y ] en teclados españoles
      if ((e.ctrlKey || e.metaKey || e.altKey) && !(altgr && TEXT[e.key])) return;
      const held = HELD[e.code];
      if (held) {
        if (!available.has(held)) { if (!e.repeat) on.unavailable?.(held); return; }
        keys.add(e.code); on.held?.(held, true);
        if (held !== "turbo") e.preventDefault();          // que Espacio y las flechas no muevan la página
        return;
      }
      if (e.repeat) { if (PRESS[e.code] || TEXT[e.key]) e.preventDefault(); return; }
      let name = PRESS[e.code] ?? TEXT[e.key];
      if (!name) return;
      if (e.shiftKey && STANDARD.shift[name] && PRESS[e.code]) name = STANDARD.shift[name];
      if (name === "escape" && document.fullscreenElement) return;   // Esc ya sale de la pantalla completa
      if (fire(name, e)) e.preventDefault();
    });
    listen(window, "keyup", (e) => { if (keys.delete(e.code)) on.held?.(HELD[e.code], false); });
    listen(window, "blur", () => keys.clear());

    // --- ratón y tacto (Pointer Events: lo mismo para los dos)
    const pointers = new Map();
    let gesture = null, lastTap = null;
    const pos = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    const pair = () => {
      const [a, b] = [...pointers.values()];
      return { mid: [(a.x + b.x) / 2, (a.y + b.y) / 2], dist: Math.hypot(a.x - b.x, a.y - b.y) };
    };
    listen(canvas, "contextmenu", (e) => e.preventDefault());
    listen(canvas, "pointerdown", (e) => {
      canvas.focus({ preventScroll: true });
      try { canvas.setPointerCapture(e.pointerId); } catch { /* puntero sintético o ya suelto */ }
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, t0: performance.now(),
        pan: e.button === 2 || e.button === 1 || e.shiftKey, moved: 0 });
      gesture = pointers.size >= 2 ? { kind: "two", ...pair() } : { kind: "one" };
      if (pointers.size >= 2) pointers.forEach((p) => { p.moved = TAP_PX + 1; });   // dos dedos nunca son un toque
    });
    listen(canvas, "pointermove", (e) => {
      const p = pointers.get(e.pointerId);
      if (!p) return;
      const dx = e.clientX - p.x, dy = e.clientY - p.y;
      p.x = e.clientX; p.y = e.clientY; p.moved += Math.abs(dx) + Math.abs(dy);
      if (pointers.size >= 2 && gesture?.kind === "two") {
        const now = pair();
        on.pan?.(now.mid[0] - gesture.mid[0], now.mid[1] - gesture.mid[1]);
        if (gesture.dist > 0 && now.dist > 0) on.zoom?.(now.dist / gesture.dist, ...pos({ clientX: now.mid[0], clientY: now.mid[1] }));
        gesture = { kind: "two", ...now };
      } else if (pointers.size === 1 && p.moved > TAP_PX) {
        (p.pan ? on.pan : on.rotate)?.(dx, dy);
      }
    });
    const up = (e) => {
      const p = pointers.get(e.pointerId);
      pointers.delete(e.pointerId);
      if (pointers.size === 1) gesture = { kind: "one" };   // al levantar un dedo de dos: sigue con uno, sin saltos
      if (!p || pointers.size > 0 || e.type === "pointercancel") return;
      const now = performance.now();
      if (p.moved > TAP_PX || now - p.t0 > TAP_MS || (e.pointerType === "mouse" && e.button !== 0)) return;
      const [x, y] = pos(e);
      if (lastTap && now - lastTap.t < DOUBLE_MS && Math.hypot(x - lastTap.x, y - lastTap.y) < DOUBLE_PX) {
        lastTap = null;
        fire("go", e);
      } else {
        lastTap = { t: now, x, y };
        on.pick?.(x, y);
      }
    };
    listen(canvas, "pointerup", up);
    listen(canvas, "pointercancel", up);
    listen(canvas, "wheel", (e) => {
      e.preventDefault();
      // los trackpads mandan el pellizco como rueda con Ctrl y pasos pequeños
      const f = e.ctrlKey ? Math.exp(-e.deltaY * 0.01) : WHEEL_STEP ** -Math.sign(e.deltaY);
      if (f !== 1) on.zoom?.(f, ...pos(e));
    }, { passive: false });

    return {
      held: (action) => (STANDARD.held[action] ?? []).some((k) => keys.has(k)),
      axis(plus, minus) { return (this.held(plus) ? 1 : 0) - (this.held(minus) ? 1 : 0); },
      anyHeld: () => [...keys].some((k) => HELD[k] !== "turbo"),
      clear: () => keys.clear(),
      available: (name) => available.has(name),
      destroy() { listeners.forEach(([t, type, fn, opts]) => t.removeEventListener(type, fn, opts)); listeners.length = 0; keys.clear(); },
    };
  }

  // --- botones (la cuadrícula de 3 columnas, igual en los cuatro visores) -----------------
  const FLIGHT = { go: "▼", go_back: "▲", go_full: "⇊", mode: "⇆", light: "☀", reset: "⟲", subshell: "◎",
    orbital: "∞", layout: "⧉", side: "↔", more: "ⓘ", help: "?", fullscreen: "⛶" };
  const BODY = { ...FLIGHT, go: "◎", go_back: "⤴", mode: "🎨", isolate: "◐", all_layers: "☰" };
  const TOGGLES = { flight: new Set(["light", "more"]), body: new Set(["light", "isolate", "mode"]) };
  const BODY_LABELS = new Set(["go", "go_back", "mode", "more"]);   // Centrar, Subir a la parte, Colores, Ficha

  /**
   * HTML de la cuadrícula de botones de un visor.
   *   t(key): textos de web.v3d.* · comparing: si se compara (fila U/V) · img: { act: ruta } para
   *   un botón con imagen (el microscopio en «Hasta el final»)
   * Los textos son web.v3d.buttons.<acción> (en Cuerpo humano, algunos son web.v3d.buttons.body_<acción>).
   */
  function buttons(viewer, { t, comparing = false, img = {} }) {
    const rows = STANDARD.buttons[viewer].filter((row) => comparing || !row.includes("layout"));
    const icons = viewer === "body" ? BODY : FLIGHT;
    const label = (act) => t(viewer === "body" && BODY_LABELS.has(act) ? `web.v3d.buttons.body_${act}` : `web.v3d.buttons.${act}`);
    const cell = (act) => act === null ? `<span class="v3d-grid-fill" aria-hidden="true"></span>`
      : V3DUI.button({ act, icon: img[act] ? "" : icons[act], img: img[act] ?? "", label: label(act), keys: keyLabel(act),
          shortcut: keyLabel(act).map((k) => ({ "⇧": "Shift", "↵": "Enter", "⌫": "Backspace" })[k] ?? k).join("+") })
          .replace("<button ", TOGGLES[viewer === "body" ? "body" : "flight"].has(act) ? `<button aria-pressed="false" ` : "<button ");
    return `<div class="v3d-grid" role="group">${rows.flat().map(cell).join("")}</div>`;
  }

  /** Marca un botón de la cuadrícula como pulsado o no (fondo claro, aislar, Saber más). */
  function setPressed(root, act, on) {
    root.querySelectorAll(`.v3d-grid [data-act="${act}"]`).forEach((b) => b.setAttribute("aria-pressed", String(!!on)));
  }

  // --- ayuda (H) con los mismos apartados en los cuatro --------------------------------------
  /**
   * Los apartados de la ventana de ayuda, para V3DUI.help. t(key) da los textos de web.v3d.*.
   * En pantallas táctiles, los gestos salen primero.
   */
  function helpGroups(viewer, { t, comparing = false }) {
    const k = (name) => t(`web.v3d.keys.${name}`), row = (keys, text) => ({ keys, text: t(`web.v3d.rows.${text}`) });
    const body = viewer === "body";
    const groups = [
      { title: t("web.v3d.groups.move"), rows: [
        row(["W", "/", "S"], body ? "zoom_body" : "forward_back"), row(["A", "/", "D"], "sideways"),
        row([k("space"), "/", "C"], "updown"), row(["Q", "/", "E"], body ? "roll_body" : "roll"),
        row(["←", "↑", "↓", "→"], "look"), row([k("shift")], "turbo")] },
      { title: t("web.v3d.groups.pointer"), rows: [
        row([k("drag")], "rotate"), row([k("right_drag"), "/", k("shift"), "+", k("drag")], "pan"),
        row([k("wheel")], "zoom"), row([k("double_click")], body ? "go_double_body" : "go_double")] },
      { title: t("web.v3d.groups.touch"), rows: [
        row([k("one_finger")], "one_finger"), row([k("two_fingers")], "two_fingers"),
        row([k("pinch")], "pinch"), row([k("double_tap")], body ? "go_double_body" : "go_double"),
        ...(body ? [row([k("tap")], "tap_pick")] : [])] },
      body
        ? { title: t("web.v3d.groups.selection"), rows: [row([k("click")], "pick"), row([k("enter")], "frame"),
            row([k("backspace")], "parent"), row(["X"], "isolate"), row(["T"], "all_layers")] }
        : { title: t("web.v3d.groups.levels"), rows: [row([k("enter")], "go_down"), row([k("shift"), "+", k("enter")], "go_full"),
            row([k("backspace")], "go_up")] },
      ...(viewer === "atom3d" ? [{ title: t("web.v3d.groups.atom"), rows: [row(["O"], "subshell"), row(["I"], "orbital"),
        row(["N", "/", "P"], "element"), row(["[", "/", "]"], "isotope")] }] : []),
      ...(viewer === "microscope" || viewer === "protein3d" ? [{ title: t("web.v3d.groups.atom"), rows: [row(["O"], "subshell"), row(["I"], "orbital")] }] : []),
      ...(comparing ? [{ title: t("web.v3d.groups.compare"), rows: [row(["U"], "layout"), row(["V"], "side")] }] : []),
      { title: t("web.v3d.groups.screen"), rows: [row(["M"], body ? "colors" : "mode"), row(["B"], "light"), row(["R"], "reset"),
        row(["L"], body ? "more_body" : "more"), row(["H"], "help"), row(["F"], "fullscreen"), row([k("esc")], body ? "esc_body" : "esc")] },
    ];
    if (window.matchMedia?.("(pointer: coarse)").matches) groups.unshift(...groups.splice(2, 1));
    return groups;
  }

  // --- fondo claro (B): se recuerda en este navegador, para los cuatro visores ---------------
  const light = {
    get() { try { return localStorage.getItem(LIGHT_KEY) === "1"; } catch { return false; } },
    set(on) { try { localStorage.setItem(LIGHT_KEY, on ? "1" : "0"); } catch { /* sin almacenamiento: solo esta vez */ } },
  };

  /* Fondo claro de los visores de nave: el lienzo se invierte con CSS (invert + hue-rotate 180°:
   * el negro pasa a blanco y los colores conservan su tono). Lo que no debe invertirse (las bolas
   * del modo plástico) se dibuja ya invertido con LIGHT_GLSL, y al invertir la imagen vuelve a su
   * color exacto: esta transformación es su propia inversa. */
  const LIGHT_GLSL = `
    vec3 v3dLight(vec3 c) {   // = invert(1) hue-rotate(180deg) de CSS
      c = 1.0 - c;
      return clamp(mat3(-0.574, 0.426, 0.426,  1.430, 0.430, 1.430,  0.144, 0.144, -0.856) * c, 0.0, 1.0);
    }`;

  return { STANDARD, actionsOf, keyLabel, attach, buttons, setPressed, helpGroups, light, LIGHT_GLSL };
})();
