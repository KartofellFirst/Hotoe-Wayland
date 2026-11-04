Error.prototype.toJSON = function () {
    return { name: this.name, message: this.message, stack: this.stack };
};

function push(data) { // pushes the string into local IPC
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify(data));
}
function SIRs({manual = null, density = 300} = {}) { // SIRs({ manual: [...], density: 300}), we dont implement a way to change TOL because claude says 0.4 is optimal for this task in any case
    SIRCollector.MAX_ROWS = density || 300; 
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: { SIRs: manual || SIRCollector.collect()}}));
}
function CLOSE() { // CLOSE
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {CLOSE: true}}));
}
function read(filePath) { // read(path).then(file => log(file.content))
    return fx._callWithPromise("readFile", { filePath: filePath });
}
function remove(filePath) { // remove(path) + optional .catch/.then
    return fx._callWithPromise("removeFile", { filePath: filePath });
}
function write(filePath, content, isBase64 = false) { // write(path, content, isBase64?) + optional .catch/.then
    return fx._callWithPromise("writeFile", { filePath: filePath, content: content, isBase64: isBase64 });
}
function scan(dirPath) { // scan()
    return fx._callWithPromise("scanDirectory", { dirPath: dirPath });
}
function openExternal(URI) { // openExternal()
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {BROWSE: URI}}))
}
function exec(cmd, {timeout = 30000, daemon=false} = {}) { // exec() + optional .then/.catch
    return fx._callWithPromise("execute", { cmd: cmd, timeout: timeout, daemon: daemon });
}
function hotkey(accelerator, eventName) { // hotkey() + optional .then/.catch
    return fx._callWithPromise("registerHotkey", { accelerator: accelerator, eventName: eventName });
}
function kill(id) { // kill(pid/id) + optional .then/.catch
    return fx._callWithPromise("killDaemon", { id: id });
}
function getDaemons() { // getDaemons().then
    return fx._callWithPromise("getDaemons");
}
function store(data, key) { // store(data, key) 
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {STORE: {data, key}}})); // not sure if that shortening works in JS
}
function toss(key) { // toss(key)
    return fx._callWithPromise("deleteFromCache", { key });
}
function rob() { // rob().then(keys => )
    return fx._callWithPromise("getKeyValues")
}
function grab(key) { // grab(key).then(data => )
    return fx._callWithPromise("getValueFromCache", {key}) // im such a niche js dev.. knowing these shorthands. mom will be proud
}


fx = {
    // system-reserved fields
    _promises: {},
    _callCounter: 0,
    _callWithPromise: function(action, payload = {}) {
        return new Promise((resolve, reject) => {
            const callId = "call_" + (++this._callCounter) + "_" + Date.now();
            this._promises[callId] = { resolve, reject };
            
            const message = {
                fxAPICall: {
                    action: action,
                    callId: callId,
                    payload: payload
                }
            };
            window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify(message));
        });
    },
    _resolvePromise: function(callId, error, result) {
        if (!this._promises[callId]) return;
        
        const { resolve, reject } = this._promises[callId];
        delete this._promises[callId];
        
        if (error) {
            reject(new Error(error));
        } else {
            resolve(result);
        }
    }
};


// rasterizer built into JS so we dont have to rewrite it every time we change the backend. Maybe one day I'd want to rewrite this in Rust to save 3Mbs lol
class SIRCollector {
    static collect() { return this.detailed().flatMap(d => d.rects) }

    static detailed() {
        const vw = innerWidth, vh = innerHeight, out = [];
        document.querySelectorAll(this.SELECTOR).forEach((el, i) => {
            if (!this.isActive(el)) return;
            const shape = this.shapeOf(el, i); if (!shape) return;
            out.push({ el, shape, rects: this.rasterize(shape, vw, vh) });
        }); return out
    }

    static isActive(el) {
        const a = el.getAttribute('active');
        if (a !== null && /^(false|0|off|no)$/i.test(a.trim())) return false;
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden' || cs.pointerEvents === 'none') return false;
        return el.getClientRects().length > 0;
    }

    static num(v) { return parseFloat(v) || 0 }

