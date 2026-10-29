module synchronizer
#(
    parameter ADDR_WIDTH = 3,
    parameter PTR_WIDTH = ADDR_WIDTH +1
)
(
    input logic  clk,
    input logic  reset,
    input logic  [PTR_WIDTH-1:0] d_in,
    output logic  [PTR_WIDTH-1:0] q_2
);

logic  [PTR_WIDTH-1:0] q_1;

always_ff @(posedge(clk)) begin
    if (reset) begin
        q_1 <= 0;
        q_2 <= 0;
    end
    else begin 
      q_1 <= d_in;
      q_2 <= q_1;
    end
end
endmodule
