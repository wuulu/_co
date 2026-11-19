#!/usr/bin/env python3
"""VM 翻譯器：將 nand2tetris Project 8 的 .vm 轉譯成 Hack .asm。"""

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

FRAME_REGISTER = "R13"
RETURN_REGISTER = "R14"
ADDRESS_REGISTER = "R15"


class VMError(ValueError):
    pass


def strip_lines(source: str) -> list[str]:
    lines = []
    for raw in source.splitlines():
        line = raw.split("//", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def parse_command(line: str) -> tuple[str, list[str]]:
    parts = line.split()
    return parts[0], parts[1:]


def parse_index(text: str, line: str) -> int:
    try:
        index = int(text)
    except ValueError as exc:
        raise VMError(f"索引必須是整數：{line}") from exc
    if index < 0:
        raise VMError(f"索引不可為負：{line}")
    return index


class CodeWriter:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.current_function = filename
        self.label_count = 0
        self.call_count = 0
        self.lines: list[str] = []

    def emit(self, *lines: str) -> None:
        self.lines.extend(lines)

    def set_filename(self, filename: str) -> None:
        self.filename = filename

    def set_function_name(self, name: str) -> None:
        self.current_function = name

    def label_name(self, label: str) -> str:
        return f"{self.current_function}${label}"

    def next_label(self, kind: str) -> tuple[str, str]:
        self.label_count += 1
        return (
            f"{self.current_function}${kind}.{self.label_count}",
            f"{self.current_function}${kind}.END.{self.label_count}",
        )

    def next_return_label(self) -> str:
        self.call_count += 1
        return f"{self.current_function}$ret.{self.call_count}"

    def push_d(self) -> None:
        self.emit("@SP", "M=M+1", "A=M-1", "M=D")

    def pop_to_d(self) -> None:
        self.emit("@SP", "M=M-1", "A=M", "D=M")

    def resolve_address(self, segment: str, index: int) -> None:
        if segment in SEGMENT_BASE:
            self.emit(f"@{SEGMENT_BASE[segment]}", "D=M", f"@{index}", "A=D+A", "D=A")
        elif segment == "temp":
            self.emit("@5", "D=A", f"@{index}", "A=D+A", "D=A")
        else:
            raise VMError(f"無法取址的 memory segment：{segment}")

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
            self.emit(f"@{ADDRESS_REGISTER}", "M=D")
            self.pop_to_d()
            self.emit(f"@{ADDRESS_REGISTER}", "A=M", "M=D")
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

    def write_label(self, label: str) -> None:
        self.emit(f"({self.label_name(label)})")

    def write_goto(self, label: str) -> None:
        self.emit(f"@{self.label_name(label)}", "0;JMP")

    def write_if_goto(self, label: str) -> None:
        self.pop_to_d()
        self.emit(f"@{self.label_name(label)}", "D;JNE")

    def write_function(self, name: str, local_count: int) -> None:
        self.set_function_name(name)
        self.emit(f"({name})")
        for _ in range(local_count):
            self.emit("@SP", "A=M", "M=0", "@SP", "M=M+1")

    def write_call(self, name: str, arg_count: int) -> None:
        return_label = self.next_return_label()
        self.emit(f"@{return_label}", "D=A")
        self.push_d()
        for pointer in ("LCL", "ARG", "THIS", "THAT"):
            self.emit(f"@{pointer}", "D=M")
            self.push_d()
        self.emit(
            "@SP", "D=M", f"@{arg_count + 5}", "D=D-A",
            "@ARG", "M=D",
            "@SP", "D=M", "@LCL", "M=D",
            f"@{name}", "0;JMP",
            f"({return_label})",
        )

    def write_return(self) -> None:
        self.emit(
            "@LCL", "D=M", f"@{FRAME_REGISTER}", "M=D",
            f"@{FRAME_REGISTER}", "D=M", "@5", "A=D-A", "D=M",
            f"@{RETURN_REGISTER}", "M=D",
        )
        self.pop_to_d()
        self.emit(
            "@ARG", "A=M", "M=D", "D=A+1", "@SP", "M=D",
        )
        for offset, pointer in ((1, "THAT"), (2, "THIS"), (3, "ARG"), (4, "LCL")):
            self.emit(
                f"@{FRAME_REGISTER}", "D=M", f"@{offset}", "A=D-A", "D=M",
                f"@{pointer}", "M=D",
            )
        self.emit(f"@{RETURN_REGISTER}", "A=M", "0;JMP")

    def write_bootstrap(self) -> None:
        self.emit("@256", "D=A", "@SP", "M=D")
        for value, pointer in ((-1, "LCL"), (-2, "ARG"), (-3, "THIS"), (-4, "THAT")):
            self.emit(f"@{value}", "D=A", f"@{pointer}", "M=D")
        self.set_function_name("Sys.init")
        self.write_call("Sys.init", 0)

    def write_command(self, line: str, origin: str) -> None:
        command, args = parse_command(line)
        if command in BINARY_OPS or command in UNARY_OPS or command in COMPARE_JUMPS:
            if args:
                raise VMError(f"{command} 不接受運算元：{origin}")
            self.write_arithmetic(command)
        elif command == "return":
            if args:
                raise VMError(f"return 不接受運算元：{origin}")
            self.write_return()
        elif command in ("push", "pop"):
            if len(args) != 2:
                raise VMError(f"指令需要 segment 與索引：{origin}")
            index = parse_index(args[1], origin)
            if command == "push":
                self.write_push(args[0], index)
            else:
                self.write_pop(args[0], index)
        elif command in ("label", "goto", "if-goto"):
            if len(args) != 1:
                raise VMError(f"指令需要一個標籤：{origin}")
            if command == "label":
                self.write_label(args[0])
            elif command == "goto":
                self.write_goto(args[0])
            else:
                self.write_if_goto(args[0])
        elif command in ("function", "call"):
            if len(args) != 2:
                raise VMError(f"指令需要函式名稱與數量：{origin}")
            count = parse_index(args[1], origin)
            if command == "function":
                self.write_function(args[0], count)
            else:
                self.write_call(args[0], count)
        else:
            raise VMError(f"未知的指令：{line}")


def translate_sources(
    sources: list[tuple[str, str]], output_name: str, bootstrap: bool = False
) -> list[str]:
    writer = CodeWriter(output_name)
    if bootstrap:
        writer.write_bootstrap()
    for filename, source in sources:
        writer.set_filename(filename)
        writer.set_function_name(filename)
        for line in strip_lines(source):
            writer.write_command(line, f"{filename}: {line}")
    return writer.lines


def translate_group(vm_paths: list[Path], output_path: Path) -> Path:
    sources = [(path.stem, path.read_text(encoding="utf-8")) for path in vm_paths]
    bootstrap = any(path.stem == "Sys" for path in vm_paths)
    code = translate_sources(sources, output_path.stem, bootstrap)
    output_path.write_text("\n".join(code) + "\n", encoding="utf-8")
    return output_path


def collect_groups(args: list[str]) -> dict[Path, list[Path]]:
    if not args:
        args = [str(Path(__file__).resolve().parent)]

    groups: dict[Path, list[Path]] = {}
    for arg in args:
        path = Path(arg)
        if path.is_dir():
            vm_paths = sorted(path.rglob("*.vm"))
            for vm_path in vm_paths:
                parent = vm_path.parent
                output_path = parent / f"{parent.name}.asm"
                groups.setdefault(output_path, []).append(vm_path)
        elif path.suffix == ".vm":
            groups[path.with_suffix(".asm")] = [path]
        else:
            raise VMError(f"不是 .vm 檔或資料夾：{arg}")
    return groups


def main(argv: list[str]) -> int:
    try:
        groups = collect_groups(argv)
    except VMError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not groups:
        print("找不到任何 .vm 檔。", file=sys.stderr)
        return 1

    failed = 0
    for output_path, vm_paths in groups.items():
        try:
            asm_path = translate_group(vm_paths, output_path)
            count = len(asm_path.read_text(encoding="utf-8").splitlines())
            names = ", ".join(path.name for path in vm_paths)
            print(f"{names} -> {asm_path.name} ({count} 行)")
        except (OSError, VMError) as exc:
            print(f"{output_path}: {exc}", file=sys.stderr)
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
