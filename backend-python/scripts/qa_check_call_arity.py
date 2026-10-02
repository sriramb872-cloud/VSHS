"""QA static check: verify `ClassName.method(...)` call sites bind correctly.

This exists because `AnnouncementService._trigger_notifications(updated)`
shipped with the `db` argument missing, raising a TypeError (HTTP 500) on both
`POST /announcements/{id}/publish` and `PUT /announcements/{id}`. Nothing else
in the toolchain type-checks Python, so the bug reached a running build.

Handles positional, keyword, *args and **kwargs binding. Reports only calls
that genuinely cannot bind: a required parameter left unsupplied, or more
positional arguments than the method accepts.

Read-only. Exits non-zero when it finds a mismatch.
"""
from __future__ import annotations

import ast
import os

UNBOUNDED = 10**9


class MethodInfo:
    __slots__ = ("params", "required", "has_vararg", "has_varkw")

    def __init__(self, params: list[str], required: list[str], has_vararg: bool, has_varkw: bool):
        self.params = params
        self.required = required
        self.has_vararg = has_vararg
        self.has_varkw = has_varkw


def _split_self(args: ast.arguments):
    """Return (positional params, self_or_cls_param) for a def."""
    names = [a.arg for a in args.posonlyargs + args.args]
    return names


def method_info(node) -> MethodInfo:
    a = node.args
    all_positional = [a.arg for a in a.posonlyargs + a.args]
    decorators = {
        d.id if isinstance(d, ast.Name) else getattr(d, "attr", "")
        for d in node.decorator_list
    }
    is_static = "staticmethod" in decorators

    if is_static and all_positional and all_positional[0] in ("self", "cls"):
        # A staticmethod that still names its first param `self` - drop it,
        # otherwise every call site looks one argument short.
        all_positional = all_positional[1:]

    positional = [p for p in all_positional if p not in ("self", "cls")]
    n_defaults = len(a.defaults)
    required = positional[: max(0, len(positional) - n_defaults)]
    return MethodInfo(
        params=positional,
        required=required,
        has_vararg=bool(a.vararg),
        has_varkw=bool(a.kwarg),
    )


class Collector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.methods: dict[tuple[str, str], MethodInfo] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.methods[(node.name, item.name)] = method_info(item)
        self.generic_visit(node)


def check_call(node: ast.Call, info: MethodInfo) -> str | None:
    supplied: set[str] = set()

    if node.args:
        if len(node.args) > len(info.params) and not info.has_vararg:
            return (
                f"expects at most {len(info.params)} positional arg(s), "
                f"got {len(node.args)}"
            )
        for name, arg in zip(info.params, node.args):
            supplied.add(name)

    star_args = sum(1 for arg in node.args if isinstance(arg, ast.Starred))
    if info.has_vararg and star_args:
        # *expr could cover anything; be permissive.
        return None

    for keyword in node.keywords:
        if keyword.arg is None:  # **kwargs
            return None
        if keyword.arg not in info.params and not info.has_varkw:
            return f"unknown keyword argument '{keyword.arg}'"
        supplied.add(keyword.arg)

    missing = [name for name in info.required if name not in supplied]
    if missing:
        return f"missing required argument(s): {', '.join(missing)}"
    return None


def main() -> int:
    signatures: dict[tuple[str, str], MethodInfo] = {}
    modules: list[tuple[str, ast.AST]] = []

    for root, dirs, files in os.walk("app"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
            modules.append((path, tree))
            collector = Collector()
            collector.visit(tree)
            signatures.update(collector.methods)

    problems: list[str] = []
    for path, tree in modules:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            owner = node.func.value
            if not isinstance(owner, ast.Name):
                continue
            info = signatures.get((owner.id, node.func.attr))
            if info is None:
                continue
            problem = check_call(node, info)
            if problem:
                problems.append(
                    f"{path}:{node.lineno}: {owner.id}.{node.func.attr}() {problem}"
                )

    for problem in problems:
        print(problem)
    print(
        f"checked {len(modules)} modules, {len(signatures)} class methods; "
        f"{len(problems)} mismatch(es)"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
