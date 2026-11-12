import os

# Hack 語言查詢表 (C-instruction)
COMP_TABLE = {
    "0":   "0101010", "1":   "0111111", "-1":  "0111010",
    "D":   "0001100", "A":   "0110000", "M":   "1110000",
    "!D":  "0001101", "!A":  "0110001", "!M":  "1110001",
    "-D":  "0001111", "-A":  "0110011", "-M":  "1110011",
    "D+1": "0011111", "A+1": "0110111", "M+1": "1110111",
    "D-1": "0001110", "A-1": "0110010", "M-1": "1110010",
    "D+A": "0000010", "D+M": "1000010",
    "D-A": "0010011", "D-M": "1010011",
    "A-D": "0000111", "M-D": "1000111",
    "D&A": "0000000", "D&M": "1000000",
    "D|A": "0010101", "D|M": "1010101",
}

DEST_TABLE = {
    "":    "000", "M":   "001", "D":   "010", "MD":  "011",
    "A":   "100", "AM":  "101", "AD":  "110", "AMD": "111",
}

JUMP_TABLE = {
    "":    "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}


def assemble(asm_lines: list[str]) -> list[str]:
    hack_lines = []
    for line in asm_lines:
        # 1. 去除註解 (//) 與前後空白
        clean = line.split("//")[0].strip()
        if not clean:
            continue

        # 2. A-instruction: @value
        if clean.startswith("@"):
            value = int(clean[1:])
            binary = f"0{value:015b}"
            hack_lines.append(binary)

        # 3. C-instruction: dest=comp;jump
        else:
            dest, rest = ("", clean)
            if "=" in clean:
                dest, rest = clean.split("=", 1)

            comp, jump = (rest, "")
            if ";" in rest:
                comp, jump = rest.split(";", 1)

            binary = "111" + COMP_TABLE[comp] + DEST_TABLE[dest] + JUMP_TABLE[jump]
            hack_lines.append(binary)

    return hack_lines


if __name__ == "__main__":
    # 取得 Add1.py 所在的資料夾路徑 (即 add 資料夾)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    asm_path = os.path.join(base_dir, "Add.asm")
    hack_path = os.path.join(base_dir, "Add.hack")

    # 讀取同資料夾內的 Add.asm
    with open(asm_path, "r", encoding="utf-8") as f:
        hack_code = assemble(f.readlines())

    # 將結果寫出至同資料夾內的 Add.hack
    with open(hack_path, "w", encoding="utf-8") as f:
        f.write("\n".join(hack_code) + "\n")

    print("成功產生 Add.hack!")