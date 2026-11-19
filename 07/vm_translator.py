#!/usr/bin/env python3
"""VM 翻譯器：將 nand2tetris Project 7 的 .vm 轉譯成 Hack .asm。"""

from __future__ import annotations

import sys
from pathlib import Path

SEGMENT_BASE = {
    "local": "LCL",
    "argument": "ARG",
    "this": "THIS",
    "that": "THAT",
}

BINARY_OPS = {
    "add": "D+M",
    "sub": "M-D",
    "and": "D&M",
    "or": "D|M",
}

UNARY_OPS = {
    "neg": "-M",
    "not": "!M",
}

COMPARE_JUMPS = {
    "eq": "D;JEQ",
    "gt": "D;JGT",
    "lt": "D;JLT",
}


class VMError(ValueError):
    pass


def strip_lines(source: str) -> list[str]:
    lines = []
    for raw in source.splitlines():
        line = raw.split("//", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def parse_command(line: str) -> tuple[str, str | None, int | None]:
    parts = line.split()
    if len(parts) == 1:
        return parts[0], None, None
    if len(parts) == 3:
        try:
            index = int(parts[2])
        except ValueError as exc:
            raise VMError(f"索引必須是整數：{line}") from exc
        if index < 0:
            raise VMError(f"索引不可為負：{line}")
        return parts[0], parts[1], index
    raise VMError(f"無法解析的 VM 指令：{line}")


class CodeWriter:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.label_count = 0
        self.lines: list[str] = []

    def emit(self, *lines: str) -> None:
        self.lines.extend(lines)

    def next_label(self, kind: str) -> tuple[str, str]:
        self.label_count += 1
        return f"{self.filename}.{kind}.{self.label_count}", f"{self.filename}.END.{self.label_count}"

    def push_d(self) -> None:
        self.emit("@SP", "M=M+1", "A=M-1", "M=D")

    def pop_to_d(self) -> None:
        self.emit("@SP", "M=M-1", "A=M", "D=M")

    def resolve_address(self, segment: str, index: int) -> None:
        if segment == "constant":
            self.emit(f"@{index}", "D=A")
        elif segment in SEGMENT_BASE:
            self.emit(f"@{SEGMENT_BASE[segment]}", "D=M", f"@{index}", "A=D+A", "D=A")
        elif segment == "temp":
            self.emit("@5", "D=A", f"@{index}", "A=D+A", "D=A")
        elif segment == "static":
            self.emit(f"@{self.filename}.{index}")
        else:
            raise VMError(f"未知的 memory segment：{segment}")

    def write_push(self, segment: str, index: int) -> None:
        if segment == "constant":
            self.emit(f"@{index}", "D=A")
        elif segment in SEGMENT_BASE:
            self.emit(f"@{SEGMENT_BASE[segment]}", "D=M", f"@{index}", "A=D+A", "D=M")
        elif segment == "temp":
            self.emit("@5", "D=A", f"@{index}", "A=D+A", "D=M")
        elif segment == "pointer":
            if index > 1:
                raise VMError(f"pointer 索引只能是 0 或 1：{segment} {index}")
            self.emit(f"@{'THIS' if index == 0 else 'THAT'}", "D=M")
        elif segment == "static":
            self.emit(f"@{self.filename}.{index}", "D=M")
        else:
            raise VMError(f"未知的 memory segment：{segment}")
        self.push_d()

    def write_pop(self, segment: str, index: int) -> None:
        if segment == "constant":
            raise VMError("constant 不能作為 pop 的目標")
        if segment in SEGMENT_BASE or segment == "temp":
            self.resolve_address(segment, index)
            self.emit("@R15", "M=D")
            self.pop_to_d()
            self.emit("@R15", "A=M", "M=D")
        elif segment == "pointer":
            if index > 1:
                raise VMError(f"pointer 索引只能是 0 或 1：{segment} {index}")
            self.pop_to_d()
            self.emit(f"@{'THIS' if index == 0 else 'THAT'}", "M=D")
        elif segment == "static":
            self.pop_to_d()
            self.emit(f"@{self.filename}.{index}", "M=D")
        else:
            raise VMError(f"未知的 memory segment：{segment}")

    def write_arithmetic(self, command: str) -> None:
        if command in BINARY_OPS:
            self.emit(
                "@SP", "A=M-1", "D=M", "A=A-1",
                f"M={BINARY_OPS[command]}", "@SP", "M=M-1",
            )
        elif command in UNARY_OPS:
            self.emit("@SP", "A=M-1", f"M={UNARY_OPS[command]}")
        elif command in COMPARE_JUMPS:
            true_label, end_label = self.next_label(command.upper())
            self.emit(
                "@SP", "A=M-1", "D=M", "A=A-1", "D=M-D",
                f"@{true_label}", COMPARE_JUMPS[command],
                "@SP", "A=M-1", "A=A-1", "M=0",
                f"@{end_label}", "0;JMP",
                f"({true_label})",
                "@SP", "A=M-1", "A=A-1", "M=-1",
                f"({end_label})",
                "@SP", "M=M-1",
            )
        else:
            raise VMError(f"未知的運算指令：{command}")

    def write_command(self, line: str) -> None:
        command, segment, index = parse_command(line)
        if segment is None:
            self.write_arithmetic(command)
        elif index is not None:
            if command == "push":
                self.write_push(segment, index)
            elif command == "pop":
                self.write_pop(segment, index)
            else:
                raise VMError(f"未知的指令：{line}")
        else:
            raise VMError(f"指令缺少索引：{line}")


def translate_source(source: str, filename: str) -> list[str]:
    writer = CodeWriter(filename)
    for line in strip_lines(source):
        writer.write_command(line)
    return writer.lines


def translate_file(vm_path: Path) -> Path:
    asm_path = vm_path.with_suffix(".asm")
    code = translate_source(vm_path.read_text(encoding="utf-8"), vm_path.stem)
    asm_path.write_text("\n".join(code) + "\n", encoding="utf-8")
    return asm_path


def collect_targets(args: list[str]) -> list[Path]:
    if not args:
        root = Path(__file__).resolve().parent
        return sorted(root.rglob("*.vm"))

    targets: list[Path] = []
    for arg in args:
        path = Path(arg)
        if path.is_dir():
            targets.extend(sorted(path.rglob("*.vm")))
        else:
            targets.append(path)
    return targets


def main(argv: list[str]) -> int:
    targets = collect_targets(argv)
    if not targets:
        print("找不到任何 .vm 檔。", file=sys.stderr)
        return 1

    failed = 0
    for vm_path in targets:
        try:
            asm_path = translate_file(vm_path)
            count = len(asm_path.read_text(encoding="utf-8").splitlines())
            print(f"{vm_path} -> {asm_path.name} ({count} 行)")
        except (OSError, VMError) as exc:
            print(f"{vm_path}: {exc}", file=sys.stderr)
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
