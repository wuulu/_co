# 08 — VM 翻譯器（nand2tetris Project 8）

這個是實作一個 **VM Translator**，將 VM 虛擬機語言（`.vm`）轉譯成 Hack 組合語言（`.asm`）。

## 檔案結構

| 路徑 | 說明 |
| --- | --- |
| `vm_translator.py` | 本次實作的翻譯器（Python 3，無需額外套件）。 |
| `ProgramFlow/` | 程式流程測試：`.vm` → `.asm` 的分支與迴圈。 |
| `ProgramFlow/BasicLoop/` | 計算 `1 + 2 + ... + n`，示範 `label` / `if-goto` 迴圈。 |
| `ProgramFlow/FibonacciSeries/` | 將前 n 項費氏數列寫入記憶體，示範 `goto` 與 `pointer 1`。 |
| `FunctionCalls/` | 函式呼叫測試：堆疊框架、`call` / `return`、遞迴、static 變數。 |
| `FunctionCalls/SimpleFunction/` | 單一函式呼叫與回傳值。 |
| `FunctionCalls/NestedCall/` | 巢狀呼叫，另附 `NestedCall.html`、`NestedCallStack.html` 追蹤檔。 |
| `FunctionCalls/FibonacciElement/` | 遞迴計算 `fib(n)`，由 `Sys.init` 呼叫 `Main.fibonacci`。 |
| `FunctionCalls/StaticsTest/` | 測試跨檔案的 `static` 變數（`Class1.vm`、`Class2.vm`）。 |

每個測試資料夾中的檔案：

- `.vm`：官方提供的 VM 原始碼。
- `.asm`：本翻譯器（或參考實作）輸出的 Hack 組合語言。
- `.tst`：CPU Emulator 測試腳本；`*VME.tst` 則是 VM Emulator 用來直接跑 `.vm` 的腳本。
- `.cmp`：預期輸出；`.out`：實際執行後產生的輸出。

## 翻譯器功能

`vm_translator.py` 支援完整的 VM 指令集：

- **Push/Pop**：`constant`、`local`、`argument`、`this`、`that`、`temp`、`pointer`、`static`
  - `static` 會加上所屬檔案名前綴（例如 `@Class1.0`），避免不同 `.vm` 衝突。
- **算術/邏輯**：`add`、`sub`、`and`、`or`、`neg`、`not`
- **比較**：`eq`、`gt`、`lt`（產生唯一標籤的跳轉片段）
- **流程控制**：`label`、`goto`、`if-goto`（標籤自動加上函式名前綴）
- **函式呼叫**：`function`、`call`、`return`
  - 使用 `R13`（frame）、`R14`（return address）、`R15`（暫存位址）實作標準呼叫序列。
  - 若同一批檔案中含有 `Sys.vm`，會自動在開頭產生 bootstrap code（設定 `SP=256` 並呼叫 `Sys.init`）。
- 會過濾 `//` 註解與空白行，並對錯誤指令/索引提出 `VMError`。

## 使用方法

```powershell
# 翻譯目前目錄下所有 .vm（依所在資料夾分組輸出 .asm）
python vm_translator.py

# 翻譯單一檔案 -> 同名 .asm
python vm_translator.py ProgramFlow\BasicLoop\BasicLoop.vm

# 翻譯整個資料夾（含子資料夾）
python vm_translator.py FunctionCalls
```

規則：同一個資料夾內的所有 `.vm` 會合併輸出成 `資料夾名稱.asm`；單一 `.vm` 則輸出成同名 `.asm`。執行後會印出輸入檔名、輸出檔名與組合語言行數。

## 驗證

使用 nand2tetris 官方工具（CPU Emulator）載入各資料夾的 `.tst`，執行後會與 `.cmp` 比對並產生 `.out`；全部一致即代表翻譯正確。也可用 `*VME.tst` 在 VM Emulator 中直接觀察原始 `.vm` 的執行結果，作為對照。
