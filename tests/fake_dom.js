'use strict';

/* A small DOM, enough to run app/renderer/app.js under plain node.
 *
 * The renderer is browser code with no module system and no framework: it
 * builds its UI with createElement, reads it back with querySelector, and
 * keeps its session state in closures over `state`. The behaviour worth
 * regression-testing - which tab is on screen, whether a preview is stale,
 * what a fresh layer's pane shows - only exists once that code has run
 * against a document with the real ids in it. So this parses the real
 * index.html into a tree of plain objects and implements the handful of DOM
 * calls the renderer makes: class lists, datasets, attributes, a selector
 * engine for the compound selectors it uses, bubbling events, focus, and the
 * media-element calls (`load` fires `loadeddata` on the next tick, the way a
 * clip that decodes instantly would).
 *
 * Deliberately not a general DOM. Anything the renderer does not use is left
 * out, and an unsupported selector throws rather than silently matching
 * nothing, so a test cannot pass by accident. */

const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
  'meta', 'param', 'source', 'track', 'wbr']);
const BOOL_ATTRS = new Set(['checked', 'selected', 'disabled', 'hidden']);
const REFLECTED = ['src', 'type', 'title', 'alt', 'placeholder', 'min', 'max', 'step',
  'href', 'name', 'role', 'loading', 'decoding'];

function decode(s) {
  return String(s).replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ');
}

function camel(name) {
  return name.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
}

function kebab(name) {
  return String(name).replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
}

/* ── events ──────────────────────────────────────────────────────────── */
class FakeEvent {
  constructor(type, init = {}) {
    this.type = type;
    this.bubbles = !!init.bubbles;
    this.cancelable = !!init.cancelable;
    this.defaultPrevented = false;
    this.target = null;
    this.currentTarget = null;
    this._stopped = false;
    this._immediate = false;
    for (const k of Object.keys(init)) if (!(k in this)) this[k] = init[k];
  }
  preventDefault() { this.defaultPrevented = true; }
  stopPropagation() { this._stopped = true; }
  stopImmediatePropagation() { this._stopped = true; this._immediate = true; }
}
class FakeCustomEvent extends FakeEvent {}
class FakeKeyboardEvent extends FakeEvent {
  constructor(type, init = {}) {
    super(type, init);
    this.key = init.key || '';
    this.code = init.code || '';
    this.metaKey = !!init.metaKey; this.ctrlKey = !!init.ctrlKey;
    this.altKey = !!init.altKey; this.shiftKey = !!init.shiftKey;
    this.repeat = !!init.repeat;
  }
}
class FakeMouseEvent extends FakeEvent {
  constructor(type, init = {}) {
    super(type, init);
    this.clientX = init.clientX || 0; this.clientY = init.clientY || 0;
    this.button = init.button || 0;
    this.altKey = !!init.altKey; this.metaKey = !!init.metaKey;
  }
}

class FakeEventTarget {
  constructor() { this._listeners = new Map(); }
  addEventListener(type, fn, opts) {
    if (!fn) return;
    let arr = this._listeners.get(type);
    if (!arr) { arr = []; this._listeners.set(type, arr); }
    arr.push({ fn, once: !!(opts && opts.once) });
  }
  removeEventListener(type, fn) {
    const arr = this._listeners.get(type);
    if (!arr) return;
    const i = arr.findIndex((l) => l.fn === fn);
    if (i >= 0) arr.splice(i, 1);
  }
  _invoke(ev) {
    ev.currentTarget = this;
    const handler = this['on' + ev.type];
    if (typeof handler === 'function') handler.call(this, ev);
    if (ev._immediate) return;
    const arr = this._listeners.get(ev.type);
    if (!arr) return;
    for (const l of [...arr]) {
      if (l.once) this.removeEventListener(ev.type, l.fn);
      if (typeof l.fn === 'function') l.fn.call(this, ev);
      else if (l.fn && typeof l.fn.handleEvent === 'function') l.fn.handleEvent(ev);
      if (ev._immediate) break;
    }
  }
  _propagationPath() { return [this]; }
  dispatchEvent(ev) {
    ev.target = this;
    const path = ev.bubbles ? this._propagationPath() : [this];
    for (const t of path) {
      t._invoke(ev);
      if (ev._stopped) break;
    }
    return !ev.defaultPrevented;
  }
}

