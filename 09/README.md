# 09 — Jack 語言範例（nand2tetris Project 9）

這個章節沒有需要自己實作的程式，重點是閱讀並理解官方提供的 Jack 範例。

## 檔案結構

| 資料夾 | 說明 |
| --- | --- |
| `Average/` | 從鍵盤讀入整數陣列並計算平均。 |
| `ComplexArrays/` | 練習巢狀陣列存取。 |
| `ConvertToBin/` | 將 `RAM[8000]` 的 16 位元值拆成 0/1 寫入 `RAM[8001]..RAM[8016]`。 |
| `Fraction/` | 以物件導向方式製作分數型別，包含約分與加法。 |
| `HelloWorld/` | 最基本的 `Output.printString` 範例。 |
| `List/` | 以 `null` 與遞迴釋放實作的連結串列。 |
| `Pong/` | 完整的 Pong 遊戲，示範 static、field、method 之間的協作。 |
| `Square/` | 可用方向鍵移動、並用 z/x 改變大小的方塊遊戲。 |

## 使用方式

這些 `.jack` 檔可以直接交給第 10、11 章的工具處理：

```powershell
# 產生 token XML 與語法樹 XML
python 10\jack_analyzer.py 09

# 編譯成 VM
python 11\jack_compiler.py 09
```

也可在 nand2tetris 的 Jack Compiler / VM Emulator 中載入個別資料夾執行。
