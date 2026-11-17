/* Piezas de interfaz de los visores 3D de Relative Developers (Átomo en 3D de AtomicWorld y
 * Microscopio 3D / Proteína 3D de DNAinvent). Vive en el núcleo de AtomicWorld
 * (atomicworld/web_assets/) y las dos webs lo sirven desde ahí, en /static/v3d/: hay un solo archivo.
 *
 *   V3DUI.key("M")                     una tecla dibujada (<kbd>)
 *   V3DUI.button({...})                botón con icono, texto y sus teclas
 *   V3DUI.help(stage, {...})           ventana de ayuda: H la abre y la cierra; Esc o ✕ la cierran
 *   V3DUI.explainer({...})             ficha «Saber más» con la explicación de lo que tienes delante
 *
 * No sabe nada de física ni de textos: cada visor le pasa las frases ya traducidas.
 */
"use strict";

const V3DUI = (() => {
  const esc = (v) => String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /** Una tecla: <kbd class="v3d-key">. size: "sm" para las de los botones. */
  const key = (label, size = "") => `<kbd class="v3d-key${size ? ` v3d-key-${size}` : ""}">${esc(label)}</kbd>`;

  /** Varias teclas. "+" y "/" se dibujan como separadores; "WASD" se dibuja en forma de cruz. */
  function keys(list, size = "") {
    return list.map((k) => {
      if (k === "+" || k === "/") return `<span class="v3d-key-sep">${k}</span>`;
      if (k === "WASD") return `<span class="v3d-wasd"><span></span>${key("W", size)}<span></span>${key("A", size)}${key("S", size)}${key("D", size)}</span>`;
      return key(k, size);
    }).join("");
  }

  /**
   * Botón de la barra.
   *   act: acción (data-act) · icon: carácter o img: ruta de una imagen · label: texto
   *   keys: teclas que hacen lo mismo (["⇧", "↵"]) · shortcut: aria-keyshortcuts ("Shift+Enter")
   *   primary: botón destacado · state: true si muestra un estado (se rellena luego con setState)
   */
  function button({ act, icon = "", img = "", label, keys: k = [], shortcut = "", primary = false, state = false, title = "" }) {
    const art = img ? `<img class="v3d-btn-img" src="${esc(img)}" alt="" width="28" height="28">`
      : icon ? `<span class="v3d-btn-icon" aria-hidden="true">${esc(icon)}</span>` : "";
    return `<button type="button" class="v3d-btn${primary ? " v3d-btn-primary" : ""}" data-act="${esc(act)}"${
      shortcut ? ` aria-keyshortcuts="${esc(shortcut)}"` : ""}${title ? ` title="${esc(title)}"` : ""}>${art}<span class="v3d-btn-label">${
      esc(label)}</span>${state ? `<span class="v3d-btn-state"></span>` : ""}${
      k.length ? `<span class="v3d-btn-keys" aria-hidden="true">${keys(k, "sm")}</span>` : ""}</button>`;
  }

  /** Grupo de botones separado de los demás por una línea. */
  const group = (...buttons) => `<span class="v3d-group">${buttons.join("")}</span>`;

  /**
   * Ventana de ayuda dentro del visor (así también se ve en pantalla completa).
   *   texts: { title, close, footer }
   *   groups: [{ title, rows: [{ keys: ["Q", "/", "E"], text }] }]
   *   onOpen / onClose: para soltar el ratón y devolver el foco al lienzo
   * Devuelve { open(), close(), toggle(), isOpen() }.
   */
  function help(stage, { texts, groups, onOpen, onClose }) {
    const id = `v3d-help-${Math.random().toString(36).slice(2, 8)}`;
    const wrap = document.createElement("div");
    wrap.className = "v3d-dialog-wrap";
    wrap.hidden = true;
    wrap.innerHTML = `
      <div class="v3d-dialog" role="dialog" aria-modal="true" aria-labelledby="${id}" tabindex="-1">
        <header><h2 id="${id}">${esc(texts.title)}</h2>
          <button type="button" class="v3d-dialog-close" aria-label="${esc(texts.close)}" title="${esc(texts.close)}">✕</button></header>
        <div class="v3d-dialog-groups">${groups.map((g) => `
          <section><h3>${esc(g.title)}</h3><dl>${g.rows.map((r) => `
            <div class="v3d-row"><dt>${keys(r.keys)}</dt><dd>${esc(r.text)}</dd></div>`).join("")}</dl></section>`).join("")}
        </div>
        <p class="v3d-dialog-foot">${texts.footer}</p>
      </div>`;
    stage.append(wrap);
    const dialog = wrap.querySelector(".v3d-dialog"), closeButton = wrap.querySelector(".v3d-dialog-close");
    let returnFocus = null;
    const api = {
      isOpen: () => !wrap.hidden,
      open() {
        if (!wrap.hidden) return;
        returnFocus = document.activeElement;
        wrap.hidden = false;
        onOpen?.();
        closeButton.focus({ preventScroll: true });
      },
      close() {
        if (wrap.hidden) return;
        wrap.hidden = true;
        onClose?.(returnFocus);
      },
      toggle() { (wrap.hidden ? api.open : api.close)(); },
    };
    closeButton.addEventListener("click", api.close);
    wrap.addEventListener("click", (e) => { if (e.target === wrap) api.close(); });   // clic fuera de la ventana
    dialog.addEventListener("keydown", (e) => {
      if (e.key === "Escape" || e.code === "KeyH") { api.close(); e.preventDefault(); e.stopPropagation(); }
      else if (e.key === "Tab") { e.preventDefault(); closeButton.focus(); }        // el foco no sale de la ventana
    });
    return api;
  }

  /**
   * Ficha «Saber más»: la explicación divulgativa de lo que tienes delante.
   * Está cerrada por defecto; mientras está cerrada solo se ve el botón «ⓘ Saber más» (y la tecla L).
   * Para que no cambie sin parar al volar, solo se actualiza cuando llevas ~0,8 s delante del
   * mismo objeto, y nunca en turbo.
   *   els: { more (botón), card, title, body, close } · texts: { empty }
   *   onToggle(open): para guardar si el usuario la tiene abierta
   * update(focus, time, fast) en cada refresco del HUD; focus = { title, expl: [frases] }.
   */
  function explainer({ els, texts, open: startOpen = false, settle = 0.8, onToggle }) {
    let open = startOpen, shown = null, candidate = null, since = 0;
    // la segunda línea del foco puede ser una distancia que cambia sin parar: no cuenta
    const keyOf = (f) => `${f.title}|${f.expl.join("|")}`;
    function paint() {
      els.card.hidden = !open;
      els.more.hidden = open || !candidate;
      els.more.setAttribute("aria-expanded", String(open));
      if (!open) return;
      if (!shown) {
        els.title.textContent = "";
        els.body.innerHTML = `<p class="v3d-expl-empty">${esc(texts.empty)}</p>`;
        return;
      }
      els.title.textContent = shown.title;
      els.body.innerHTML = shown.expl.map((x) => `<p>${esc(x)}</p>`).join("");
      els.card.classList.remove("v3d-swap"); void els.card.offsetWidth; els.card.classList.add("v3d-swap");   // fundido
    }
    const api = {
      isOpen: () => open,
      toggle(force) {
        open = force ?? !open;
        if (open && candidate) shown = candidate;          // al abrirla, la explicación de lo que tienes delante
        paint();
        onToggle?.(open);
      },
      update(focus, time, fast) {
        const next = focus?.expl?.length ? { ...focus, key: keyOf(focus) } : null;
        if ((next?.key ?? null) !== (candidate?.key ?? null)) { candidate = next; since = time; }
        els.more.hidden = open || !candidate;
        if (open && candidate && !fast && time - since >= settle && candidate.key !== shown?.key) {
          shown = candidate;
          paint();
        }
      },
    };
    els.more.addEventListener("click", () => api.toggle(true));
    els.close.addEventListener("click", () => api.toggle(false));
    paint();
    return api;
  }

  return { esc, key, keys, button, group, help, explainer };
})();