/* ── selectors ───────────────────────────────────────────────────────── */
const COMPOUND_RE = /([a-zA-Z][\w-]*|\*)|#([\w-]+)|\.([\w-]+)|\[([\w-]+)(?:=(?:"([^"]*)"|'([^']*)'|([^\]]+)))?\]|:not\(([^)]*)\)/y;

function parseCompound(s) {
  const c = { tag: null, id: null, classes: [], attrs: [], nots: [] };
  COMPOUND_RE.lastIndex = 0;
  let m;
  let at = 0;
  while (at < s.length) {
    COMPOUND_RE.lastIndex = at;
    m = COMPOUND_RE.exec(s);
    if (!m) throw new Error(`fake_dom: unsupported selector "${s}"`);
    at = COMPOUND_RE.lastIndex;
    if (m[1] !== undefined) c.tag = m[1] === '*' ? null : m[1].toLowerCase();
    else if (m[2] !== undefined) c.id = m[2];
    else if (m[3] !== undefined) c.classes.push(m[3]);
    else if (m[4] !== undefined) c.attrs.push({ name: m[4], value: m[5] ?? m[6] ?? m[7] });
    else if (m[8] !== undefined) c.nots.push(parseCompound(m[8].trim()));
  }
  return c;
}

/* "a > b c" -> compounds with the combinator that joins each to the one before. */
function parseComplex(s) {
  const tokens = s.trim().split(/\s+/);
  const out = [];
  let combinator = ' ';
  for (const t of tokens) {
    if (t === '>') { combinator = '>'; continue; }
    out.push({ compound: parseCompound(t), combinator });
    combinator = ' ';
  }
  return out;
}

const selectorCache = new Map();
function parseSelector(sel) {
  let parsed = selectorCache.get(sel);
  if (!parsed) {
    parsed = sel.split(',').map((s) => parseComplex(s));
    selectorCache.set(sel, parsed);
  }
  return parsed;
}

function matchesCompound(el, c) {
  if (c.tag && el.localName !== c.tag) return false;
  if (c.id && el.getAttribute('id') !== c.id) return false;
  for (const k of c.classes) if (!el.classList.contains(k)) return false;
  for (const a of c.attrs) {
    const v = el.getAttribute(a.name);
    if (v === null) return false;
    if (a.value !== undefined && v !== a.value) return false;
  }
  for (const n of c.nots) if (matchesCompound(el, n)) return false;
  return true;
}

function matchesComplex(el, parts) {
  let i = parts.length - 1;
  if (!matchesCompound(el, parts[i].compound)) return false;
  let node = el;
  while (--i >= 0) {
    const { compound, combinator } = parts[i + 1];
    void compound;
    const want = parts[i].compound;
    if (combinator === '>') {
      node = node.parentElement;
      if (!node || !matchesCompound(node, want)) return false;
    } else {
      node = node.parentElement;
      while (node && !matchesCompound(node, want)) node = node.parentElement;
      if (!node) return false;
    }
  }
  return true;
}

/* ── nodes ───────────────────────────────────────────────────────────── */
class FakeNode extends FakeEventTarget {
  constructor(doc) {
    super();
    this.ownerDocument = doc;
    this.parentNode = null;
    this.childNodes = [];
  }
  get parentElement() { return this.parentNode instanceof FakeElement ? this.parentNode : null; }
  get isConnected() {
    let n = this;
    while (n) { if (n === this.ownerDocument) return true; n = n.parentNode; }
    return false;
  }
  _propagationPath() {
    const path = [];
    let n = this;
    while (n) { path.push(n); n = n.parentNode; }
    const doc = this.ownerDocument;
    if (path[path.length - 1] !== doc) path.push(doc);
    if (doc.defaultView) path.push(doc.defaultView);
    return path;
  }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
}

class FakeText extends FakeNode {
  constructor(doc, text) {
    super(doc);
    this.nodeType = 3;
    this.nodeName = '#text';
    this.data = String(text);
  }
  get textContent() { return this.data; }
  set textContent(v) { this.data = String(v); }
  get nodeValue() { return this.data; }
}

