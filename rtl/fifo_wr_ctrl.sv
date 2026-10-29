module fifo_wr_ctrl
#(
    parameter ADDR_WIDTH = 3,
    parameter PTR_WIDTH = ADDR_WIDTH + 1
)
(
    input logic wr_en,
    input logic wr_reset,
    input logic wr_clk,
    input logic [PTR_WIDTH-1:0] sync_rd_gptr,

    output logic  full,
    output logic  [PTR_WIDTH-1:0] cur_wr_gptr,
    output logic  [PTR_WIDTH-1:0] cur_wr_bptr
);

logic [PTR_WIDTH-1:0] next_wr_gptr;
logic [PTR_WIDTH-1:0] next_wr_bptr;

logic next_full;
logic wr_valid;

assign wr_valid = (wr_en) & (~full);
assign next_wr_bptr = (cur_wr_bptr) + {{(PTR_WIDTH-1){1'b0}}, wr_valid};
assign next_wr_gptr = (next_wr_bptr >> 1) ^ next_wr_bptr;
assign next_full = (next_wr_gptr == {~sync_rd_gptr[PTR_WIDTH-1:PTR_WIDTH-2],sync_rd_gptr[PTR_WIDTH-3:0]});


always_ff @(posedge wr_clk) begin
    if (wr_reset) begin
        cur_wr_bptr <= 0;
        cur_wr_gptr <= 0;
        full <= 0;
    end

    else begin
        full <= next_full;
        cur_wr_bptr <= next_wr_bptr;
        cur_wr_gptr <= next_wr_gptr;    
    end  
end
endmodule

