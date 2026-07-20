PROJECT_ROOT := $(abspath $(CURDIR)/..)
RTL_DIR      := $(PROJECT_ROOT)/rtl
TB_DIR       := $(PROJECT_ROOT)/tb

export PYTHONPATH := $(TB_DIR):$(PYTHONPATH)

VERILOG_SOURCES := \
    $(RTL_DIR)/async_fifo.v \
    $(RTL_DIR)/dual_port_ram.v \
    $(RTL_DIR)/fifo_rd_ctrl.v \
    $(RTL_DIR)/fifo_wr_ctrl.v \
    $(RTL_DIR)/synchronizer.v

TOPLEVEL := async_fifo
COCOTB_TEST_MODULES := test_fifo
TOPLEVEL_LANG := verilog
SIM := icarus

include $(shell cocotb-config --makefiles)/Makefile.sim

export COCOTB_RESOLVE_X=ZEROS
export WAVES=1

