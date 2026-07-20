import cocotb
import random
from collections import deque
from cocotb.triggers import (
    FallingEdge,
    RisingEdge,
    Timer,
    SimTimeoutError,
    with_timeout,
)

FAST_CLK = 20
SLOW_CLK = 325.52
WIDTH = 64
ADDR_WIDTH = 3
DEPTH = 1 << ADDR_WIDTH
PTR_WIDTH = ADDR_WIDTH + 1
MASK = (1<<WIDTH)-1

async def fifo_reset(dut):
  dut.wr_en.value = 0
  dut.rd_en.value = 0
  dut.d_in.value = 0

  dut.wr_reset.value = 1
  dut.rd_reset.value = 1

  for _ in range(2):
    await RisingEdge(dut.wr_clk)

  for _ in range(2):
    await RisingEdge(dut.rd_clk)

  dut.wr_reset.value = 0
  dut.rd_reset.value = 0

  for _ in range(2):
    await RisingEdge(dut.wr_clk)

  for _ in range(2):
    await RisingEdge(dut.rd_clk)

def appending(input_frame):
  result = []
  for left, right in input_frame:
    word = ((MASK & left) << WIDTH) | (MASK & right)
    result.append(word)
  return result

async def write_frame(dut, words):
  dut.wr_en.value = 0
  for word in words:
    while int(dut.full.value) == 1:
      await FallingEdge(dut.wr_clk)
    
    dut.wr_en.value = 1
    dut.d_in.value = word

    await RisingEdge(dut.wr_clk)
    
    await FallingEdge(dut.wr_clk)
    dut.wr_en.value = 0

async def read_frame(dut, nbr_of_frame):
  output = []
  while len(output) < nbr_of_frame:
    while dut.empty.value == 1:
      await FallingEdge(dut.rd_clk)
    
    dut.rd_en.value = 1
    await RisingEdge(dut.rd_clk)

    await FallingEdge(dut.rd_clk)
    dut.rd_en.value = 0

    await RisingEdge(dut.rd_clk)
    output.append(int(dut.d_out.value))

  return output

async def clock_start(dut, wr_period, rd_period):
  # wr_clk represents the I²S receiver/SCK domain.
  cocotb.start_soon(Clock(dut.wr_clk, wr_period, unit="ns").start())
  # rd_clk represents the faster DSP/FIR domain
  cocotb.start_soon(Clock(dut.rd_clk, rd_period, unit="ns").start())

async def random_write(dut, scoreboard, nbr_of_cycles):
  dut.wr_en.value = 0
  for _ in range(nbr_of_cycles):
    await FallingEdge(dut.wr_clk)
    requested_write = random.random() < 0.5
    full_before_edge = int(dut.full.value)
    word = random.getrandbits(WIDTH)

    dut.d_in.value = word
    dut.wr_en.value = requested_write

    await RisingEdge(dut.wr_clk)


    if requested_write and not full_before_edge:
      scoreboard.append(word)
      assert len(scoreboard) <= DEPTH,(
        f"Scoreboard exceeded FIFO depth: "
        f"{len(scoreboard)} > {DEPTH}"
      )
    
  await FallingEdge(dut.wr_clk)
  dut.wr_en.value = 0

async def random_read(dut, scoreboard, nbr_of_cycles):
  dut.rd_en.value = 0
  for _ in range(nbr_of_cycles):
    await FallingEdge(dut.rd_clk)
    requested_read = random.random() < 0.5
    empty_before_edge = int(dut.empty.value)

    dut.rd_en.value = requested_read

    await RisingEdge(dut.rd_clk)

    if requested_read and not empty_before_edge:
      expected = scoreboard.popleft()
      await FallingEdge(dut.rd_clk)
      dut.rd_en.value = 0
      await RisingEdge(dut.rd_clk)
      actual = int(dut.d_out.value)
      assert actual == expected, (
        f"expected {expected}, "
        f"got {actual}"
      )  
  await FallingEdge(dut.rd_clk)
  dut.rd_en.value = 0

async def drain_fifo(dut, scoreboard):
  dut.rd_en.value = 0
  while scoreboard:

    await FallingEdge(dut.rd_clk)

    empty_before_edge = int(dut.empty.value)

    if empty_before_edge:
      continue

    dut.rd_en.value = 1
    await RisingEdge(dut.rd_clk)

    await FallingEdge(dut.rd_clk)
    dut.rd_en.value = 0

    await RisingEdge(dut.rd_clk)

    expected = scoreboard.popleft()
    actual = int(dut.d_out.value)

    assert actual == expected, (
      f"FIFO mismatch: expected {expected}, "
      f"got {actual}"
    )

  for _ in range(4):
    await RisingEdge(dut.rd_clk)
    if int(dut.empty.value):
      break
  else: 
    raise AssertionError("FIFO did not assert empty after draining")
    
  assert int(dut.empty.value) == 1,(
    f"FIFO should have read all the values"
  )

