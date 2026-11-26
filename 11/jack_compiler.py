#!/usr/bin/env python3
"""Jack 編譯器：將 .jack 轉成 VM 語言（nand2tetris Project 11）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "10"))

from jack_analyzer import JackError, JackTokenizer, TokenStream  # noqa: E402

SEGMENTS = {
    "field": "this",
    "static": "static",
    "arg": "argument",
    "var": "local",
}

BINARY_OPS = {
    "+": "add",
    "-": "sub",
    "&": "and",
    "|": "or",
    "<": "lt",
    ">": "gt",
    "=": "eq",
}

UNARY_OPS = {"-": "neg", "~": "not"}

CALL_OPS = {"*": "Math.multiply", "/": "Math.divide"}

TYPES = {"int", "char", "boolean", "void"}


class SymbolTable:
    def __init__(self) -> None:
        self._table: dict[str, tuple[str, str, int]] = {}
        self._counts = {"static": 0, "field": 0, "arg": 0, "var": 0}

    def reset(self) -> None:
        self._table = {
            name: entry
            for name, entry in self._table.items()
            if entry[1] in ("static", "field")
        }
        self._counts["arg"] = 0
        self._counts["var"] = 0

    def define(self, name: str, type_name: str, kind: str) -> None:
        self._table[name] = (type_name, kind, self._counts[kind])
        self._counts[kind] += 1

    def var_count(self, kind: str) -> int:
        return self._counts[kind]

    def kind_of(self, name: str) -> str | None:
        entry = self._table.get(name)
        return entry[1] if entry else None

    def type_of(self, name: str) -> str:
        entry = self._table.get(name)
        if entry is None:
            raise JackError(f"未宣告的變數：{name}")
        return entry[0]

    def index_of(self, name: str) -> int:
        entry = self._table.get(name)
        if entry is None:
            raise JackError(f"未宣告的變數：{name}")
        return entry[2]


class VMWriter:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write_push(self, segment: str, index: int) -> None:
        self.lines.append(f"push {segment} {index}")

    def write_pop(self, segment: str, index: int) -> None:
        self.lines.append(f"pop {segment} {index}")

    def write_arithmetic(self, command: str) -> None:
        self.lines.append(command)

    def write_call(self, name: str, arg_count: int) -> None:
        self.lines.append(f"call {name} {arg_count}")

    def write_label(self, label: str) -> None:
        self.lines.append(f"label {label}")

    def write_goto(self, label: str) -> None:
        self.lines.append(f"goto {label}")

    def write_if_goto(self, label: str) -> None:
        self.lines.append(f"if-goto {label}")

    def write_function(self, name: str, local_count: int) -> None:
        self.lines.append(f"function {name} {local_count}")

    def write_return(self) -> None:
        self.lines.append("return")

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def collect_subroutine_kinds(tokens: list) -> dict[str, str]:
    stream = TokenStream(tokens)
    stream.take("keyword", "class")
    stream.take("identifier")
    stream.take("symbol", "{")
    kinds: dict[str, str] = {}

    while stream.check("keyword", ("static", "field")):
        while not stream.check("symbol", ";"):
            stream.take()
        stream.take("symbol", ";")

    while stream.check("keyword", ("constructor", "function", "method")):
        kind = stream.take().value
        stream.take()
        name = stream.take("identifier").value
        kinds[name] = kind

        stream.take("symbol", "(")
        depth = 1
        while depth:
            token = stream.take()
            if token.kind == "symbol" and token.value == "(":
                depth += 1
            elif token.kind == "symbol" and token.value == ")":
                depth -= 1

        stream.take("symbol", "{")
        depth = 1
        while depth:
            token = stream.take()
            if token.kind == "symbol" and token.value == "{":
                depth += 1
            elif token.kind == "symbol" and token.value == "}":
                depth -= 1

    return kinds


class JackCompiler:
    def __init__(self, tokens: list) -> None:
        self.stream = TokenStream(tokens)
        self.symbols = SymbolTable()
        self.writer = VMWriter()
        self.subroutine_kinds = collect_subroutine_kinds(tokens)
        self.class_name = ""
        self.current_subroutine_kind = "function"
        self.label_count = 0

    def compile(self) -> str:
        self.compile_class()
        if not self.stream.at_end():
            token = self.stream.peek()
            raise JackError(f"過多的 token：{token.value}")
        return self.writer.text()

    def consume_type(self) -> str:
        token = self.stream.peek()
        if token is None:
            raise JackError("預期型別")
        if token.kind == "identifier" or (
            token.kind == "keyword" and token.value in TYPES
        ):
            return self.stream.take().value
        raise JackError(f"預期型別，實際為 {token.value!r}")

    def resolve(self, name: str) -> tuple[str, int]:
        kind = self.symbols.kind_of(name)
        if kind is None:
            raise JackError(f"未宣告的變數：{name}")
        return SEGMENTS[kind], self.symbols.index_of(name)

    def next_label(self, prefix: str) -> str:
        label = f"{prefix}.{self.label_count}"
        self.label_count += 1
        return label

    def compile_class(self) -> None:
        self.stream.take("keyword", "class")
        self.class_name = self.stream.take("identifier").value
        self.stream.take("symbol", "{")

        while self.stream.check("keyword", ("static", "field")):
            self.compile_class_var_dec()
        while self.stream.check("keyword", ("constructor", "function", "method")):
            self.compile_subroutine()

        self.stream.take("symbol", "}")

    def compile_class_var_dec(self) -> None:
        kind = self.stream.take().value
        type_name = self.consume_type()
        self.symbols.define(self.stream.take("identifier").value, type_name, kind)
        while self.stream.check("symbol", ","):
            self.stream.take("symbol", ",")
            self.symbols.define(self.stream.take("identifier").value, type_name, kind)
        self.stream.take("symbol", ";")

    def compile_subroutine(self) -> None:
        self.current_subroutine_kind = self.stream.take().value
        self.consume_type()
        name = self.stream.take("identifier").value
        self.stream.take("symbol", "(")

        self.symbols.reset()
        if self.current_subroutine_kind == "method":
            self.symbols.define("this", self.class_name, "arg")
        self.compile_parameter_list()
        self.stream.take("symbol", ")")
        self.stream.take("symbol", "{")

        while self.stream.check("keyword", "var"):
            self.compile_var_dec()

        self.writer.write_function(
            f"{self.class_name}.{name}", self.symbols.var_count("var")
        )
        if self.current_subroutine_kind == "constructor":
            self.writer.write_push("constant", self.symbols.var_count("field"))
            self.writer.write_call("Memory.alloc", 1)
            self.writer.write_pop("pointer", 0)
        elif self.current_subroutine_kind == "method":
            self.writer.write_push("argument", 0)
            self.writer.write_pop("pointer", 0)

        self.compile_statements()
        self.stream.take("symbol", "}")

    def compile_parameter_list(self) -> None:
        if self.stream.check("symbol", ")"):
            return
        type_name = self.consume_type()
        self.symbols.define(self.stream.take("identifier").value, type_name, "arg")
        while self.stream.check("symbol", ","):
            self.stream.take("symbol", ",")
            type_name = self.consume_type()
            self.symbols.define(self.stream.take("identifier").value, type_name, "arg")

    def compile_var_dec(self) -> None:
        self.stream.take("keyword", "var")
        type_name = self.consume_type()
        self.symbols.define(self.stream.take("identifier").value, type_name, "var")
        while self.stream.check("symbol", ","):
            self.stream.take("symbol", ",")
            self.symbols.define(self.stream.take("identifier").value, type_name, "var")
        self.stream.take("symbol", ";")

    def compile_statements(self) -> None:
        while self.stream.check("keyword", ("let", "if", "while", "do", "return")):
            token = self.stream.peek()
            if token is None:
                return
            if token.value == "let":
                self.compile_let()
            elif token.value == "if":
                self.compile_if()
            elif token.value == "while":
                self.compile_while()
            elif token.value == "do":
                self.compile_do()
            else:
                self.compile_return()

    def compile_let(self) -> None:
        self.stream.take("keyword", "let")
        name = self.stream.take("identifier").value
        is_array = self.stream.check("symbol", "[")

        if is_array:
            self.stream.take("symbol", "[")
            self.compile_expression()
            segment, index = self.resolve(name)
            self.writer.write_push(segment, index)
            self.writer.write_arithmetic("add")
            self.stream.take("symbol", "]")

        self.stream.take("symbol", "=")
        self.compile_expression()

        if is_array:
            self.writer.write_pop("temp", 0)
            self.writer.write_pop("pointer", 1)
            self.writer.write_push("temp", 0)
            self.writer.write_pop("that", 0)
        else:
            segment, index = self.resolve(name)
            self.writer.write_pop(segment, index)

        self.stream.take("symbol", ";")

    def compile_if(self) -> None:
        self.stream.take("keyword", "if")
        else_label = self.next_label("IF_ELSE")
        end_label = self.next_label("IF_END")
        self.stream.take("symbol", "(")
        self.compile_expression()
        self.stream.take("symbol", ")")
        self.writer.write_if_goto(else_label)
        self.stream.take("symbol", "{")
        self.compile_statements()
        self.stream.take("symbol", "}")
        self.writer.write_goto(end_label)
        self.writer.write_label(else_label)
        if self.stream.check("keyword", "else"):
            self.stream.take("keyword", "else")
            self.stream.take("symbol", "{")
            self.compile_statements()
            self.stream.take("symbol", "}")
        self.writer.write_label(end_label)

    def compile_while(self) -> None:
        self.stream.take("keyword", "while")
        start_label = self.next_label("WHILE")
        end_label = self.next_label("WHILE_END")
        self.writer.write_label(start_label)
        self.stream.take("symbol", "(")
        self.compile_expression()
        self.stream.take("symbol", ")")
        self.writer.write_arithmetic("not")
        self.writer.write_if_goto(end_label)
        self.stream.take("symbol", "{")
        self.compile_statements()
        self.stream.take("symbol", "}")
        self.writer.write_goto(start_label)
        self.writer.write_label(end_label)

    def compile_do(self) -> None:
        self.stream.take("keyword", "do")
        self.compile_subroutine_call()
        self.writer.write_pop("temp", 0)
        self.stream.take("symbol", ";")

    def compile_return(self) -> None:
        self.stream.take("keyword", "return")
        if self.stream.check("symbol", ";"):
            self.writer.write_push("constant", 0)
        else:
            self.compile_expression()
        self.writer.write_return()
        self.stream.take("symbol", ";")

    def compile_expression(self) -> None:
        self.compile_term()
        while self.stream.check("symbol", ("+", "-", "*", "/", "&", "|", "<", ">", "=")):
            operator = self.stream.take("symbol").value
            self.compile_term()
            if operator in CALL_OPS:
                self.writer.write_call(CALL_OPS[operator], 2)
            else:
                self.writer.write_arithmetic(BINARY_OPS[operator])

    def compile_term(self) -> None:
        token = self.stream.peek()
        if token is None:
            raise JackError("預期 term")

        if token.kind == "integerConstant":
            self.writer.write_push("constant", int(self.stream.take().value))
            return

        if token.kind == "stringConstant":
            value = self.stream.take().value
            self.writer.write_push("constant", len(value))
            self.writer.write_call("String.new", 1)
            for char in value:
                self.writer.write_push("constant", ord(char))
                self.writer.write_call("String.appendChar", 2)
            return

        if token.kind == "keyword":
            if token.value == "true":
                self.stream.take()
                self.writer.write_push("constant", 1)
                self.writer.write_arithmetic("neg")
            elif token.value in ("false", "null"):
                self.stream.take()
                self.writer.write_push("constant", 0)
            elif token.value == "this":
                if self.stream.peek(1) is not None and self.stream.peek(1).value == ".":
                    self.compile_subroutine_call()
                else:
                    self.stream.take()
                    self.writer.write_push("pointer", 0)
            else:
                raise JackError(f"無法解析的 term：{token.value}")
            return

        if token.kind == "symbol" and token.value == "(":
            self.stream.take("symbol", "(")
            self.compile_expression()
            self.stream.take("symbol", ")")
            return

        if token.kind == "symbol" and token.value in UNARY_OPS:
            operator = self.stream.take("symbol").value
            self.compile_term()
            self.writer.write_arithmetic(UNARY_OPS[operator])
            return

        if token.kind == "identifier":
            following = self.stream.peek(1)
            if following is not None and following.value == "[":
                name = self.stream.take("identifier").value
                self.stream.take("symbol", "[")
                segment, index = self.resolve(name)
                self.writer.write_push(segment, index)
                self.compile_expression()
                self.stream.take("symbol", "]")
                self.writer.write_arithmetic("add")
                self.writer.write_pop("pointer", 1)
                self.writer.write_push("that", 0)
            elif following is not None and following.value in ("(", "."):
                self.compile_subroutine_call()
            else:
                name = self.stream.take("identifier").value
                segment, index = self.resolve(name)
                self.writer.write_push(segment, index)
            return

        raise JackError(f"無法解析的 term：{token.value}")

    def compile_subroutine_call(self) -> None:
        token = self.stream.peek()
        if token is None:
            raise JackError("預期 subroutineCall")

        receiver: str | None = None
        receiver_type: str | None = None

        if token.kind == "identifier":
            name = self.stream.take("identifier").value
            if self.symbols.kind_of(name) is not None:
                receiver = name
                receiver_type = self.symbols.type_of(name)
        elif token.kind == "keyword" and token.value == "this":
            self.stream.take("keyword", "this")
            receiver = "this"
            receiver_type = self.class_name
        else:
            raise JackError(f"無法解析的 subroutineCall：{token.value}")

        if self.stream.check("symbol", "."):
            receiver_count = 0
            if receiver is None:
                receiver_type = name
            else:
                segment, index = self.resolve(receiver)
                self.writer.write_push(segment, index)
                receiver_count = 1

            self.stream.take("symbol", ".")
            subroutine_name = self.stream.take("identifier").value
            self.stream.take("symbol", "(")
            arg_count = self.compile_expression_list()
            self.stream.take("symbol", ")")
            self.writer.write_call(
                f"{receiver_type}.{subroutine_name}", arg_count + receiver_count
            )
            return

        subroutine_kind = self.subroutine_kinds.get(name)
        if subroutine_kind in ("method", "constructor"):
            self.writer.write_push("pointer", 0)
            arg_count = 1
        else:
            arg_count = 0

        self.stream.take("symbol", "(")
        arg_count += self.compile_expression_list()
        self.stream.take("symbol", ")")
        self.writer.write_call(f"{self.class_name}.{name}", arg_count)

    def compile_expression_list(self) -> int:
        if self.stream.check("symbol", ")"):
            return 0
        count = 1
        self.compile_expression()
        while self.stream.check("symbol", ","):
            self.stream.take("symbol", ",")
            self.compile_expression()
            count += 1
        return count


def compile_source(source: str) -> str:
    return JackCompiler(JackTokenizer(source).tokens).compile()


def collect_jack_files(args: list[str], default_dir: Path) -> list[Path]:
    if not args:
        args = [str(default_dir)]

    paths: list[Path] = []
    for arg in args:
        path = Path(arg)
        if path.is_dir():
            paths.extend(sorted(path.rglob("*.jack")))
        elif path.suffix == ".jack":
            paths.append(path)
        else:
            raise JackError(f"不是 .jack 檔或資料夾：{arg}")
    return paths


def compile_file(path: Path) -> Path:
    output_path = path.with_suffix(".vm")
    output_path.write_text(compile_source(path.read_text(encoding="utf-8")), encoding="utf-8")
    return output_path


def main(argv: list[str]) -> int:
    try:
        paths = collect_jack_files(argv, Path(__file__).resolve().parent)
    except JackError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not paths:
        print("找不到任何 .jack 檔。", file=sys.stderr)
        return 1

    failed = 0
    for path in paths:
        try:
            output_path = compile_file(path)
            count = len(output_path.read_text(encoding="utf-8").splitlines())
            print(f"{path.name} -> {output_path.name} ({count} 行)")
        except (OSError, JackError) as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
