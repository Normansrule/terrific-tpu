/* =====================================================================
   compiler.js - a tiny neural-network compiler for TinyTPU
   ---------------------------------------------------------------------
   Input : layer widths [K0, N1, N2, ...] (multiples of 4), batch size M,
           integer weights and inputs, ReLU on/off per layer.
   Output: TinyTPU assembly, memory images, and a memory map.

   What a real compiler (XLA, TVM) does, in miniature:
     1. TILING      - cut each K x N weight matrix into 4 x 4 tiles
     2. ALLOCATION  - place weights, activations, partial sums in memory
     3. SCHEDULING  - order LDW / MMUL / ACT; optionally hoist the next
                      LDW above an ACT so v2 can hide the drain
     4. CALIBRATION - pick each layer's ACT shift by running the integer
                      math once ("profiling") so results fit in 8 bits
   Mirrors tools/tpu_compile.py exactly; `make compile-test` checks the
   Python version on both Verilog chips.
   ===================================================================== */
(function (root) {
  "use strict";
  function lcg(seed) { let s = seed >>> 0; return (lo, hi) => { s = (s * 1664525 + 1013904223) >>> 0; return lo + ((s >>> 16) % (hi - lo + 1)); }; }
  const mm = (X, W) => X.map(x => W[0].map((_, j) => x.reduce((s, v, k) => s + v * W[k][j], 0)));

  function makeData(widths, M, seed) {
    const r = lcg(seed);
    const X = [...Array(M)].map(() => [...Array(widths[0])].map(() => r(-8, 7)));
    const Ws = widths.slice(1).map((n, l) => [...Array(widths[l])].map(() => [...Array(n)].map(() => r(-3, 3))));
    return { X, Ws };
  }

  function compile(opts) {
    const { widths, M, relu, hoist, X, Ws } = opts;
    const errors = [], warnings = [];
    if (widths.some(w => w % 4 || w < 4)) errors.push("every layer width must be a multiple of 4");
    if (M < 1 || M > 255) errors.push("batch size must be 1..255");
    if (errors.length) return { errors };
    const wmem = [], ub = [], regions = { wmem: [], ub: [], acc: [] };
    // ---- 1 + 2: tile the weights and place them in weight memory
    const tileAddr = [];
    Ws.forEach((W, l) => {
      const K = widths[l], N = widths[l + 1]; tileAddr.push([]);
      const start = wmem.length;
      for (let kt = 0; kt < K / 4; kt++) { tileAddr[l].push([]); for (let ct = 0; ct < N / 4; ct++) {
        tileAddr[l][kt].push(wmem.length);
        for (let i = 0; i < 4; i++) wmem.push(W[kt * 4 + i].slice(ct * 4, ct * 4 + 4)); } }
      regions.wmem.push({ name: `W${l + 1}`, from: start, to: wmem.length - 1, layer: l });
    });
    if (wmem.length > 256) errors.push(`weights need ${wmem.length} rows of weight memory; only 256 exist`);
    // ---- activations: the input, then each layer's output, bump-allocated in the Unified Buffer
    let ubNext = 0; const actBase = [];
    const place = (name, K, layer) => { const base = ubNext; actBase.push(base); ubNext += (K / 4) * M;
      regions.ub.push({ name, from: base, to: ubNext - 1, layer }); return base; };
    place("X", widths[0], -1);
    X.forEach((x, i) => { for (let kt = 0; kt < widths[0] / 4; kt++) ub[actBase[0] + kt * M + i] = x.slice(kt * 4, kt * 4 + 4); });
    for (let l = 0; l < Ws.length; l++) place(l === Ws.length - 1 ? "Y" : `H${l + 1}`, widths[l + 1], l);
    if (ubNext > 256) errors.push(`activations need ${ubNext} Unified Buffer rows; only 256 exist (use a smaller batch)`);
    const maxAcc = Math.max(...widths.slice(1).map(n => (n / 4) * M));
    if (maxAcc > 256) errors.push(`a layer needs ${maxAcc} accumulator rows; only 256 exist`);
    if (errors.length) return { errors };
    // ---- 4: calibration - run the integer math once and pick shifts
    let A = X; const shifts = [], ref = [];
    Ws.forEach((W, l) => {
      const acc = mm(A, W), useRelu = relu[l];
      const peak = Math.max(1, ...acc.flat().map(v => Math.abs(useRelu && v < 0 ? 0 : v)));
      let s = 0; while ((peak >> s) > 127 && s < 7) s++;
      if ((peak >> s) > 127) warnings.push(`layer ${l + 1}: values up to ${peak} need a shift above 7; results will saturate`);
      shifts.push(s);
      A = acc.map(row => row.map(v => Math.max(-128, Math.min(127, ((useRelu && v < 0) ? 0 : v) >> s))));
      ref.push(A);
      regions.acc.push({ name: `layer ${l + 1}`, from: 0, to: (widths[l + 1] / 4) * M - 1, layer: l });
    });
    // ---- 3: scheduling
    const prog = [], notes = [];
    let pending = null;
    const emit = (line, note) => { prog.push(line); notes.push(note || ""); };
    const ldw = (addr, note) => { emit(`LDW   w=${addr}`, note); if (pending) { emit(pending[0], pending[1] + (hoist ? " (hoisted after the LDW above)" : "")); pending = null; } };
    Ws.forEach((W, l) => {
      const K = widths[l], N = widths[l + 1];
      for (let ct = 0; ct < N / 4; ct++) {
        for (let kt = 0; kt < K / 4; kt++) {
          ldw(tileAddr[l][kt][ct], `layer ${l + 1}: weight tile rows ${kt * 4}-${kt * 4 + 3}, cols ${ct * 4}-${ct * 4 + 3}`);
          emit(`MMUL  ub=${actBase[l] + kt * M} rows=${M} acc=${ct * M}${kt ? " accumulate" : ""}`, `layer ${l + 1}: ${kt ? "add" : "start"} K-tile ${kt} into column tile ${ct}`);
        }
        const act = [`ACT   acc=${ct * M} rows=${M} ub=${actBase[l + 1] + ct * M}${relu[l] ? " relu" : ""} shift=${shifts[l]}`, `layer ${l + 1}: finish column tile ${ct}`];
        if (hoist) pending = act; else emit(act[0], act[1]);
      }
    });
    if (pending) emit(pending[0], pending[1]);
    emit("HALT");
    // expected output location
    const L = Ws.length, outBase = actBase[L], NO = widths[L];
    return { errors: [], warnings, prog, notes, wmem, ub, regions, shifts, ref, outBase, NO, M,
             macs: Ws.reduce((s, W, l) => s + M * widths[l] * widths[l + 1], 0) };
  }
  // read the network's output back out of the Unified Buffer (column tiles are stored one after another)
  function readOutput(ubMem, c) {
    return [...Array(c.M)].map((_, i) => [].concat(...[...Array(c.NO / 4)].map((_, ct) => ubMem[c.outBase + ct * c.M + i])));
  }
  const api = { compile, makeData, readOutput, lcg };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.TinyTPUCompiler = api;
})(typeof window !== "undefined" ? window : globalThis);
