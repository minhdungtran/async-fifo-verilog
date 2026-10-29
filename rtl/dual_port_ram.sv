module dual_port_ram
#(
    parameter WIDTH = 64,
    parameter ADDR_WIDTH = 3,
    parameter PTR_WIDTH = ADDR_WIDTH+1
)
(
    input logic  wr_clk,
    input logic  rd_clk,
    input logic  wr_en,
    input logic  rd_en,
    input logic  full,
    input logic  empty,
    input logic  [PTR_WIDTH-1:0] cur_rd_bptr,
    input logic  [PTR_WIDTH-1:0] cur_wr_bptr,
    input logic  [WIDTH-1:0] d_in,

    output logic  [WIDTH-1:0] d_out
);
localparam DEPTH = 1 << ADDR_WIDTH;

logic  [WIDTH-1:0] ram [0:DEPTH-1];

always_ff @(posedge wr_clk) begin
    if (wr_en & !full) begin
        ram[cur_wr_bptr[ADDR_WIDTH-1:0]] <= d_in;
    end
end

always @(posedge rd_clk) begin
    if (rd_en & !empty) begin
        d_out <= ram[cur_rd_bptr[ADDR_WIDTH-1:0]];
    end
end

endmodule

