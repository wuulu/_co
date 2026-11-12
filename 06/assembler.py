#!/usr/bin/env python3
"""Hack 組譯器：將 nand2tetris 的 .asm 檔轉譯成 .hack 機器碼。"""

from __future__ import annotations

import sys
from pathlib import Path

COMP_TABLE = {
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "M": "1110000",
    "!D": "0001101", "!A": "0110001", "!M": "1110001",
    "-D": "0001111", "-A": "0110011", "-M": "1110011",
    "D+1": "0011111", "A+1": "0110111", "M+1": "1110111",
    "D-1": "0001110", "A-1": "0110010", "M-1": "1110010",
    "D+A": "0000010", "D+M": "1000010",
    "D-A": "0010011", "D-M": "1010011",
    "A-D": "0000111", "M-D": "1000111",
    "D&A": "0000000", "D&M": "1000000",
    "D|A": "0010101", "D|M": "1010101",
}

DEST_TABLE = {
    "": "000", "M": "001", "D": "010", "MD": "011",
    "A": "100", "AM": "101", "AD": "110", "AMD": "111",
}

JUMP_TABLE = {
    "": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

PREDEFINED_SYMBOLS = {
    "SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
    "SCREEN": 16384, "KBD": 24576,
    **{f"R{i}": i for i in range(16)},
}


class AssemblyError(ValueError):
    pass


def strip_lines(source: str) -> list[str]:
    lines = []
    for raw in source.splitlines():
        line = raw.split("//", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def is_label(line: str) -> bool:
    return line.startswith("(") and line.endswith(")")


def build_symbol_table(lines: list[str]) -> dict[str, int]:
    symbols = dict(PREDEFINED_SYMBOLS)
    rom_address = 0
    for line in lines:
        if is_label(line):
            name = line[1:-1].strip()
            if not name:
                raise AssemblyError(f"空白標籤：{line}")
            symbols[name] = rom_address
        else:
            rom_address += 1
    return symbols


def encode_a(operand: str, symbols: dict[str, int], next_var: int) -> tuple[str, int]:
    if operand.isdigit():
        address = int(operand)
    else:
        if operand not in symbols:
            symbols[operand] = next_var
            next_var += 1
        address = symbols[operand]

    if not 0 <= address <= 0x7FFF:
        raise AssemblyError(f"A 指令位址超出範圍：@{operand}")
    return f"{address:016b}", next_var


def encode_c(line: str) -> str:
    body = line
    dest = ""
    jump = ""

    if "=" in body:
        dest, body = body.split("=", 1)
    if ";" in body:
        body, jump = body.split(";", 1)

    dest = dest.strip()
    comp = body.strip()
    jump = jump.strip()

    if comp not in COMP_TABLE:
        raise AssemblyError(f"未知的 comp 組合：{comp!r}（原始指令：{line}）")
    if dest not in DEST_TABLE:
        raise AssemblyError(f"未知的 dest：{dest!r}（原始指令：{line}）")
    if jump not in JUMP_TABLE:
        raise AssemblyError(f"未知的 jump：{jump!r}（原始指令：{line}）")

    return "111" + COMP_TABLE[comp] + DEST_TABLE[dest] + JUMP_TABLE[jump]


def assemble(source: str) -> list[str]:
    lines = strip_lines(source)
    symbols = build_symbol_table(lines)

    next_var = 16
    hack: list[str] = []

    for line in lines:
        if is_label(line):
            continue

        if line.startswith("@"):
            operand = line[1:].strip()
            if not operand:
                raise AssemblyError("A 指令缺少運算元：@")
            code, next_var = encode_a(operand, symbols, next_var)
            hack.append(code)
        else:
            hack.append(encode_c(line))

    return hack


def assemble_file(asm_path: Path) -> Path:
    hack_path = asm_path.with_suffix(".hack")
    code = assemble(asm_path.read_text(encoding="utf-8"))
    hack_path.write_text("\n".join(code) + "\n", encoding="utf-8")
    return hack_path


def collect_targets(args: list[str]) -> list[Path]:
    if not args:
        root = Path(__file__).resolve().parent
        return sorted(root.rglob("*.asm"))

    targets: list[Path] = []
    for arg in args:
        path = Path(arg)
        if path.is_dir():
            targets.extend(sorted(path.rglob("*.asm")))
        else:
            targets.append(path)
    return targets


def main(argv: list[str]) -> int:
    targets = collect_targets(argv)
    if not targets:
        print("找不到任何 .asm 檔。", file=sys.stderr)
        return 1

    failed = 0
    for asm_path in targets:
        try:
            hack_path = assemble_file(asm_path)
            count = len(hack_path.read_text(encoding="utf-8").splitlines())
            print(f"{asm_path} -> {hack_path.name} ({count} 行)")
        except (OSError, AssemblyError) as exc:
            print(f"{asm_path}: {exc}", file=sys.stderr)
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
