#!/usr/bin/env python3
"""
tpu_host.py - run programs on a TinyTPU inside an FPGA, over a USB serial port.

The FPGA runs rtl/fpga/tpu_uart_top.v (see docs/21-fpga.md). This script
speaks its one-letter protocol: load the program and data, press "go",
read every result back, and compare with the same answer key the Verilog
testbench uses.

    pip install pyserial
    python3 tools/tpu_host.py --port /dev/ttyUSB0 --demo mlp
    python3 tools/tpu_host.py --fake --demo conv       # no board: a virtual chip

--fake swaps the serial port for a virtual board that implements the same
protocol on top of the instruction-level model, so you can try the host
side (and this script's own logic) before any hardware arrives.
"""
import argparse
import os
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def read_hex(path, bits, whole=False):
    """One row per line: a whole word (instructions) or 4 unsigned lanes of `bits` bits."""
    rows = []
    for line in open(path):
        line = line.split("//")[0].strip()
        if line:
            v = int(line, 16)
            rows.append(v if whole else [(v >> (bits * i)) & ((1 << bits) - 1) for i in range(4)])
    return rows


def signed(v, bits):
    return v - (1 << bits) if v >> (bits - 1) else v


class FakeBoard:
    """A virtual FPGA: the same byte protocol, backed by the instruction-level model."""
    def __init__(self):
        from tpu_isa_sim import TinyTPU
        self.TinyTPU = TinyTPU
        self.imem, self.wmem, self.ub, self.acc = [0xF0000000] * 256, [[0] * 4 for _ in range(256)], [[0] * 4 for _ in range(256)], [[0] * 4 for _ in range(256)]
        self.inbuf, self.out = b"", b""

    def write(self, data):
        self.inbuf += data
        while self.inbuf:
            c = chr(self.inbuf[0])
            need = {"P": 1, "G": 1, "R": 2, "A": 2, "I": 6, "W": 6, "U": 6}.get(c, 1)
            if len(self.inbuf) < need:
                return
            pkt, self.inbuf = self.inbuf[:need], self.inbuf[need:]
            if c == "P":
                self.out += b"K"
            elif c == "I":
                self.imem[pkt[1]] = int.from_bytes(pkt[2:6], "big")
            elif c in "WU":
                (self.wmem if c == "W" else self.ub)[pkt[1]] = [signed(b, 8) for b in pkt[2:6]]
            elif c == "G":
                t = self.TinyTPU(4)
                t.wmem, t.ub, t.acc = [r[:] for r in self.wmem], [r[:] for r in self.ub], [r[:] for r in self.acc]
                t.run(self.imem)
                self.ub, self.acc = t.ub, t.acc
                self.out += b"D" + (0).to_bytes(4, "big")         # the model has no clock: 0 cycles
            elif c == "R":
                self.out += bytes(v & 255 for v in self.ub[pkt[1]])
            elif c == "A":
                self.out += b"".join((v & 0xFFFFFFFF).to_bytes(4, "big") for v in self.acc[pkt[1]])

    def read(self, n):
        d, self.out = self.out[:n], self.out[n:]
        return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial port, e.g. /dev/ttyUSB0 (Linux) or COM5 (Windows)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--fake", action="store_true", help="use a virtual board instead of real hardware")
    ap.add_argument("--demo", default="mlp", help="mlp, dft, conv, grover, graph, or fuzz")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if not a.fake and not a.port:
        ap.error("give --port, or --fake to try without a board")
    build = os.path.join(HERE, "..", "build")
    subprocess.run([sys.executable, os.path.join(HERE, "golden_model.py"), "--demo", a.demo, "--seed", str(a.seed), "--out", build],
                   check=True, stdout=subprocess.DEVNULL)
    imem, wmem, ub = read_hex(f"{build}/imem.hex", 32, whole=True), read_hex(f"{build}/wmem.hex", 8), read_hex(f"{build}/ub.hex", 8)
    eub, eacc = read_hex(f"{build}/expect_ub.hex", 8), read_hex(f"{build}/expect_acc.hex", 32)

    if a.fake:
        dev = FakeBoard()
    else:
        import serial                                     # pip install pyserial
        dev = serial.Serial(a.port, a.baud, timeout=2)
        time.sleep(0.2)
        dev.reset_input_buffer()

    def ask(data, n):
        dev.write(data)
        got = dev.read(n)
        if len(got) != n:
            sys.exit(f"no answer from the board (sent {data[:1]!r}, got {got!r}); check the port, baud rate and bitstream")
        return got

    assert ask(b"P", 1) == b"K", "ping failed"
    print(f"connected to {'the virtual board' if a.fake else a.port}")
    last = max(i for i, w in enumerate(imem) if w >> 28 != 0xF) + 1
    t0 = time.time()
    for i in range(last + 1):
        dev.write(b"I" + bytes([i]) + imem[i].to_bytes(4, "big"))
    for tag, mem in ((b"W", wmem), (b"U", ub)):
        for i, row in enumerate(mem):
            if any(row):
                dev.write(tag + bytes([i]) + bytes(row))
    print(f"loaded {last + 1} instructions and data in {time.time() - t0:.2f} s")
    reply = ask(b"G", 5)
    assert reply[:1] == b"D", f"unexpected reply {reply!r}"
    cycles = int.from_bytes(reply[1:], "big")
    errors = 0
    for i in range(256):
        if list(ask(b"R" + bytes([i]), 4)) != eub[i]:
            errors += 1
        raw = ask(b"A" + bytes([i]), 16)
        if [int.from_bytes(raw[4 * k:4 * k + 4], "big") for k in range(4)] != eacc[i]:
            errors += 1
    print(f"ran {a.demo}: {cycles} clock cycles on the chip" if cycles else f"ran {a.demo} on the virtual board")
    print("PASS - all 512 memory words match the answer key" if errors == 0 else f"FAIL - {errors} mismatches")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
