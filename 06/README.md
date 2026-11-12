# nand2tetris Hack 組譯器（Python 轉譯 Hack 過程）

本資料夾是 nand2tetris Project 6 的實作：用 Python 撰寫一個 **Hack 組譯器（Assembler）**，把人類可讀的組合語言 `.asm` 檔轉譯成 CPU 可以直接執行的 16 位元機器碼 `.hack` 檔。

```
assembler.py      # 組譯器主程式
add/Add.asm       # 範例：R0 = 2 + 3
max/Max.asm       # 範例：R2 = max(R0, R1)
rect/Rect.asm     # 範例：在螢幕左上角畫矩形
pong/Pong.asm     # 範例：Pong 遊戲（由 Jack/VM 編譯器產生）
```

## 使用方式

需要 Python 3.7 以上。

```bash
# 1. 指定單一檔案
python assembler.py add/Add.asm

# 2. 指定資料夾（遞迴處理底下所有 .asm）
python assembler.py add

# 3. 不帶參數：處理 assembler.py 所在資料夾底下所有 .asm
python assembler.py
```

執行後會在 `.asm` 檔旁產生同名的 `.hack` 檔，例如 `add/Add.asm` → `add/Add.hack`。

## Hack 機器碼格式

Hack 指令固定 16 位元，只有兩種：

| 類型 | 格式 | 說明 |
|------|------|------|
| A-instruction | `0vvvvvvvvvvvvvvv` | 最高位元為 0，後 15 位元是位址或常數（0–32767） |
| C-instruction | `111accccccdddjjj` | 最高三位元為 111，後面依序是 comp、dest、jump |

### C-instruction 的三個欄位

```
 1 1 1 a c1 c2 c3 c4 c5 c6 d1 d2 d3 j1 j2 j3
└─────┘ └───────────┘ └─────┘ └─────┘
  111      comp(7)      dest(3)  jump(3)
```

組譯器使用三張查表（`COMP_TABLE`、`DEST_TABLE`、`JUMP_TABLE`）把文字轉成二進位。例如：

```asm
D=D-M
```

拆解後 `dest = "D"`、`comp = "D-M"`、`jump = ""`，查表得到：

```
dest = 010
comp = 1010011
jump = 000
=> 111 1010011 010 000 = 1111010011010000
```

## Python 轉譯 Hack 的完整流程

### 步驟 0：清除註解與空白

Hack 組譯器只在乎「指令」，因此先移除 `//` 之後的註解，並去掉前後空白、忽略空行。

```python
def strip_lines(source: str) -> list[str]:
    lines = []
    for raw in source.splitlines():
        line = raw.split("//", 1)[0].strip()
        if line:
            lines.append(line)
    return lines
```

### 步驟 1：第一遍掃描（建立符號表）

第一遍只做兩件事：

1. 遇到標籤 `(LOOP)`，把標籤名稱對應到「下一條指令的 ROM 位址」。
2. 遇到一般指令，ROM 位址加一。

注意：**標籤本身不佔用 ROM 位址**，它只是位址的別名。

```python
def build_symbol_table(lines):
    symbols = dict(PREDEFINED_SYMBOLS)
    rom_address = 0
    for line in lines:
        if is_label(line):
            symbols[line[1:-1].strip()] = rom_address
        else:
            rom_address += 1
    return symbols
```

#### 預先定義的符號

| 符號 | 位址 | 符號 | 位址 |
|------|------|------|------|
| `R0`–`R15` | 0–15 | `SCREEN` | 16384 |
| `SP` | 0 | `KBD` | 24576 |
| `LCL` | 1 | `THIS` | 3 |
| `ARG` | 2 | `THAT` | 4 |

#### 變數符號

程式中若出現未定義的符號（例如 `@n`、`@addr`），就視為**變數**，從 RAM 位址 16 開始依序配發：

```python
if operand not in symbols:
    symbols[operand] = next_var
    next_var += 1
```

### 步驟 2：第二遍掃描（產生機器碼）

第二遍逐行轉譯，跳過標籤定義：

- `@value` → A-instruction
  - 若 `value` 是數字，直接轉成 15 位元二進位。
  - 若是符號，查符號表；查不到就當成新變數配置位址。
- `dest=comp;jump` → C-instruction，用三張表組出 16 位元。

```python
for line in lines:
    if is_label(line):
        continue
    if line.startswith("@"):
        code, next_var = encode_a(line[1:].strip(), symbols, next_var)
        hack.append(code)
    else:
        hack.append(encode_c(line))
```

### 步驟 3：輸出 `.hack` 檔

每條指令一行，共 16 個 0/1 字元：

```python
hack_path.write_text("\n".join(code) + "\n", encoding="utf-8")
```

## 轉譯範例：Add.asm

原始組合語言：

```asm
@2
D=A
@3
D=D+A
@0
M=D
```

逐步轉譯：

| 指令 | 類型 | 轉譯結果 |
|------|------|----------|
| `@2` | A-instruction | `0000000000000010` |
| `D=A` | C-instruction | `1110110000010000` |
| `@3` | A-instruction | `0000000000000011` |
| `D=D+A` | C-instruction | `1110000010010000` |
| `@0` | A-instruction | `0000000000000000` |
| `M=D` | C-instruction | `1110001100001000` |

產生的 `Add.hack`：

```
0000000000000010
1110110000010000
0000000000000011
1110000010010000
0000000000000000
1110001100001000
```

## 標籤與變數範例：Max.asm

```asm
@R0
D=M
@R1
D=D-M
@ITSR0
D;JGT
...
(ITSR0)
@R0
D=M
(OUTPUT_D)
@R2
M=D
```

第一遍掃描時：

- `ITSR0` 對應到該標籤後面第一條指令的 ROM 位址。
- `OUTPUT_D` 同理。
- `R0`、`R1`、`R2` 使用預定義符號（0、1、2）。

第二遍掃描時，`@ITSR0` 就變成 `0` 加上 `ITSR0` 的 15 位元位址。

## 驗證

本組譯器產生的 `Add.hack`、`Max.hack`、`Rect.hack` 與 nand2tetris 官方解答的 `.hack` 完全一致；`Pong.asm` 也能成功轉譯出 27483 條指令。

## 錯誤處理

若遇到不合法指令，組譯器會指出是哪一行出錯，例如：

- `未知的 comp 組合：'D+X'`
- `未知的 dest：'Q'`
- `未知的 jump：'JXX'`
- `A 指令位址超出範圍：@40000`

如此一來，除錯時就能快速定位問題。
