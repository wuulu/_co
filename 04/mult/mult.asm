// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// 初始化 R2 = 0
@R2
M=0

// 檢查 R0 是否為 0，如果是 0 就直接跳到結束
@R0
D=M
@END
D;JEQ

// 檢查 R1 是否為 0，如果是 0 就直接跳到結束
@R1
D=M
@END
D;JEQ

// 將 R1 的值存入 count 變數
@count
M=D

(LOOP)
    // 將 R0 加到 R2
    @R0
    D=M
    @R2
    M=M+D

    // count 減 1
    @count
    M=M-1
    D=M

    // 如果 count > 0，繼續執行迴圈
    @LOOP
    D;JGT

(END)
    @END
    0;JMP