class ClassList {
  constructor() { this._set = new Set(); }
  add(...cs) { for (const c of cs) if (c) this._set.add(c); }
  remove(...cs) { for (const c of cs) this._set.delete(c); }
  toggle(c, force) {
    const on = force === undefined ? !this._set.has(c) : !!force;
    if (on) this._set.add(c); else this._set.delete(c);
    return on;
  }
  contains(c) { return this._set.has(c); }
  get length() { return this._set.size; }
  toString() { return [...this._set].join(' '); }
  [Symbol.iterator]() { return this._set[Symbol.iterator](); }
}

function makeStyle() {
  return {
    setProperty(k, v) { this[k] = String(v); },
    getPropertyValue(k) { return this[k] === undefined ? '' : this[k]; },
    removeProperty(k) { delete this[k]; },
  };
}

class FakeElement extends FakeNode {
  constructor(doc, tag) {
    super(doc);
    this.nodeType = 1;
    this.localName = String(tag).toLowerCase();
    this.tagName = this.localName.toUpperCase();
    this.nodeName = this.tagName;
    this._attrs = new Map();
    this.classList = new ClassList();
    // dataset writes reflect into data-* attributes, the way the real one does,
    // so a row tagged through `row.dataset.param` is findable by selector.
    this._data = {};
    this.dataset = new Proxy(this._data, {
      set: (obj, k, v) => { obj[k] = String(v); this._attrs.set(`data-${kebab(k)}`, String(v)); return true; },
      deleteProperty: (obj, k) => { delete obj[k]; this._attrs.delete(`data-${kebab(k)}`); return true; },
    });
    this.style = makeStyle();
    this.checked = false;
    this.disabled = false;
    this.selected = false;
    this.hidden = false;
    this.draggable = false;
    this.spellcheck = true;
    this.scrollTop = 0;
    this._value = null;
    // media
    this.readyState = 0;
    this.currentTime = 0;
    this.duration = NaN;
    this.paused = true;
    this.muted = false;
    this.videoWidth = 0;
    this.videoHeight = 0;
    this.naturalWidth = 0;
    this._loadSeq = 0;
    this.mediaDuration = 3;   // what a loaded clip reports; tests can set it
  }

  // attributes
  getAttribute(k) {
    if (k === 'class') return this.classList.length ? this.classList.toString() : (this._attrs.has('class') ? '' : null);
    return this._attrs.has(k) ? this._attrs.get(k) : null;
  }
  setAttribute(k, v) {
    const s = String(v);
    this._attrs.set(k, s);
    if (k === 'class') this.className = s;
    else if (k.startsWith('data-')) this._data[camel(k.slice(5))] = s;
    else if (BOOL_ATTRS.has(k)) this[k] = true;
  }
  removeAttribute(k) {
    this._attrs.delete(k);
    if (k === 'class') this.className = '';
    else if (k.startsWith('data-')) delete this._data[camel(k.slice(5))];
    else if (BOOL_ATTRS.has(k)) this[k] = false;
    else if (k === 'src') this.readyState = 0;
  }
  hasAttribute(k) { return this._attrs.has(k); }
  get id() { return this._attrs.get('id') || ''; }
  set id(v) { this.setAttribute('id', v); }
  get className() { return this.classList.toString(); }
  set className(v) {
    this.classList._set = new Set(String(v).split(/\s+/).filter(Boolean));
  }
  get htmlFor() { return this._attrs.get('for') || ''; }
  set htmlFor(v) { this.setAttribute('for', v); }
  get tabIndex() { return this._attrs.has('tabindex') ? Number(this._attrs.get('tabindex')) : -1; }
  set tabIndex(v) { this.setAttribute('tabindex', v); }

  get value() {
    if (this._value !== null) return this._value;
    if (this.localName === 'select') {
      const opts = this.querySelectorAll('option');
      const pick = opts.find((o) => o.selected) || opts[0];
      return pick ? pick.value : '';
    }
    if (this.localName === 'option') return this._attrs.has('value') ? this._attrs.get('value') : this.textContent;
    return this._attrs.has('value') ? this._attrs.get('value') : '';
  }
  set value(v) { this._value = String(v); }