    static px(tok, ref) {
        tok = String(tok).trim();
        const m = /^([-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)(px|%)?$/i.exec(tok);
        if (!m) throw new Error('unsupported value "' + tok + '"');
        const v = parseFloat(m[1]);
        return m[2] === '%' ? v * ref / 100 : v
    }
    
    static px0(tok, ref) { try { return this.px(tok, ref); } catch (e) { return 0; } }

    static expand4(a) {
        return a.length === 1 ? [a[0], a[0], a[0], a[0]]
             : a.length === 2 ? [a[0], a[1], a[0], a[1]]
             : a.length === 3 ? [a[0], a[1], a[2], a[1]] : a.slice(0, 4)
    }

    static angleDeg(s) {
        const m = /^([-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)(deg|rad|turn|grad)?$/i.exec(s.trim());
        if (!m) throw new Error('rotate ' + s); const v = parseFloat(m[1]);
        return ({ rad: v * 180 / Math.PI, turn: v * 360, grad: v * 0.9 })[(m[2] || '').toLowerCase()] ?? v
    }

    static linearOf(el) {
        let m = new DOMMatrix(), flat = true;
        for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
            const cs = getComputedStyle(n);
            let t = new DOMMatrix();
            if (cs.rotate && cs.rotate !== 'none') {
                const tk = cs.rotate.trim().split(/\s+/);
                if (tk.length === 1) t = t.multiply(new DOMMatrix().rotate(this.angleDeg(tk[0]))); else flat = false;
            }
            if (cs.scale && cs.scale !== 'none') {
                const tk = cs.scale.trim().split(/\s+/).map(parseFloat);
                t = t.multiply(new DOMMatrix().scale(tk[0], tk[1] ?? tk[0]));
            }
            if (cs.transform && cs.transform !== 'none') {
                const T = new DOMMatrix(cs.transform);
                if (!T.is2D) flat = false;
                t = t.multiply(T);
            }
            m = t.multiply(m);
        }
        return { m, flat };
    }

    static frameOf(el) {
        const bb = el.getBoundingClientRect();
        const W = el.offsetWidth, H = el.offsetHeight;
        const { m, flat } = this.linearOf(el);
        const identity = m.a === 1 && m.b === 0 && m.c === 0 && m.d === 1;
        if (!flat || !W || !H) return { W: bb.width, H: bb.height, a: 1, b: 0, c: 0, d: 1, e: bb.left, f: bb.top, fallback: true };
        if (identity) return { W: bb.width, H: bb.height, a: 1, b: 0, c: 0, d: 1, e: bb.left, f: bb.top };
        const p = [[0, 0], [W, 0], [W, H], [0, H]].map(([x, y]) => [m.a * x + m.c * y, m.b * x + m.d * y]);
        return { W, H, a: m.a, b: m.b, c: m.c, d: m.d, e: bb.left - Math.min(...p.map(v => v[0])), f: bb.top - Math.min(...p.map(v => v[1])) };
    }
    
    static scaleOf(fr) { return Math.max(Math.hypot(fr.a, fr.b), Math.hypot(fr.c, fr.d)) }
    static mapPts(fr, pts) { return pts.map(([x, y]) => [fr.a * x + fr.c * y + fr.e, fr.b * x + fr.d * y + fr.f]) }
    static r1(pts) { return pts.map(([x, y]) => [Math.round(x * 10) / 10, Math.round(y * 10) / 10]); }

    static radiiOf(cs, W, H) {
        const r = ['TopLeft', 'TopRight', 'BottomRight', 'BottomLeft'].map(n => {
            const t = (cs['border' + n + 'Radius'] || '0').trim().split(/\s+/);
            const rx = this.px0(t[0], W);
            const ry = t.length > 1 ? this.px0(t[1], H) : (t[0].endsWith('%') ? this.px0(t[0], H) : rx);
            return [rx, ry];
        });
        const lim = (len, sum) => sum > 0 ? len / sum : 1;
        const f = Math.min(1, lim(W, r[0][0] + r[1][0]), lim(W, r[3][0] + r[2][0]), lim(H, r[0][1] + r[3][1]), lim(H, r[1][1] + r[2][1]))
        return r.map(([x, y]) => [x * f, y * f]);
    }

    static rrPoly(x0, y0, x1, y1, r, S) {
        const w = x1 - x0, h = y1 - y0;
        if (w <= 0 || h <= 0) return [];
        r = r.map(([rx, ry]) => (rx > 0 && ry > 0) ? [rx, ry] : [0, 0]);
        const lim = (len, sum) => sum > 0 ? len / sum : 1;
        const f = Math.min(1, lim(w, r[0][0] + r[1][0]), lim(w, r[3][0] + r[2][0]), lim(h, r[0][1] + r[3][1]), lim(h, r[1][1] + r[2][1]));
        r = r.map(([x, y]) => [x * f, y * f]);
        const pts = [], TOL = this.TOL;
        const arc = (cx, cy, rx, ry, a0) => {
            if (rx <= 0) { pts.push([cx, cy]); return; }
            const R = Math.max(rx, ry) * S;
            const step = R > TOL ? 2 * Math.acos(1 - TOL / R) : Math.PI / 2;
            const n = Math.min(48, Math.max(1, Math.ceil((Math.PI / 2) / step)));
            for (let i = 0; i <= n; i++) {
                const a = a0 + (Math.PI / 2) * i / n;
                pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
            }
        };
        arc(x0 + r[0][0], y0 + r[0][1], r[0][0], r[0][1], Math.PI);
        arc(x1 - r[1][0], y0 + r[1][1], r[1][0], r[1][1], 1.5 * Math.PI);
        arc(x1 - r[2][0], y1 - r[2][1], r[2][0], r[2][1], 0);
        arc(x0 + r[3][0], y1 - r[3][1], r[3][0], r[3][1], 0.5 * Math.PI);
        return pts
    }

    static ellipsePoly(cx, cy, rx, ry, S) {
        const R = Math.max(rx, ry) * S, TOL = this.TOL; const pts = [];
        const step = R > TOL ? 2 * Math.acos(1 - TOL / R) : Math.PI / 2;
        const n = Math.min(256, Math.max(8, Math.ceil(2 * Math.PI / step)));
        for (let i = 0; i < n; i++) { const a = 2 * Math.PI * i / n; pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]); }
        return pts
    }

    static clipRaw(cs) { return (cs.clipPath || cs.getPropertyValue('clip-path') || cs.webkitClipPath || cs.getPropertyValue('-webkit-clip-path') || 'none').trim(); }

    static refBox(cs, W, H, kw) {
        const n = v => this.num(v);
        const bl = n(cs.borderLeftWidth), br = n(cs.borderRightWidth), bt = n(cs.borderTopWidth), bb = n(cs.borderBottomWidth);
        if (kw === 'padding-box') return { x: bl, y: bt, w: W - bl - br, h: H - bt - bb };
        if (kw === 'content-box') {
            const pl = n(cs.paddingLeft), pr = n(cs.paddingRight), pt = n(cs.paddingTop), pb = n(cs.paddingBottom);
            return { x: bl + pl, y: bt + pt, w: W - bl - br - pl - pr, h: H - bt - bb - pt - pb };
        }
        return { x: 0, y: 0, w: W, h: H };
    }

    static parsePos(str, w, h) {
        const KW = { left: 0, right: 100, top: 0, bottom: 100, center: 50 };
        const t = str.trim().split(/\s+/).filter(Boolean);
        if (!t.length) return [w / 2, h / 2];
        if (t.length > 2) throw new Error('3/4-value position');
        const isV = k => k === 'top' || k === 'bottom', isH = k => k === 'left' || k === 'right';
        let xt, yt;
        if (t.length === 1) { if (isV(t[0])) { xt = 'center'; yt = t[0]; } else { xt = t[0]; yt = 'center'; } }
        else { xt = t[0]; yt = t[1]; if (isV(xt) || isH(yt)) [xt, yt] = [yt, xt]; }
        const c = (tok, ref) => (tok in KW) ? KW[tok] * ref / 100 : this.px(tok, ref);
        return [c(xt, w), c(yt, h)];
    }

    static clipPoly(cs, fr, S) {
        let s = this.clipRaw(cs);
        if (s === 'none') return null;
        let box = 'border-box';
        s = s.replace(/(^|\s)(border-box|padding-box|content-box|margin-box|fill-box|stroke-box|view-box)(?=\s|$)/i,
                      (m, p, k) => { box = k.toLowerCase(); return ' '; }).trim();
        const m = /^(polygon|inset|circle|ellipse)\(([\s\S]*)\)$/i.exec(s);
        if (!m) throw new Error('clip-path not supported: ' + s);
        const fn = m[1].toLowerCase(), args = m[2];
        if (args.includes('(')) throw new Error('calc()/nested function in clip-path: ' + s);
        const R = this.refBox(cs, fr.W, fr.H, box), px = (t, r) => this.px(t, r);

        if (fn === 'polygon') {
            const parts = args.split(',').map(x => x.trim());
            let eo = false;
            if (/^(evenodd|nonzero)$/i.test(parts[0])) { eo = parts[0].toLowerCase() === 'evenodd'; parts.shift(); }
            return { eo, pts: parts.map(p => { const [a, b] = p.split(/\s+/); return [R.x + px(a, R.w), R.y + px(b, R.h)]; }) };
        }
        if (fn === 'inset') {
            const [offs, rnd] = args.split(/\s+round\s+/i);
            const o = this.expand4(offs.trim().split(/\s+/));
            const t = px(o[0], R.h), r = px(o[1], R.w), b = px(o[2], R.h), l = px(o[3], R.w);
            let rad = [[0, 0], [0, 0], [0, 0], [0, 0]];
            if (rnd) {
                const [hs, vs] = rnd.split('/');
                const hx = this.expand4(hs.trim().split(/\s+/));
                const vy = vs ? this.expand4(vs.trim().split(/\s+/)) : hx;
                rad = hx.map((hv, i) => [px(hv, R.w), px(vy[i], R.h)]);
            }
            return { eo: false, pts: this.rrPoly(R.x + l, R.y + t, R.x + R.w - r, R.y + R.h - b, rad, S) };
        }
        const parts = (' ' + args + ' ').split(/\sat\s/i);
        const rs = parts[0].trim(), ps = (parts[1] || '').trim();
        const [cx, cy] = this.parsePos(ps, R.w, R.h);
        if (fn === 'circle') {
            const sides = [cx, R.w - cx, cy, R.h - cy];
            const r = (rs === '' || rs === 'closest-side') ? Math.min(...sides)
                    : rs === 'farthest-side' ? Math.max(...sides)
                    : px(rs, Math.hypot(R.w, R.h) / Math.SQRT2);
            return { eo: false, pts: this.ellipsePoly(R.x + cx, R.y + cy, r, r, S) };
        }
        const tk = rs.split(/\s+/).filter(Boolean);
        const rad1 = (tok, a, b, ref) => (!tok || tok === 'closest-side') ? Math.min(a, b) : tok === 'farthest-side' ? Math.max(a, b) : px(tok, ref);
        return { eo: false, pts: this.ellipsePoly(R.x + cx, R.y + cy, rad1(tk[0], cx, R.w - cx, R.w), rad1(tk[1], cy, R.h - cy, R.h), S) };
    }

    static shapeOf(el, i) {
        const html = document.documentElement;
        const fr = this.frameOf(el);
        if (!(fr.W > 0 && fr.H > 0)) return null;
        const cs = getComputedStyle(el), S = this.scaleOf(fr), notes = [];
        if (fr.fallback) notes.push('3D/unknown transform: AABB fallback');
        const shape = {
            id: el.id || ('#' + i),
            poly: this.r1(this.mapPts(fr, fr.fallback ? this.rrPoly(0, 0, fr.W, fr.H, [[0, 0], [0, 0], [0, 0], [0, 0]], S)
                                                     : this.rrPoly(0, 0, fr.W, fr.H, this.radiiOf(cs, fr.W, fr.H), S))),
            clips: [], clipRaw: this.clipRaw(cs),
        };
        try {
            const c = this.clipPoly(cs, fr, S);
            if (c) shape.clips.push({ p: this.r1(this.mapPts(fr, c.pts)), eo: c.eo ? 1 : 0, by: 'own clip-path' });
        } catch (e) { notes.push('own clip-path: ' + e.message); }

        for (let n = el.parentElement; n && n !== html; n = n.parentElement) {
            const ncs = getComputedStyle(n), nfr = this.frameOf(n), nS = this.scaleOf(nfr);
            const name = n.id || n.className || n.tagName.toLowerCase();
            const viewportOverflow = n === document.body && getComputedStyle(html).overflow === 'visible';
            if (!viewportOverflow && (ncs.overflowX !== 'visible' || ncs.overflowY !== 'visible')) {
                const k = v => this.num(v);
                const bl = k(ncs.borderLeftWidth), br = k(ncs.borderRightWidth), bt = k(ncs.borderTopWidth), bb = k(ncs.borderBottomWidth);
                const o = this.radiiOf(ncs, nfr.W, nfr.H);
                const inner = [[o[0][0] - bl, o[0][1] - bt], [o[1][0] - br, o[1][1] - bt], [o[2][0] - br, o[2][1] - bb], [o[3][0] - bl, o[3][1] - bb]]
                                .map(([x, y]) => (x > 0 && y > 0) ? [x, y] : [0, 0]);
                const poly = this.mapPts(nfr, this.rrPoly(bl, bt, nfr.W - br, nfr.H - bb, inner, nS));
                if (!shape.poly.every(pt => this.inPoly(pt, poly, false))) shape.clips.push({ p: this.r1(poly), eo: 0, by: 'overflow: ' + name });
            }
            try {
                const c = this.clipPoly(ncs, nfr, nS);
                if (c) shape.clips.push({ p: this.r1(this.mapPts(nfr, c.pts)), eo: c.eo ? 1 : 0, by: 'clip-path: ' + name });
            } catch (e) { notes.push('ancestor ' + name + ' clip-path: ' + e.message); }
        }
        if (notes.length) shape.notes = notes;
        return shape
    }

    static inPoly(pt, poly, eo) {
        const [x, y] = pt; let wn = 0, cr = false;
        for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
            const [xi, yi] = poly[i], [xj, yj] = poly[j];
            if ((yi > y) !== (yj > y)) {
                const xc = (xj - xi) * (y - yi) / (yj - yi) + xi;
                if (x < xc) { cr = !cr; wn += (yj > yi) ? 1 : -1; }
            }
        }
        return eo ? cr : wn !== 0;
    }

    static spansAt(poly, eo, y) {
        const xs = [];
        for (let i = 0, n = poly.length; i < n; i++) {
            const [x1, y1] = poly[i], [x2, y2] = poly[(i + 1) % n];
            if ((y1 > y) !== (y2 > y)) xs.push([x1 + (y - y1) * (x2 - x1) / (y2 - y1), y2 > y1 ? 1 : -1]);
        }
        xs.sort((a, b) => a[0] - b[0]);
        const spans = [];
        if (eo) { for (let i = 0; i + 1 < xs.length; i += 2) spans.push([xs[i][0], xs[i + 1][0]]); }
        else {
            let w = 0, start = 0;
            for (const [x, dir] of xs) {
                const prev = w; w += dir;
                if (prev === 0 && w !== 0) start = x; else if (prev !== 0 && w === 0) spans.push([start, x]);
            }
        }
        return spans
    }

    static intersectSpans(A, B) {
        const out = []; let i = 0, j = 0;
        while (i < A.length && j < B.length) {
            const lo = Math.max(A[i][0], B[j][0]), hi = Math.min(A[i][1], B[j][1]);
            if (hi > lo) out.push([lo, hi]);
            if (A[i][1] < B[j][1]) i++; else j++;
        }
        return out
    }

    static rasterize(shape, vw, vh) {
        const polys = [{ p: shape.poly, eo: false }, ...shape.clips];
        if (!shape.poly.length) return [];

        if (!shape.clips.length && shape.poly.length === 4) {
            const xs = shape.poly.map(v => v[0]), ys = shape.poly.map(v => v[1]);
            const ax = Math.max(...xs) - Math.min(...xs), ay = Math.max(...ys) - Math.min(...ys);
            const distinct = a => new Set(a.map(v => Math.round(v * 5))).size;
            if (distinct(xs) === 2 && distinct(ys) === 2) {
                const x0 = Math.max(0, Math.round(Math.min(...xs))), y0 = Math.max(0, Math.round(Math.min(...ys)));
                const x1 = Math.min(vw, Math.round(Math.min(...xs) + ax)), y1 = Math.min(vh, Math.round(Math.min(...ys) + ay));
                return (x1 > x0 && y1 > y0) ? [[x0, y0, x1 - x0, y1 - y0]] : [];
            }
        }

        let ymin = 0, ymax = vh;
        for (const { p } of polys) {
            ymin = Math.max(ymin, Math.min(...p.map(v => v[1])));
            ymax = Math.min(ymax, Math.max(...p.map(v => v[1])));
        }
        const y0 = Math.max(0, Math.floor(ymin)), y1 = Math.min(vh, Math.ceil(ymax));
        if (y1 <= y0) return [];
        const step = Math.max(1, Math.ceil((y1 - y0) / this.MAX_ROWS));

        const rects = []; let open = [];
        for (let y = y0; y < y1; y += step) {
            const h = Math.min(step, y1 - y), yc = y + h / 2;
            let spans = null;
            for (const { p, eo } of polys) {
                const s = this.spansAt(p, !!eo, yc);
                spans = spans === null ? s : this.intersectSpans(spans, s);
                if (!spans.length) break;
            }
            const next = [];
            for (const [a, b] of spans || []) {
                const x0 = Math.max(0, Math.round(a)), x1 = Math.min(vw, Math.round(b));
                if (x1 <= x0) continue;
                let r = open.find(o => o.x0 === x0 && o.x1 === x1);
                if (r) r.y1 = y + h; else { r = { x0, x1, y0: y, y1: y + h }; rects.push(r); }
                next.push(r);
            }
            open = next;
        }
        return rects.map(r => [r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0]);
    }
}

SIRCollector.SELECTOR = '.hotoe-input-region-regulator-box, [sir]'; // have to keep the old way alive
SIRCollector.TOL = 0.4; SIRCollector.MAX_ROWS = 300; 