async def clock_start_with_delay(dut, wr_period, rd_period, delay):
  cocotb.start_soon(Clock(dut.wr_clk, wr_period, unit="ns").start())
  await Timer(delay, unit="ns")
  cocotb.start_soon(Clock(dut.rd_clk, rd_period, unit="ns").start())

async def frequency_random_test(dut, wr_clk, rd_clk, delay):
  random.seed(1)
  scoreboard = deque()
  await clock_start_with_delay(dut, wr_clk, rd_clk, delay)
  await fifo_reset(dut)

  write_task = cocotb.start_soon(random_write(dut, scoreboard, 5000))
  read_task = cocotb.start_soon(random_read(dut, scoreboard, 5000))

  await write_task
  await read_task

  await drain_fifo(dut, scoreboard)

  assert not scoreboard


async def run_frequency_test(dut, wr_clk, rd_clk, nbr_of_frame):
  random.seed(1)

  await clock_start(dut, wr_clk, rd_clk)
  await fifo_reset(dut)
  
  input_frames = []
  for i in range(nbr_of_frame):
    left = (i + 1) & MASK
    right = (i + 100) & MASK
    input_frames.append((left,right))
  expected_words = appending(input_frames)

  write = cocotb.start_soon(write_frame(dut, expected_words))
  read = cocotb.start_soon(read_frame(dut, len(input_frames)))

  try:
    await with_timeout(write, 700, "us")
  except SimTimeoutError:
    raise AssertionError(
      "Writer timed out. "
    )

  try:
    actual_words = await with_timeout(read, 700,"us")
  except SimTimeoutError:
    raise AssertionError(
        "Reader timed out. "
    )

  for index, (expected, actual) in enumerate(
    zip(expected_words, actual_words)
  ):
    assert actual == expected, (
      f"Mismatch at index {index}: "
      f"expected {expected}, "
      f"got {actual}"
    )
  while not int(dut.empty.value):
    await RisingEdge(dut.rd_clk)

  assert int(dut.empty.value) == 1

async def frequency_reset_behavior(dut, wr_clk, rd_clk):
  await clock_start(dut, wr_clk, rd_clk)
  await fifo_reset(dut)

  assert int(dut.full.value) == 0, (
    f"Expected full=0 after reset, got {dut.full.value}"
  )
  
  assert int(dut.wr_bptr.value) == 0, (
    f"Expected write pointer=0, got {dut.wr_bptr.value}"
  )

  assert int(dut.empty.value) == 1, (
    f"Expected empty=1 after reset, got {dut.empty.value}"
  )
  
  assert int(dut.rd_bptr.value) == 0, (
    f"Expected read pointer=0, got {dut.rd_bptr.value}"
  )

async def frequency_ordering_test(dut, wr_clk, rd_clk):
  await clock_start(dut, wr_clk, rd_clk)
  await fifo_reset(dut)
  
  input_frames = [(0x001, 0x0101),
                 (0x002, 0x0102),
                 (0x003, 0x0103),
                 (0x004, 0x0104)
  ]

  expected_words = appending(input_frames)
  write = cocotb.start_soon(write_frame(dut, appending(input_frames)))
  read = cocotb.start_soon(read_frame(dut, len(input_frames)))

  await write 
  actual_words = await read

  assert expected_words == actual_words,(
    f"Expected: {input_frames}\n"
    f"Got: {actual_words}"
  )

async def frequency_full_protection(dut, wr_clk, rd_clk):
  random.seed(1)
  await clock_start(dut, wr_clk, rd_clk)
  await fifo_reset(dut)
  
  input_frames = []
  for _ in range(8):
    left = random.getrandbits(WIDTH)
    right = random.getrandbits(WIDTH)
    input_frames.append((left,right))
  
  ninth_frame = [(0x001, 0x0100)]
  expected_words = appending(input_frames)

  await write_frame(dut, expected_words)
  await RisingEdge(dut.wr_clk)
  
  assert dut.full.value == 1,(
    f"FIFO should be full after 8 accepted writes"
  )  

  old_pointer = int(dut.wr_bptr.value)
  
  # Trying to push the ninth frame into fifo
  await FallingEdge(dut.wr_clk)
  dut.wr_en.value = 1
  dut.d_in.value = appending(ninth_frame)[0]
  await RisingEdge(dut.wr_clk)
  await FallingEdge(dut.wr_clk)
  dut.wr_en.value = 0
  await RisingEdge(dut.wr_clk)

  assert int(dut.wr_bptr.value) == old_pointer,(
    f"Write pointer advanced while FIFO was full"
  )

  actual_words = await read_frame(dut, len(input_frames))
  assert actual_words == expected_words,(
    f"Expected: {[hex(x) for x in expected_words]}\n"
    f"Got:      {[hex(x) for x in actual_words]}"
  )