  // tree
  get children() { return this.childNodes.filter((n) => n.nodeType === 1); }
  get childElementCount() { return this.children.length; }
  get firstChild() { return this.childNodes[0] || null; }
  get lastChild() { return this.childNodes[this.childNodes.length - 1] || null; }
  get firstElementChild() { return this.children[0] || null; }
  get lastElementChild() { const c = this.children; return c[c.length - 1] || null; }
  get previousElementSibling() {
    if (!this.parentNode) return null;
    const sib = this.parentNode.children;
    return sib[sib.indexOf(this) - 1] || null;
  }
  get nextElementSibling() {
    if (!this.parentNode) return null;
    const sib = this.parentNode.children;
    return sib[sib.indexOf(this) + 1] || null;
  }
  _adopt(n) {
    if (typeof n === 'string' || typeof n === 'number') return new FakeText(this.ownerDocument, n);
    if (n.parentNode) n.parentNode.removeChild(n);
    return n;
  }
  appendChild(n) {
    // A fragment empties itself into its new parent, the way the real one does.
    if (n && n.localName === '#document-fragment') {
      for (const c of [...n.childNodes]) this.appendChild(c);
      return n;
    }
    n = this._adopt(n);
    this.childNodes.push(n);
    n.parentNode = this;
    return n;
  }
  append(...items) { for (const it of items) this.appendChild(it); }
  prepend(...items) {
    for (const it of items.reverse()) {
      const n = this._adopt(it);
      this.childNodes.unshift(n);
      n.parentNode = this;
    }
  }
  insertBefore(n, ref) {
    if (!ref) return this.appendChild(n);
    n = this._adopt(n);
    const i = this.childNodes.indexOf(ref);
    if (i < 0) throw new Error('fake_dom: insertBefore reference is not a child');
    this.childNodes.splice(i, 0, n);
    n.parentNode = this;
    return n;
  }
  removeChild(n) {
    const i = this.childNodes.indexOf(n);
    if (i < 0) throw new Error('fake_dom: removeChild of a non-child');
    this.childNodes.splice(i, 1);
    n.parentNode = null;
    return n;
  }
  replaceChildren(...items) {
    for (const c of [...this.childNodes]) this.removeChild(c);
    for (const it of items) this.appendChild(it);
  }
  contains(n) {
    let x = n;
    while (x) { if (x === this) return true; x = x.parentNode; }
    return false;
  }

  get textContent() {
    return this.childNodes.map((n) => n.textContent).join('');
  }
  set textContent(v) {
    this.replaceChildren();
    if (v !== '' && v !== null && v !== undefined) this.appendChild(new FakeText(this.ownerDocument, v));
  }
  get innerText() { return this.textContent; }
  set innerText(v) { this.textContent = v; }
  get innerHTML() { return this.childNodes.map(serialize).join(''); }
  set innerHTML(html) {
    this.replaceChildren();
    if (html) parseHTML(this.ownerDocument, String(html), this);
  }

  // querying
  matches(sel) { return parseSelector(sel).some((parts) => matchesComplex(this, parts)); }
  closest(sel) {
    let n = this;
    while (n && n.nodeType === 1) { if (n.matches(sel)) return n; n = n.parentElement; }
    return null;
  }
  _descendants(out = []) {
    for (const c of this.childNodes) {
      if (c.nodeType !== 1) continue;
      out.push(c);
      c._descendants(out);
    }
    return out;
  }
  querySelectorAll(sel) {
    const parsed = parseSelector(sel);
    return this._descendants().filter((el) => parsed.some((parts) => matchesComplex(el, parts)));
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }

