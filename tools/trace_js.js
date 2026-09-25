#!/usr/bin/env node
// trace_js.js - run build/*.hex on the cycle-exact JS model and print a JSON
// trace for the experiments: per-cycle controller state and which PEs are
// doing useful work, plus event counts for the energy model.
//   usage: node tools/trace_js.js build > trace.json
const fs = require("fs"), path = require("path");
const { Chip } = require(path.join(__dirname, "..", "web", "tinytpu-core.js"));
const dir = process.argv[2] || "build", N = 4;
const lines = f => fs.readFileSync(path.join(dir, f), "utf8").trim().split(/\s+/);
const unpack = (hex, bits) => {
  const v = BigInt("0x" + hex), m = (1n << BigInt(bits)) - 1n, out = [];
  for (let i = 0; i < N; i++) { let x = Number((v >> BigInt(bits * i)) & m); if (x >= 2 ** (bits - 1)) x -= 2 ** bits; out.push(x); }
  return out;
};
const chip = new Chip(N);
chip.imem = lines("imem.hex").map(h => parseInt(h, 16) >>> 0);
chip.wmem = lines("wmem.hex").map(h => unpack(h, 8));
chip.ub = lines("ub.hex").map(h => unpack(h, 8));
const states = [], busy = [], load = [];
const ev = { mac: 0, ub_read: 0, ub_write: 0, acc_read: 0, acc_write: 0, w_read: 0 };
while (!chip.done) {
  const f = chip.fields(), st = chip.state;
  let mask = 0;
  if (st === 3) for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) {
    const v = chip.cnt - r - c; if (v >= 0 && v < f.B) mask |= 1 << (r * N + c);
  }
  states.push(st); busy.push(mask); load.push(st === 2 ? 1 : 0);
  const s = chip.tick();
  if (s.inValid) { ev.ub_read++; ev.mac += N * N; }
  if (s.ubWrEn) { ev.ub_write++; ev.acc_read++; }
  if (s.outValid) ev.acc_write++;
  if (s.wLoad) ev.w_read++;
}
process.stdout.write(JSON.stringify({ cycles: chip.cycles, states, busy, load, events: ev }));