async def frequency_empty_protection(dut, wr_clk, rd_clk):
  await clock_start(dut, wr_clk, rd_clk)
  await fifo_reset(dut)

  input_frames = []
  for i in range(8):
    left = (i + 1) & MASK
    right = (i + 100) & MASK
    input_frames.append((left,right))

  expected_words = appending(input_frames)
  write = cocotb.start_soon(write_frame(dut, appending(input_frames)))
  read = cocotb.start_soon(read_frame(dut, len(input_frames)))

  await write 
  actual_words = await read

  assert actual_words == expected_words,(
    f"Expected: {[hex(x) for x in expected_words]}\n"
    f"Got:      {[hex(x) for x in actual_words]}"
  )

  await RisingEdge(dut.rd_clk)
  old_pointer = int(dut.rd_bptr.value)

  assert dut.empty.value == 1,(
    f"FIFO should be empty after 8 accepted reads"
  )

  await FallingEdge(dut.rd_clk)
  dut.rd_en.value = 1
  await FallingEdge(dut.rd_clk)
  dut.rd_en.value = 0
  await RisingEdge(dut.rd_clk)
  assert old_pointer == int(dut.rd_bptr.value),(
    f"Read pointer advanced while FIFO was empty"
  )


# _____________Reset behavior test_____________
@cocotb.test()
async def wr_faster_reset_behavior(dut):
  await frequency_reset_behavior(dut, FAST_CLK, SLOW_CLK)

@cocotb.test()
async def rd_faster_reset_behavior(dut):
  await frequency_reset_behavior(dut, SLOW_CLK, FAST_CLK)

@cocotb.test()
async def nearly_equal_faster_reset_behavior(dut):
  await frequency_reset_behavior(dut, 20, 21)


# _____________Ordering test_____________
@cocotb.test()
async def wr_faster_ordering(dut):
  await frequency_ordering_test(dut, FAST_CLK, SLOW_CLK)

@cocotb.test()
async def rd_faster_ordering(dut):
  await frequency_ordering_test(dut, SLOW_CLK, FAST_CLK)

@cocotb.test()
async def nearly_equal_ordering(dut):
  await frequency_ordering_test(dut, 20, 21)


# _____________Full protection test_____________
@cocotb.test()
async def wr_faster_full_protection(dut):
  await frequency_full_protection(dut, FAST_CLK, SLOW_CLK)

@cocotb.test()
async def rd_faster_full_protection(dut):
  await frequency_full_protection(dut, SLOW_CLK, FAST_CLK)

@cocotb.test()
async def nearly_equal_full_protection(dut):
  await frequency_full_protection(dut, 20, 21)

# _____________Long transfer and pointer-wraparound tests_____________
@cocotb.test()
async def wr_faster_empty_protection(dut):
  await frequency_empty_protection(dut, FAST_CLK, SLOW_CLK)

@cocotb.test()
async def rd_faster_empty_protection(dut):
  await frequency_empty_protection(dut, SLOW_CLK, FAST_CLK)

@cocotb.test()
async def nearly_equal_empty_protection(dut):
  await frequency_empty_protection(dut, 20, 21)

# _____________Random test with 1000 frames_____________
@cocotb.test()
async def frequency_test_wr_fast(dut):
    await run_frequency_test(dut, wr_clk=FAST_CLK, rd_clk=SLOW_CLK, nbr_of_frame=1000)

@cocotb.test()
async def frequency_test_nearly_equal(dut):
    await run_frequency_test(dut, wr_clk=20, rd_clk=21, nbr_of_frame=1000)

@cocotb.test()
async def frequency_test_rd_faster(dut):
    await run_frequency_test(dut, wr_clk=SLOW_CLK, rd_clk=FAST_CLK, nbr_of_frame=1000)

# _____________Random test_____________
random.seed(1)
delay = round(random.uniform(0, 10))
@cocotb.test()
async def rd_fast_random_test(dut):
  await frequency_random_test(dut, SLOW_CLK, FAST_CLK, delay)

@cocotb.test()
async def nearly_equal_random_test(dut):
  await frequency_random_test(dut, 20, 21, delay)

@cocotb.test()
async def wr_fast_random_test(dut):
  await frequency_random_test(dut, FAST_CLK, SLOW_CLK, delay)














  
  

      
    