  // geometry and focus: nothing is laid out, so everything is at the origin
  getBoundingClientRect() { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0 }; }
  getClientRects() { return []; }
  scrollIntoView() {}
  setPointerCapture() {}
  releasePointerCapture() {}
  select() {}
  focus() {
    const doc = this.ownerDocument;
    if (doc.activeElement === this) return;
    const prev = doc.activeElement;
    doc.activeElement = this;
    if (prev && prev !== doc.body && prev.dispatchEvent) prev.dispatchEvent(new FakeEvent('blur'));
    this.dispatchEvent(new FakeEvent('focus'));
    this.dispatchEvent(new FakeEvent('focusin', { bubbles: true }));
  }
  blur() {
    const doc = this.ownerDocument;
    if (doc.activeElement !== this) return;
    doc.activeElement = doc.body;
    this.dispatchEvent(new FakeEvent('blur'));
    this.dispatchEvent(new FakeEvent('focusout', { bubbles: true }));
  }
  click() {
    const checkbox = this.localName === 'input' && this.getAttribute('type') === 'checkbox';
    if (checkbox && !this.disabled) this.checked = !this.checked;
    const ok = this.dispatchEvent(new FakeMouseEvent('click', { bubbles: true, cancelable: true }));
    if (checkbox) {
      if (!ok) this.checked = !this.checked;
      else {
        this.dispatchEvent(new FakeEvent('input', { bubbles: true }));
        this.dispatchEvent(new FakeEvent('change', { bubbles: true }));
      }
    }
  }

  // media
  load() {
    const seq = ++this._loadSeq;
    const src = this.getAttribute('src');
    this.readyState = 0;
    if (!src) { this.dispatchEvent(new FakeEvent('emptied')); return; }
    setTimeout(() => {
      if (seq !== this._loadSeq) return;   // a newer load() superseded this one
      this.readyState = 4;
      this.duration = this.mediaDuration;
      this.videoWidth = 320; this.videoHeight = 180;
      this.naturalWidth = 320;
      this.dispatchEvent(new FakeEvent('loadedmetadata'));
      this.dispatchEvent(new FakeEvent('loadeddata'));
      if (this.localName === 'img') this.dispatchEvent(new FakeEvent('load'));
    }, 0);
  }
  play() { this.paused = false; return Promise.resolve(); }
  pause() { this.paused = true; }
}

for (const name of REFLECTED) {
  Object.defineProperty(FakeElement.prototype, name, {
    get() { return this._attrs.has(name) ? this._attrs.get(name) : ''; },
    set(v) {
      this.setAttribute(name, v);
      // An <img> starts decoding as soon as it has a source; a <video> waits
      // for load(), the way setVideo() calls it.
      if (name === 'src' && this.localName === 'img') this.load();
    },
    configurable: true,
  });
}

function serialize(n) {
  if (n.nodeType === 3) return n.data;
  const attrs = [...n._attrs].map(([k, v]) => ` ${k}="${v}"`).join('');
  if (VOID.has(n.localName)) return `<${n.localName}${attrs}/>`;
  return `<${n.localName}${attrs}>${n.childNodes.map(serialize).join('')}</${n.localName}>`;
}

