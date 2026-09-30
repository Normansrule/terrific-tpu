# =====================================================================
#  TinyTPU - build, test, draw
# ---------------------------------------------------------------------
#   make                 neural-network demo on both chip versions
#   make V=v1_simple     ... or just one version (v1_simple | v2_pipelined)
#   make dft             4-point Fourier transform on both versions
#   make compile-test    compile 4 networks, run them on both Verilog chips
#   make apps            image filter, quantum search, graph triangles on both versions
#   make experiments     run the 5 experiments (CSV + charts)
#   make fuzz            200 random programs on both versions
#   make scale           array sizes N = 2, 4, 8, 16 on both versions
#   make mutants         plant 16 bugs; every one must be caught
#   make jscheck         both browser models (v1 and v2) must match the RTL exactly
#   make test            everything above
#   make diagrams        regenerate every SVG in diagrams/ (runs the RTL)
#   make synth           gate counts with Yosys (sky130 area if PDK found)
#   make wave            open the waveform in GTKWave
#   make serve           the website at http://localhost:8000/web/  (3-D pages need a web server)
#   make screenshots     re-capture docs/img/*.png with a headless browser (needs Playwright)
# =====================================================================
V        ?= v1_simple v2_pipelined
SEED     ?= 1
FUZZ     ?= 200
COMMON   := $(wildcard rtl/common/*.v)
PY       := python3

.PHONY: compile-test serve screenshots all sim dft apps experiments fuzz scale mutants jscheck test diagrams synth wave clean

all: sim

build/%.vvp: $(COMMON) rtl/%/*.v tb/tb_tpu_top.v
	@mkdir -p build
	iverilog -g2012 -o $@ tb/tb_tpu_top.v $(COMMON) rtl/$*/*.v

define RUN_DEMO
	@for v in $(V); do \
	  $(MAKE) -s build/$$v.vvp; \
	  $(PY) tools/golden_model.py --demo $(1) --seed $(SEED) --out build > /dev/null; \
	  printf "%-14s %-5s" $$v $(1); \
	  vvp -n build/$$v.vvp $(2) | grep -E "cycles|PASS|FAIL" | tr -s ' ' | tr '\n' ' '; echo; \
	  vvp -n build/$$v.vvp +novcd | grep -q PASS || exit 1; \
	done
endef

sim:
	$(call RUN_DEMO,mlp,)
dft:
	$(call RUN_DEMO,dft,+novcd)

apps:
	$(call RUN_DEMO,conv,+novcd)
	$(call RUN_DEMO,grover,+novcd)
	$(call RUN_DEMO,graph,+novcd)

experiments:
	$(PY) experiments/run_all.py

compile-test:
	@for net in "8,12,8,4 16" "16,16,8 24" "4,4 1" "12,8,8,8 20"; do set -- $$net; \
	  for h in "" "--hoist"; do \
	    $(PY) tools/tpu_compile.py --layers $$1 --batch $$2 $$h --out build > build/compile.log || { cat build/compile.log; exit 1; }; \
	    for v in $(V); do $(MAKE) -s build/$$v.vvp; \
	      printf "%-12s batch %-3s %-8s %-13s" $$1 $$2 "$${h:-plain}" $$v; \
	      vvp -n build/$$v.vvp +novcd | grep -E "cycles|PASS|FAIL" | tr -s ' ' | tr '\n' ' '; echo; \
	      vvp -n build/$$v.vvp +novcd | grep -q PASS || exit 1; \
	    done; done; done

fuzz:
	@for v in $(V); do \
	  $(MAKE) -s build/$$v.vvp; fails=0; \
	  for s in $$(seq 1 $(FUZZ)); do \
	    $(PY) tools/golden_model.py --demo fuzz --seed $$s --out build > /dev/null; \
	    vvp -n build/$$v.vvp +novcd | grep -q PASS || { echo "  $$v: FAIL on fuzz seed $$s"; fails=1; }; \
	  done; \
	  [ $$fails -eq 0 ] && echo "$$v: $(FUZZ)/$(FUZZ) random programs PASS" || exit 1; \
	done

scale:
	@mkdir -p build
	@for v in $(V); do for n in 2 4 8 16; do \
	  iverilog -g2012 -Ptb_scale.N=$$n -o build/scale.vvp tb/tb_scale.v $(COMMON) rtl/$$v/*.v || exit 1; \
	  printf "%-14s" $$v; vvp -n build/scale.vvp | grep -E "PASS|FAIL"; \
	  vvp -n build/scale.vvp | grep -q PASS || exit 1; \
	done; done

mutants:
	./tools/mutation_test.sh

jscheck:
	@for v in v1_simple v2_pipelined; do $(MAKE) -s build/$$v.vvp; done
	@for v in v1_simple v2_pipelined; do flag=$$( [ $$v = v2_pipelined ] && echo v2 ); \
	  for d in mlp dft conv grover graph; do \
	    $(PY) tools/golden_model.py --demo $$d --seed $(SEED) --out build > /dev/null; \
	    node tools/check_js_sim.js build $$(vvp -n build/$$v.vvp +novcd | grep -o "in [0-9]* clock" | grep -o "[0-9]*") $$flag || exit 1; \
	  done; \
	  for s in $$(seq 1 40); do \
	    $(PY) tools/golden_model.py --demo fuzz --seed $$s --out build > /dev/null; \
	    node tools/check_js_sim.js build $$(vvp -n build/$$v.vvp +novcd | grep -o "in [0-9]* clock" | grep -o "[0-9]*") $$flag > /dev/null || { echo "$$v fuzz seed $$s"; exit 1; }; \
	  done; echo "browser model of $$v: 40 random programs cycle-exact with the RTL"; \
	done

test: sim dft apps compile-test fuzz scale jscheck mutants
	@echo; echo "  ALL TESTS PASSED"

diagrams:
	$(PY) tools/diagrams/make_all.py

synth:
	./tools/synth_report.sh

wave: 
	@$(MAKE) -s build/v1_simple.vvp
	$(PY) tools/golden_model.py --demo mlp --seed $(SEED) --out build > /dev/null
	vvp -n build/v1_simple.vvp > /dev/null
	gtkwave build/tpu.vcd sim/tpu.gtkw &

clean:
	rm -rf build tools/__pycache__ tools/diagrams/__pycache__ experiments/__pycache__

PORT ?= 8000
serve:
	@echo "open http://localhost:$(PORT)/web/   (Ctrl-C to stop)"
	$(PY) -m http.server $(PORT)

screenshots:
	$(PY) tools/screenshots.py
