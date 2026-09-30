/* =====================================================================
 *  tinytpu-core.js  -  a cycle-exact JavaScript model of rtl/v1_simple
 * ---------------------------------------------------------------------
 *  Every register in the Verilog has a twin here, and tick() updates
 *  them all "at the clock edge" from their old values, exactly like
 *  nonblocking assignments.  `make jscheck` runs this file under Node
 *  against the Verilog simulation and demands identical memories AND
 *  an identical cycle count.
 *
 *  Also contains the assembler, so the browser can compile programs.
 * ===================================================================== */
(function (root) {
  "use strict";
  const OPC = { NOP: 0x0, LDW: 0x1, MMUL: 0x2, ACT: 0x3, HALT: 0xF };
  const STATE = ["FETCH", "DECODE", "LDW", "MMUL", "ACT", "HALT"];

  // ------------------------------------------------------------ assembler
  function assemble(text) {
    const words = [], errors = [];
    text.split("\n").forEach((raw, i) => {
      const line = raw.split(";")[0].split("#")[0].trim();
      if (!line) return;
      const parts = line.split(/\s+/);
      const op = parts[0].toUpperCase();
      const kv = {}, flags = new Set();
      parts.slice(1).forEach(p => {
        if (p.includes("=")) { const [k, v] = p.split("="); kv[k.toLowerCase()] = parseInt(v); }
        else flags.add(p.toLowerCase());
      });
      const need = (k) => { if (!(k in kv) || isNaN(kv[k])) throw new Error(`missing ${k}=`); const v = kv[k]; if (v < 0 || v > 255) throw new Error(`${k}=${v} is outside 0..255`); return v; };
      try {
        let w;
        if (op === "NOP") w = 0;
        else if (op === "HALT") w = 0xF0000000;
        else if (op === "LDW") w = (1 << 28) | (need("w") << 20);
        else if (op === "MMUL") w = (2 << 28) | (need("ub") << 20) | (need("rows") << 12) | (need("acc") << 4) | (flags.has("accumulate") ? 1 : 0);
        else if (op === "ACT") {
          const sh = kv.shift || 0; if (sh < 0 || sh > 7) throw new Error("shift must be 0..7");
          w = (3 << 28) | (need("acc") << 20) | (need("rows") << 12) | (need("ub") << 4) | (sh << 1) | (flags.has("relu") ? 1 : 0);
        } else throw new Error(`unknown instruction "${op}"`);
        words.push(w >>> 0);
      } catch (e) { errors.push(`line ${i + 1}: ${e.message}`); }
    });
    return { words, errors };
  }

  function disassemble(w) {
    const op = w >>> 28, a = (w >>> 20) & 255, b = (w >>> 12) & 255, c = (w >>> 4) & 255, f = w & 15;
    if (op === 1) return `LDW   w=${a}`;
    if (op === 2) return `MMUL  ub=${a} rows=${b} acc=${c}${f & 1 ? " accumulate" : ""}`;
    if (op === 3) return `ACT   acc=${a} rows=${b} ub=${c}${f & 1 ? " relu" : ""} shift=${f >> 1}`;
    if (op === 15) return "HALT";
    return "NOP";
  }

  // ------------------------------------------------------------ the chip
  class Chip {
    constructor(N = 4) {
      this.N = N; this.LAT = 2 * N - 1;
      const z = () => Array(N).fill(0);
      this.imem = Array(256).fill(0xF0000000);
      this.wmem = Array.from({ length: 256 }, z);
      this.ub = Array.from({ length: 256 }, z);
      this.acc = Array.from({ length: 256 }, z);
      this.reset();
    }
    reset() {
      const N = this.N;
      this.state = 0; this.pc = 0; this.ir = 0; this.cnt = 0;
      this.accWr = 0; this.accumulate = 0; this.done = false; this.cycles = 0;
      this.inSkew = Array.from({ length: N }, (_, k) => Array(k).fill(0));
      this.outSkew = Array.from({ length: N }, (_, k) => Array(N - 1 - k).fill(0));
      this.W = Array.from({ length: N }, () => Array(N).fill(0));
      this.A = Array.from({ length: N }, () => Array(N).fill(0));
      this.P = Array.from({ length: N }, () => Array(N).fill(0));
      this.validPipe = Array(this.LAT).fill(0);
      this.last = null;
    }
    fields() {
      const w = this.ir;
      return { op: w >>> 28, A: (w >>> 20) & 255, B: (w >>> 12) & 255, C: (w >>> 4) & 255, F: w & 15 };
    }
    // combinational logic for the current cycle (controller.v always @(*))
    comb() {
      const N = this.N, { A, B, C, F } = this.fields();
      const s = { wLoad: 0, wmemAddr: 0, inValid: 0, ubRd: 0, accRd: 0, ubWrEn: 0, ubWr: 0, relu: F & 1, shift: F >> 1 };
      if (this.state === 2) { s.wLoad = 1; s.wmemAddr = (A + (N - 1 - this.cnt)) & 255; }
      if (this.state === 3) { s.inValid = this.cnt < B ? 1 : 0; s.ubRd = (A + this.cnt) & 255; }
      if (this.state === 4) { s.accRd = (A + this.cnt) & 255; s.ubWrEn = 1; s.ubWr = (C + this.cnt) & 255; }
      s.inVec = s.inValid ? this.ub[s.ubRd].slice() : Array(N).fill(0);
      s.skewed = s.inVec.map((v, k) => (k === 0 ? v : this.inSkew[k][k - 1]));
      s.pBottom = this.P[N - 1].slice();
      s.result = s.pBottom.map((v, c) => (c === N - 1 ? v : this.outSkew[c][N - 2 - c]));
      s.outValid = this.validPipe[this.LAT - 1];
      s.wTop = this.wmem[s.wmemAddr].slice();
      const accRow = this.acc[s.accRd];
      s.actOut = accRow.map(v => {
        let r = (s.relu && v < 0) ? 0 : v;
        r = r >> s.shift;
        return Math.max(-128, Math.min(127, r));
      });
      return s;
    }
    tick() {
      if (this.done) return null;
      const N = this.N, s = this.comb(), f = this.fields();
      // ---- datapath registers ----
      const nW = this.W.map(r => r.slice()), nA = this.A.map(r => r.slice()), nP = this.P.map(r => r.slice());
      for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) {
        const aIn = c === 0 ? s.skewed[r] : this.A[r][c - 1];
        const pIn = r === 0 ? 0 : this.P[r - 1][c];
        if (s.wLoad) nW[r][c] = r === 0 ? s.wTop[c] : this.W[r - 1][c];
        nA[r][c] = aIn;
        nP[r][c] = (pIn + aIn * this.W[r][c]) | 0;
      }
      for (let k = 1; k < N; k++) { this.inSkew[k].pop(); this.inSkew[k].unshift(s.inVec[k]); }
      for (let c = 0; c < N - 1; c++) { this.outSkew[c].pop(); this.outSkew[c].unshift(s.pBottom[c]); }
      if (s.outValid) {
        const old = this.acc[this.accWr];
        this.acc[this.accWr] = s.result.map((v, l) => ((this.accumulate ? old[l] : 0) + v) | 0);
      }
      if (s.ubWrEn) this.ub[s.ubWr] = s.actOut.slice();
      this.validPipe.pop(); this.validPipe.unshift(s.inValid);
      this.W = nW; this.A = nA; this.P = nP;
      // ---- controller registers (controller.v always @(posedge clk)) ----
      if (!this.done) this.cycles++;
      if (s.outValid) this.accWr = (this.accWr + 1) & 255;
      const LAT = this.LAT;
      switch (this.state) {
        case 0: this.ir = this.imem[this.pc]; this.pc = (this.pc + 1) & 255; this.cnt = 0; this.state = 1; break;
        case 1:
          if (f.op === 1) this.state = 2;
          else if (f.op === 2) { this.accWr = f.C; this.accumulate = f.F & 1; this.state = 3; }
          else if (f.op === 3) this.state = f.B === 0 ? 0 : 4;
          else if (f.op === 15) this.state = 5;
          else this.state = 0;
          break;
        case 2: this.cnt++; if (this.cnt - 1 === N - 1) this.state = 0; break;
        case 3: this.cnt++; if (this.cnt - 1 === f.B + LAT - 1) this.state = 0; break;
        case 4: this.cnt++; if (this.cnt - 1 === f.B - 1) this.state = 0; break;
        case 5: this.done = true; break;
      }
      this.last = s;
      return s;
    }
    run(max = 100000) { while (!this.done && max-- > 0) this.tick(); return this; }
    get stateName() { return STATE[this.state]; }
    // is PE(r, c) doing useful work this cycle? (for visualizations)
    peBusy(r, c) { const v = this.cnt - r - c; return this.state === 3 && !this.done && v >= 0 && v < this.fields().B; }
    get version() { return "v1_simple"; }
    get resultAddr() { return this.accWr; }
  }

  // ===================================================================
  //  ChipV2 - cycle-exact model of rtl/v2_pipelined
  //  Adds: shadow + active weights per PE, a swap flag that rides the
  //  skew with the first vector of each MMUL, a metadata pipeline
  //  (valid, accumulate, address) next to the data, and the DECODE
  //  stall rules (swap_wait for LDW, pipe_busy for ACT and HALT).
  // ===================================================================
  class ChipV2 extends Chip {
    reset() {
      super.reset();
      const N = this.N;
      this.Wsh = Array.from({ length: N }, () => Array(N).fill(0));   // shadow weights
      this.W = Array.from({ length: N }, () => Array(N).fill(0));     // active weights
      this.S = Array.from({ length: N }, () => Array(N).fill(0));     // swap flag registers
      this.AV = Array.from({ length: N }, () => Array(N).fill(0));    // valid bits (visualization only)
      this.inSkewS = Array.from({ length: N }, (_, k) => Array(k).fill(0));
      this.inSkewV = Array.from({ length: N }, (_, k) => Array(k).fill(0));
      this.accumPipe = Array(this.LAT).fill(0);
      this.addrPipe = Array(this.LAT).fill(0);
      this.swapWait = 0; this.stallCycles = 0;
    }
    get version() { return "v2_pipelined"; }
    get resultAddr() { return this.addrPipe[this.LAT - 1]; }
    comb() {
      const N = this.N, { op, A, B, C, F } = this.fields();
      const pipeBusy = this.validPipe.some(v => v);
      const s = { wLoad: 0, wmemAddr: 0, inValid: 0, inSwap: 0, ubRd: 0, accRd: 0, ubWrEn: 0, ubWr: 0, relu: F & 1, shift: F >> 1,
                  inAccAddr: (C + this.cnt) & 255, inAccumulate: F & 1, pipeBusy };
      s.stall = this.state === 1 && ((op === 1 && this.swapWait !== 0) || ((op === 3 || op === 15) && pipeBusy));
      if (this.state === 2) { s.wLoad = 1; s.wmemAddr = (A + (N - 1 - this.cnt)) & 255; }
      if (this.state === 3) { s.inValid = 1; s.inSwap = this.cnt === 0 ? 1 : 0; s.ubRd = (A + this.cnt) & 255; }
      if (this.state === 4) { s.accRd = (A + this.cnt) & 255; s.ubWrEn = 1; s.ubWr = (C + this.cnt) & 255; }
      s.inVec = s.inValid ? this.ub[s.ubRd].slice() : Array(N).fill(0);
      const sw = s.inSwap & s.inValid;
      s.skewed = s.inVec.map((v, k) => (k === 0 ? v : this.inSkew[k][k - 1]));
      s.skewedS = s.inVec.map((_, k) => (k === 0 ? sw : this.inSkewS[k][k - 1]));
      s.skewedV = s.inVec.map((_, k) => (k === 0 ? s.inValid : this.inSkewV[k][k - 1]));
      s.pBottom = this.P[N - 1].slice();
      s.result = s.pBottom.map((v, c) => (c === N - 1 ? v : this.outSkew[c][N - 2 - c]));
      s.outValid = this.validPipe[this.LAT - 1];
      s.wTop = this.wmem[s.wmemAddr].slice();
      s.actOut = this.acc[s.accRd].map(v => Math.max(-128, Math.min(127, ((s.relu && v < 0) ? 0 : v) >> s.shift)));
      return s;
    }
    peBusy(r, c) { const s = this.comb(); return !!(c === 0 ? s.skewedV[r] : this.AV[r][c - 1]); }
    tick() {
      if (this.done) return null;
      const N = this.N, LAT = this.LAT, s = this.comb(), f = this.fields();
      const nSh = this.Wsh.map(r => r.slice()), nW = this.W.map(r => r.slice()), nA = this.A.map(r => r.slice()),
            nS = this.S.map(r => r.slice()), nP = this.P.map(r => r.slice()), nV = this.AV.map(r => r.slice());
      for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) {
        const aIn = c === 0 ? s.skewed[r] : this.A[r][c - 1];
        const sIn = c === 0 ? s.skewedS[r] : this.S[r][c - 1];
        const vIn = c === 0 ? s.skewedV[r] : this.AV[r][c - 1];
        const pIn = r === 0 ? 0 : this.P[r - 1][c];
        const wUse = sIn ? this.Wsh[r][c] : this.W[r][c];
        if (s.wLoad) nSh[r][c] = r === 0 ? s.wTop[c] : this.Wsh[r - 1][c];
        if (sIn) nW[r][c] = this.Wsh[r][c];
        nA[r][c] = aIn; nS[r][c] = sIn; nV[r][c] = vIn;
        nP[r][c] = (pIn + aIn * wUse) | 0;
      }
      const sw = s.inSwap & s.inValid;
      for (let k = 1; k < N; k++) {
        this.inSkew[k].pop(); this.inSkew[k].unshift(s.inVec[k]);
        this.inSkewS[k].pop(); this.inSkewS[k].unshift(sw);
        this.inSkewV[k].pop(); this.inSkewV[k].unshift(s.inValid);
      }
      for (let c = 0; c < N - 1; c++) { this.outSkew[c].pop(); this.outSkew[c].unshift(s.pBottom[c]); }
      if (s.outValid) {
        const a = this.addrPipe[LAT - 1], old = this.acc[a];
        this.acc[a] = s.result.map((v, l) => ((this.accumPipe[LAT - 1] ? old[l] : 0) + v) | 0);
      }
      if (s.ubWrEn) this.ub[s.ubWr] = s.actOut.slice();
      this.validPipe.pop(); this.validPipe.unshift(s.inValid);
      this.accumPipe.pop(); this.accumPipe.unshift(s.inAccumulate);
      this.addrPipe.pop(); this.addrPipe.unshift(s.inAccAddr);
      this.Wsh = nSh; this.W = nW; this.A = nA; this.S = nS; this.P = nP; this.AV = nV;
      // controller (controller_pipe.v)
      if (!this.done) this.cycles++;
      if (this.swapWait !== 0) this.swapWait--;
      switch (this.state) {
        case 0: this.ir = this.imem[this.pc]; this.pc = (this.pc + 1) & 255; this.cnt = 0; this.state = 1; break;
        case 1:
          if (s.stall) this.stallCycles++;
          else if (f.op === 1) this.state = 2;
          else if (f.op === 2) this.state = f.B === 0 ? 0 : 3;
          else if (f.op === 3) this.state = f.B === 0 ? 0 : 4;
          else if (f.op === 15) this.state = 5;
          else this.state = 0;
          break;
        case 2: this.cnt++; if (this.cnt - 1 === N - 1) this.state = 0; break;
        case 3: if (this.cnt === 0) this.swapWait = 2 * N - 3; this.cnt++; if (this.cnt - 1 === f.B - 1) this.state = 0; break;
        case 4: this.cnt++; if (this.cnt - 1 === f.B - 1) this.state = 0; break;
        case 5: this.done = true; break;
      }
      this.last = s;
      return s;
    }
  }

  const api = { assemble, disassemble, Chip, ChipV2, STATE, OPC };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.TinyTPUCore = api;
})(typeof window !== "undefined" ? window : globalThis);
