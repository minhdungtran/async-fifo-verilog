module fifo_rd_ctrl
#(
    parameter ADDR_WIDTH = 3,
    parameter PTR_WIDTH = ADDR_WIDTH +1
)
(
    input logic rd_reset,
    input logic rd_clk,
    input logic rd_en,
    input logic [PTR_WIDTH-1:0] sync_wr_gptr,

    output logic empty,
    output logic [PTR_WIDTH-1:0] cur_rd_bptr,
    output logic [PTR_WIDTH-1:0] cur_rd_gptr
);

logic [PTR_WIDTH-1:0] next_rd_bptr;
logic [PTR_WIDTH-1:0] next_rd_gptr;

logic next_empty;
logic rd_valid;

assign rd_valid = (~empty) & (rd_en);
assign next_rd_bptr = cur_rd_bptr + {{(PTR_WIDTH-1){1'b0}},rd_valid};
assign next_rd_gptr = (next_rd_bptr>>1) ^ next_rd_bptr;
assign next_empty = (sync_wr_gptr == next_rd_gptr);

always_ff @(posedge rd_clk) begin
    if (rd_reset) begin
        cur_rd_bptr <= 0;
        cur_rd_gptr <= 0;
        empty <= 1;
    end
    else begin
        cur_rd_bptr <= next_rd_bptr;
        cur_rd_gptr <= next_rd_gptr;
        empty <= next_empty;
        
    end
end 
endmodule




