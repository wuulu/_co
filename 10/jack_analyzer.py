#!/usr/bin/env python3
"""Jack 分析器：將 .jack 轉成 token XML 與語法樹 XML（nand2tetris Project 10）。"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

KEYWORDS = {
    "class",
    "constructor",
    "function",
    "method",
    "field",
    "static",
    "var",
    "int",
    "char",
    "boolean",
    "void",
    "true",
    "false",
    "null",
    "this",
    "let",
    "do",
    "if",
    "else",
    "while",
    "return",
}

SYMBOLS = set("{}()[].,;+-*/&|<>=~")

TYPES = {"int", "char", "boolean", "void"}

ESCAPES = {"<": "&lt;", ">": "&gt;", "&": "&amp;"}


class JackError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


def strip_comments(source: str) -> str:
    result: list[str] = []
    index = 0
    length = len(source)

    while index < length:
        char = source[index]
        if char == '"':
            result.append(char)
            index += 1
            while index < length and source[index] != '"':
                if source[index] == "\n":
                    raise JackError("字串常數不能跨行")
                result.append(source[index])
                index += 1
            if index >= length:
                raise JackError("字串常數缺少結尾引號")
            result.append(char)
            index += 1
            continue

        if char == "/" and index + 1 < length and source[index + 1] == "/":
            index += 2
            while index < length and source[index] != "\n":
                index += 1
            continue

        if char == "/" and index + 1 < length and source[index + 1] == "*":
            index += 2
            while index + 1 < length and not (
                source[index] == "*" and source[index + 1] == "/"
            ):
                index += 1
            if index + 1 >= length:
                raise JackError("區塊註解缺少結尾")
            index += 2
            result.append(" ")
            continue

        result.append(char)
        index += 1

    return "".join(result)


def tokenize(source: str) -> list[Token]:
    text = strip_comments(source)
    tokens: list[Token] = []
    index = 0
    length = len(text)

    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue

        if char == '"':
            end = text.find('"', index + 1)
            if end < 0:
                raise JackError("字串常數缺少結尾引號")
            tokens.append(Token("stringConstant", text[index + 1 : end]))
            index = end + 1
            continue

        if char in SYMBOLS:
            tokens.append(Token("symbol", char))
            index += 1
            continue

        if char.isdigit():
            end = index
            while end < length and text[end].isdigit():
                end += 1
            value = text[index:end]
            if int(value) > 32767:
                raise JackError(f"整數常數超出範圍：{value}")
            tokens.append(Token("integerConstant", value))
            index = end
            continue

        if char.isalpha() or char == "_":
            end = index
            while end < length and (text[end].isalnum() or text[end] == "_"):
                end += 1
            word = text[index:end]
            kind = "keyword" if word in KEYWORDS else "identifier"
            tokens.append(Token(kind, word))
            index = end
            continue

        raise JackError(f"無法辨識的字元：{char!r}")

    return tokens


def escape(value: str) -> str:
    return "".join(ESCAPES.get(char, char) for char in value)


def format_token(token: Token) -> str:
    return f"<{token.kind}> {escape(token.value)} </{token.kind}>"


class JackTokenizer:
    def __init__(self, source: str) -> None:
        self._tokens = tokenize(source)

    @property
    def tokens(self) -> list[Token]:
        return self._tokens


class TokenStream:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0

    def peek(self, offset: int = 0) -> Token | None:
        position = self._index + offset
        if position >= len(self._tokens):
            return None
        return self._tokens[position]

    def check(
        self,
        kind: str | tuple[str, ...],
        value: str | tuple[str, ...] | None = None,
    ) -> bool:
        token = self.peek()
        if token is None:
            return False
        kinds = (kind,) if isinstance(kind, str) else kind
        if token.kind not in kinds:
            return False
        if value is None:
            return True
        values = (value,) if isinstance(value, str) else value
        return token.value in values

    def take(
        self,
        kind: str | tuple[str, ...] | None = None,
        value: str | tuple[str, ...] | None = None,
    ) -> Token:
        token = self.peek()
        if token is None:
            raise JackError("已經沒有可用的 token")
        if kind is not None and not self.check(kind, value):
            expected = value if value is not None else kind
            raise JackError(f"預期 {expected}，實際為 {format_token(token)}")
        self._index += 1
        return token

    def at_end(self) -> bool:
        return self._index >= len(self._tokens)


class XmlWriter:
    def __init__(self) -> None:
        self._lines: list[str] = []
        self._indent = 0

    def start(self, tag: str) -> None:
        self._lines.append("  " * self._indent + f"<{tag}>")
        self._indent += 1

    def end(self, tag: str) -> None:
        self._indent -= 1
        self._lines.append("  " * self._indent + f"</{tag}>")

    def token(self, token: Token) -> None:
        self._lines.append("  " * self._indent + format_token(token))

    def text(self) -> str:
        return "\n".join(self._lines) + "\n"


class CompilationEngine:
    def __init__(self, tokens: list[Token]) -> None:
        self.stream = TokenStream(tokens)
        self.writer = XmlWriter()

    def compile(self) -> str:
        self.compile_class()
        if not self.stream.at_end():
            token = self.stream.peek()
            raise JackError(f"過多的 token：{format_token(token)}")
        return self.writer.text()

    def consume(
        self,
        kind: str | tuple[str, ...] | None = None,
        value: str | tuple[str, ...] | None = None,
    ) -> Token:
        token = self.stream.take(kind, value)
        self.writer.token(token)
        return token

    def consume_type(self) -> Token:
        token = self.stream.peek()
        if token is None:
            raise JackError("預期型別")
        if token.kind == "identifier" or (
            token.kind == "keyword" and token.value in TYPES
        ):
            return self.consume()
        raise JackError(f"預期型別，實際為 {format_token(token)}")

    def compile_class(self) -> None:
        self.writer.start("class")
        self.consume("keyword", "class")
        self.consume("identifier")
        self.consume("symbol", "{")
        while self.stream.check("keyword", ("static", "field")):
            self.compile_class_var_dec()
        while self.stream.check("keyword", ("constructor", "function", "method")):
            self.compile_subroutine()
        self.consume("symbol", "}")
        self.writer.end("class")

    def compile_class_var_dec(self) -> None:
        self.writer.start("classVarDec")
        self.consume("keyword", ("static", "field"))
        self.consume_type()
        self.consume("identifier")
        while self.stream.check("symbol", ","):
            self.consume("symbol", ",")
            self.consume("identifier")
        self.consume("symbol", ";")
        self.writer.end("classVarDec")

    def compile_subroutine(self) -> None:
        self.writer.start("subroutineDec")
        self.consume("keyword", ("constructor", "function", "method"))
        self.consume_type()
        self.consume("identifier")
        self.consume("symbol", "(")
        self.compile_parameter_list()
        self.consume("symbol", ")")
        self.compile_subroutine_body()
        self.writer.end("subroutineDec")

    def compile_parameter_list(self) -> None:
        self.writer.start("parameterList")
        if not self.stream.check("symbol", ")"):
            self.consume_type()
            self.consume("identifier")
            while self.stream.check("symbol", ","):
                self.consume("symbol", ",")
                self.consume_type()
                self.consume("identifier")
        self.writer.end("parameterList")

    def compile_subroutine_body(self) -> None:
        self.writer.start("subroutineBody")
        self.consume("symbol", "{")
        while self.stream.check("keyword", "var"):
            self.compile_var_dec()
        self.compile_statements()
        self.consume("symbol", "}")
        self.writer.end("subroutineBody")

    def compile_var_dec(self) -> None:
        self.writer.start("varDec")
        self.consume("keyword", "var")
        self.consume_type()
        self.consume("identifier")
        while self.stream.check("symbol", ","):
            self.consume("symbol", ",")
            self.consume("identifier")
        self.consume("symbol", ";")
        self.writer.end("varDec")

    def compile_statements(self) -> None:
        self.writer.start("statements")
        while self.stream.check("keyword", ("let", "if", "while", "do", "return")):
            self.compile_statement()
        self.writer.end("statements")

    def compile_statement(self) -> None:
        token = self.stream.peek()
        if token is None:
            raise JackError("預期敘述")
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
        self.writer.start("letStatement")
        self.consume("keyword", "let")
        self.consume("identifier")
        if self.stream.check("symbol", "["):
            self.consume("symbol", "[")
            self.compile_expression()
            self.consume("symbol", "]")
        self.consume("symbol", "=")
        self.compile_expression()
        self.consume("symbol", ";")
        self.writer.end("letStatement")

    def compile_if(self) -> None:
        self.writer.start("ifStatement")
        self.consume("keyword", "if")
        self.consume("symbol", "(")
        self.compile_expression()
        self.consume("symbol", ")")
        self.consume("symbol", "{")
        self.compile_statements()
        self.consume("symbol", "}")
        if self.stream.check("keyword", "else"):
            self.consume("keyword", "else")
            self.consume("symbol", "{")
            self.compile_statements()
            self.consume("symbol", "}")
        self.writer.end("ifStatement")

    def compile_while(self) -> None:
        self.writer.start("whileStatement")
        self.consume("keyword", "while")
        self.consume("symbol", "(")
        self.compile_expression()
        self.consume("symbol", ")")
        self.consume("symbol", "{")
        self.compile_statements()
        self.consume("symbol", "}")
        self.writer.end("whileStatement")

    def compile_do(self) -> None:
        self.writer.start("doStatement")
        self.consume("keyword", "do")
        self.compile_subroutine_call()
        self.consume("symbol", ";")
        self.writer.end("doStatement")

    def compile_return(self) -> None:
        self.writer.start("returnStatement")
        self.consume("keyword", "return")
        if not self.stream.check("symbol", ";"):
            self.compile_expression()
        self.consume("symbol", ";")
        self.writer.end("returnStatement")

    def compile_expression(self) -> None:
        self.writer.start("expression")
        self.compile_term()
        while self.stream.check("symbol", ("+", "-", "*", "/", "&", "|", "<", ">", "=")):
            self.consume("symbol")
            self.compile_term()
        self.writer.end("expression")

    def compile_term(self) -> None:
        self.writer.start("term")
        token = self.stream.peek()
        if token is None:
            raise JackError("預期 term")

        if token.kind in ("integerConstant", "stringConstant"):
            self.consume()
        elif token.kind == "keyword" and token.value in (
            "true",
            "false",
            "null",
            "this",
        ):
            self.consume()
        elif token.kind == "symbol" and token.value == "(":
            self.consume("symbol", "(")
            self.compile_expression()
            self.consume("symbol", ")")
        elif token.kind == "symbol" and token.value in ("-", "~"):
            self.consume("symbol")
            self.compile_term()
        elif token.kind == "identifier":
            self.consume("identifier")
            if self.stream.check("symbol", "["):
                self.consume("symbol", "[")
                self.compile_expression()
                self.consume("symbol", "]")
            elif self.stream.check("symbol", "("):
                self.consume("symbol", "(")
                self.compile_expression_list()
                self.consume("symbol", ")")
            elif self.stream.check("symbol", "."):
                self.consume("symbol", ".")
                self.consume("identifier")
                self.consume("symbol", "(")
                self.compile_expression_list()
                self.consume("symbol", ")")
        else:
            raise JackError(f"無法解析的 term：{format_token(token)}")
        self.writer.end("term")

    def compile_subroutine_call(self) -> None:
        self.consume("identifier")
        if self.stream.check("symbol", "."):
            self.consume("symbol", ".")
            self.consume("identifier")
        self.consume("symbol", "(")
        self.compile_expression_list()
        self.consume("symbol", ")")

    def compile_expression_list(self) -> None:
        self.writer.start("expressionList")
        if not self.stream.check("symbol", ")"):
            self.compile_expression()
            while self.stream.check("symbol", ","):
                self.consume("symbol", ",")
                self.compile_expression()
        self.writer.end("expressionList")


def collect_jack_files(args: list[str]) -> list[Path]:
    if not args:
        args = [str(Path(__file__).resolve().parent)]

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


def analyze_file(path: Path) -> tuple[Path, Path]:
    tokens = JackTokenizer(path.read_text(encoding="utf-8")).tokens
    token_path = path.with_name(f"{path.stem}T.xml")
    parse_path = path.with_name(f"{path.stem}.xml")
    token_path.write_text(tokens_xml(tokens), encoding="utf-8")
    parse_path.write_text(CompilationEngine(tokens).compile(), encoding="utf-8")
    return token_path, parse_path


def tokens_xml(tokens: list[Token]) -> str:
    lines = ["<tokens>"]
    lines.extend(format_token(token) for token in tokens)
    lines.append("</tokens>")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    try:
        paths = collect_jack_files(argv)
    except JackError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not paths:
        print("找不到任何 .jack 檔。", file=sys.stderr)
        return 1

    failed = 0
    for path in paths:
        try:
            token_path, parse_path = analyze_file(path)
            print(f"{path.name} -> {token_path.name}, {parse_path.name}")
        except (OSError, JackError) as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