/* ── parsing ─────────────────────────────────────────────────────────── */
const TOKEN_RE = /<!--[\s\S]*?-->|<!DOCTYPE[^>]*>|<\/([a-zA-Z][\w-]*)\s*>|<([a-zA-Z][\w-]*)((?:\s+[\w:-]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'>]+))?)*)\s*(\/?)>|([^<]+)/g;
const ATTR_RE = /([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g;

function parseHTML(doc, html, parent) {
  const stack = [parent];
  TOKEN_RE.lastIndex = 0;
  let m;
  while ((m = TOKEN_RE.exec(html))) {
    if (m[0].startsWith('<!')) continue;
    if (m[1]) {
      const name = m[1].toLowerCase();
      for (let i = stack.length - 1; i > 0; i--) {
        if (stack[i].localName === name) { stack.length = i; break; }
      }
      continue;
    }
    if (m[2]) {
      const el = doc.createElement(m[2]);
      ATTR_RE.lastIndex = 0;
      let a;
      while ((a = ATTR_RE.exec(m[3] || ''))) el.setAttribute(a[1], decode(a[2] ?? a[3] ?? a[4] ?? ''));
      stack[stack.length - 1].appendChild(el);
      if (!m[4] && !VOID.has(el.localName)) stack.push(el);
      continue;
    }
    if (m[5] !== undefined && m[5].trim()) {
      stack[stack.length - 1].appendChild(doc.createTextNode(decode(m[5])));
    }
  }
}

/* ── document and window ─────────────────────────────────────────────── */
class FakeDocument extends FakeEventTarget {
  constructor(html) {
    super();
    this.nodeType = 9;
    this.visibilityState = 'visible';
    this.title = '';
    this.defaultView = null;
    this.parentNode = null;
    this.documentElement = new FakeElement(this, 'html');
    this.documentElement.parentNode = this;
    parseHTML(this, html, this.documentElement);
    this.head = this.documentElement.querySelector('head');
    this.body = this.documentElement.querySelector('body');
    if (!this.body) { this.body = this.createElement('body'); this.documentElement.appendChild(this.body); }
    this.activeElement = this.body;
  }
  createElement(tag) { return new FakeElement(this, tag); }
  createTextNode(t) { return new FakeText(this, t); }
  createDocumentFragment() { return new FakeElement(this, '#document-fragment'); }
  createRange() { return { selectNodeContents() {} }; }
  getElementById(id) {
    return this.documentElement._descendants().find((el) => el.getAttribute('id') === id) || null;
  }
  querySelector(sel) { return this.documentElement.querySelector(sel); }
  querySelectorAll(sel) { return this.documentElement.querySelectorAll(sel); }
  _propagationPath() { return this.defaultView ? [this, this.defaultView] : [this]; }
}

/* The sandbox that app.js runs in. It is its own `window`, the way a browser
   global object is, and carries the timers and event constructors the
   renderer reaches for. `aesth` is the preload bridge; pass the stubs a test
   needs and the rest answer with quiet defaults. */
function makeWindow(html, { aesth = {}, storage = new Map() } = {}) {
  const doc = new FakeDocument(html);
  const win = new FakeEventTarget();
  doc.defaultView = win;
  Object.assign(win, {
    window: win,
    document: doc,
    innerWidth: 1400,
    innerHeight: 900,
    localStorage: {
      getItem: (k) => (storage.has(k) ? storage.get(k) : null),
      setItem: (k, v) => storage.set(k, String(v)),
      removeItem: (k) => storage.delete(k),
    },
    navigator: { clipboard: { writeText: async () => {} } },
    getSelection: () => ({ removeAllRanges() {}, addRange() {} }),
    requestAnimationFrame: (fn) => setTimeout(fn, 0),
    cancelAnimationFrame: (id) => clearTimeout(id),
    // Unref'd, so a test process exits when its work is done rather than
    // waiting out the renderer's hourly update poll or a pending debounce.
    setTimeout: (fn, ms, ...a) => { const t = setTimeout(fn, ms, ...a); if (t.unref) t.unref(); return t; },
    setInterval: (fn, ms, ...a) => { const t = setInterval(fn, ms, ...a); if (t.unref) t.unref(); return t; },
    clearTimeout, clearInterval, queueMicrotask,
    alert: () => {},
    confirm: () => true,
    Event: FakeEvent,
    CustomEvent: FakeCustomEvent,
    KeyboardEvent: FakeKeyboardEvent,
    MouseEvent: FakeMouseEvent,
    console,
    aesth: {
      version: '0.0.0',
      packaged: false,
      checkEnv: async () => ({ ok: true, problems: [] }),
      thumbs: async () => ({ thumbs: {} }),
      schema: async () => { throw new Error('no schema stub'); },
      probe: async (file) => ({ path: file, duration: 15, width: 640, height: 360, fps: 30,
        has_video: true, has_audio: true, sr: 48000, channels: 2 }),
      preview: async () => { throw new Error('no preview stub'); },
      still: async () => { throw new Error('no still stub'); },
      snippet: async (req) => ({ output: `/cache/snippet-${req.start}-${req.duration}-${req.scale}.mp4` }),
      events: async () => ({ events: [] }),
      filmstrip: async () => ({ frames: [], duration: 15 }),
      cacheInfo: async () => ({ dir: '/cache', bytes: 0, count: 0, newest: null }),
      cacheClear: async () => ({ removed: 0, bytes: 0 }),
      cacheReveal: async () => ({}),
      onProgress: () => () => {},
      reveal: async () => ({ ok: true }),
      notify: async () => ({ ok: true }),
      pathForFile: (f) => f.path,
      updateInfo: async () => ({ version: '0.0.0', packaged: false, stale: false, last: null, staged: null }),
      updateCheck: async () => ({ ok: true, available: false }),
      updateReleases: async () => ({ ok: true, releases: [] }),
      onUpdateProgress: () => () => {},
      openExternal: async () => true,
      ...aesth,
    },
  });
  return win;
}

module.exports = { makeWindow, FakeDocument, FakeElement, FakeEvent, FakeCustomEvent,
  FakeKeyboardEvent, FakeMouseEvent };
