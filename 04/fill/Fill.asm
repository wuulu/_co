// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

(CHECK_KEYBOARD)
    // 讀取鍵盤輸入 (RAM[24576])
    @KBD
    D=M

    // 若有按鍵 pressed (D != 0)，跳轉至 SET_BLACK
    @SET_BLACK
    D;JNE

    // 若未按鍵 (D == 0)，設定填滿顏色為白色 (0)
    @color
    M=0
    @FILL_SCREEN
    0;JMP

(SET_BLACK)
    // 設定填滿顏色為黑色 (-1 / 0xFFFF)
    @color
    M=-1

(FILL_SCREEN)
    // 將當前指標 ptr 初始化為螢幕起始位址 SCREEN (16384)
    @SCREEN
    D=A
    @ptr
    M=D

(FILL_LOOP)
    // 檢查指標是否已超越螢幕記憶體範圍 (24576 = KBD 起始位址)
    @ptr
    D=M
    @KBD
    D=D-A
    @CHECK_KEYBOARD
    D;JEQ    // 當 ptr == KBD 時，代表全螢幕已刷完，重新檢查鍵盤

    // 將當前顏色填入當前像素記憶體區塊 (*ptr = color)
    @color
    D=M
    @ptr
    A=M
    M=D

    // 指標遞增 (ptr++)
    @ptr
    M=M+1

    // 繼續循環刷屏
    @FILL_LOOP
    0;JMP