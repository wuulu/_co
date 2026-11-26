# 11 — Jack 編譯器（nand2tetris Project 11）

這個資料夾實作完整的 **Jack Compiler**，把 `.jack` 轉成 nand2tetris 的 VM 語言（`.vm`）。

## 檔案結構

| 路徑 | 說明 |
| --- | --- |
| `jack_compiler.py` | 本次實作的編譯器（Python 3，無需額外套件）。 |
| `Average/` | 平均值程式。 |
| `ComplexArrays/` | 巢狀陣列讀寫測試。 |
| `ConvertToBin/` | 位元拆分測試。 |
| `Pong/` | Pong 遊戲，四個 class 會各自產生一個 `.vm`。 |
| `Seven/` | `1 + (2 * 3)`，檢查常數、乘法與呼叫。 |
| `Square/` | Square 遊戲，檢查方法呼叫與繪圖 OS 呼叫。 |

每個資料夾中的 `.jack` 會產生同名 `.vm`。

## 編譯器功能

- `SymbolTable`：管理 `static`、`field`、`arg`、`var` 四種變數。
- `VMWriter`：輸出 `push`、`pop`、`arithmetic`、`call`、`function`、`return` 等指令。
- 函式種類：
  - `constructor`：先 `Memory.alloc` 再設定 `THIS`。
  - `method`：把 `ARG 0` 載入 `THIS`，呼叫時自動傳入 `this`。
  - `function`：不傳入 `this`。
- 運算式：`+`、`-`、`*`、`/`、`&`、`|`、`<`、`>`、`=`、`-`、`~`。
  - `*` / `/` 分別轉成 `Math.multiply` / `Math.divide`。
  - `true` 轉成 `-1`，`false` / `null` 轉成 `0`。
- 字串常數：轉成 `String.new` 與一連串 `String.appendChar`。
- 陣列：`varName[expr]` 以 `pointer 1` / `that 0` 存取。
  - 陣列指定會先保留目標位址，再計算右值，避免右值中的陣列存取覆蓋 `THAT`。
- 流程控制：`if` / `else` / `while` 使用自動產生的唯一標籤。
- `do` 呼叫會丟棄回傳值；`return` 若無運算式會推入 `0`。

## 使用方法

```powershell
# 編譯目前資料夾 11 下所有 .jack
python jack_compiler.py

# 編譯單一檔案
python jack_compiler.py Seven\Main.jack

# 編譯其他資料夾，例如第 09 章的 Jack 範例
python jack_compiler.py ..\09
```

分析器共用第 10 章的 `jack_analyzer.py`，因此不需要重複安裝套件。

## 驗證

1. 所有 `.jack` 都能成功編譯成 `.vm`。
2. 所有 `call` 的參數數量都符合 Jack 宣告與 OS 例行程序的簽名。
3. 產生的 `.vm` 可以再通過第 08 章的 `vm_translator.py` 轉成 `.asm`，沒有語法錯誤。
4. 再用 nand2tetris 的 VM Emulator / CPU Emulator 載入各資料夾的 `.tst` 與 `.cmp` 比對執行結果。
