# 10 — Jack 語法分析器（nand2tetris Project 10）

這個資料夾實作 Jack 的 **Tokenizer** 與 **Parser**，把 `.jack` 轉成官方格式的 XML。

## 檔案結構

| 路徑 | 說明 |
| --- | --- |
| `jack_analyzer.py` | 本次實作的語法分析器（Python 3，無需額外套件）。 |
| `ArrayTest/` | 簡單陣列與平均值程式。 |
| `ExpressionLessSquare/` | 不含複雜運算式的 Square 版本，方便檢查語法結構。 |
| `Square/` | 完整 Square 遊戲，包含巢狀運算式與 if/while。 |

每個測試資料夾中的檔案：

- `.jack`：官方提供的 Jack 原始碼。
- `*T.xml`：Tokenizer 輸出，每個 token 一行。
- `.xml`：Parser 輸出的語法樹。

## 分析器功能

- 移除 `//` 與 `/* ... */` 註解，保留字串常數內容。
- 辨識 keyword、identifier、integerConstant、stringConstant、symbol。
- 將 XML 特殊符號跳脫：`<` → `&lt;`、`>` → `&gt;`、`&` → `&amp;`。
- 完整解析 Jack 文法：`class`、`classVarDec`、`subroutineDec`、`parameterList`、
  `varDec`、`statements`、`letStatement`、`ifStatement`、`whileStatement`、
  `doStatement`、`returnStatement`、`expression`、`term`、`expressionList`。
- 遇到多餘或缺少的 token 會丟出 `JackError`。

## 使用方法

```powershell
# 分析目前資料夾 10 下所有 .jack
python jack_analyzer.py

# 分析單一檔案
python jack_analyzer.py ArrayTest\Main.jack

# 分析整個資料夾（含子資料夾）
python jack_analyzer.py ..\09
```

執行後會在每個 `.jack` 旁邊產生 `MainT.xml` 與 `Main.xml`。

## 驗證

本資料夾原有的 14 個 XML 檔已用此分析器重新產生，內容與官方期望輸出一致（只差
Windows 換行字元）。也可以用 nand2tetris 的 `JackAnalyzer` 對同一份 `.jack` 產生 XML
後互相比對。
