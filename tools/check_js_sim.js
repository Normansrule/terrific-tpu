#!/usr/bin/env node
// check_js_sim.js - runs web/tinytpu-core.js on build/*.hex and demands
// the same final memories as the answer key and the same cycle count
// as the Verilog simulation.   usage: node tools/check_js_sim.js build <rtl_cycles>
const fs = require("fs"), path = require("path");
const { Chip } = require(path.join(__dirname, "..", "web", "tinytpu-core.js"));
const dir = process.argv[2] || "build", rtlCycles = parseInt(process.argv[3]);
const N = 4;
const lines = f => fs.readFileSync(path.join(dir, f), "utf8").trim().split(/\s+/);
const unpack = (hex, bits) => {
  const v = BigInt("0x" + hex), m = (1n << BigInt(bits)) - 1n, out = [];
  for (let i = 0; i < N; i++) {
    let x = Number((v >> BigInt(bits * i)) & m);
    if (x >= 2 ** (bits - 1)) x -= 2 ** bits;
    out.push(x);
  }
  return out;
};
const chip = new Chip(N);
chip.imem = lines("imem.hex").map(h => parseInt(h, 16) >>> 0);
chip.wmem = lines("wmem.hex").map(h => unpack(h, 8));
chip.ub = lines("ub.hex").map(h => unpack(h, 8));
chip.run();
const eu = lines("expect_ub.hex").map(h => unpack(h, 8));
const ea = lines("expect_acc.hex").map(h => unpack(h, 32));
let bad = 0;
for (let i = 0; i < 256; i++) {
  if (JSON.stringify(chip.ub[i]) !== JSON.stringify(eu[i])) bad++;
  if (JSON.stringify(chip.acc[i]) !== JSON.stringify(ea[i])) bad++;
}
const cyc = isNaN(rtlCycles) ? "?" : rtlCycles;
if (bad || (cyc !== "?" && chip.cycles !== rtlCycles)) {
  console.log(`JS sim MISMATCH: ${bad} memory words differ, cycles js=${chip.cycles} rtl=${cyc}`);
  process.exit(1);
}
console.log(`JS sim matches RTL: 512 memory words, ${chip.cycles} cycles`);
