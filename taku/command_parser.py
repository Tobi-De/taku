import argparse
import inspect
from dataclasses import asdict
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any
from typing import Callable
from typing import get_args
from typing import get_type_hints
from typing import Iterable
from typing import Sequence

NOT_SET = ...


@dataclass(frozen=True)
class ArgSpec:
    action: str | type[argparse.Action] = NOT_SET  # type :ignore
    nargs: int | str | None = None
    help: str | None = NOT_SET  # type: ignore
    type: Any = NOT_SET  # type: ignore
    choices: Iterable | None = NOT_SET  # type: ignore
    required: bool | None = NOT_SET  # type: ignore
    metavar: str | tuple[str, ...] | None = NOT_SET  # type: ignore
    const: Any = NOT_SET
    dest: str | None = NOT_SET  # type: ignore

    ignore: bool = False


def command(subparsers: argparse._SubParsersAction):
    """Decorator factory for creating subcommand parsers from type hints."""

    def register_command(
        command_name: str,
        aliases: Sequence[str] | None = None,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    ):
        aliases = aliases or []

        def decorator(func: Callable):
            subparser: argparse.ArgumentParser = subparsers.add_parser(
                command_name,
                help=func.__doc__,
                aliases=aliases,  # type: ignore
                formatter_class=formatter_class,
            )

            hints = get_type_hints(func, include_extras=True)
            parameters = inspect.signature(func).parameters
            auto_types = [int, float, Path]

            for param_name, param in parameters.items():
                hint = hints.get(param_name)

                if not hint:
                    raise ValueError(
                        f"Parameter '{param_name}' in function '{func.__name__}' lacks a type hint."
                    )

                # Extract metadata from Annotated types
                metadata = getattr(hint, "__metadata__", ())
                arg_spec = next((m for m in metadata if isinstance(m, ArgSpec)), None)
                arg_names = [m for m in metadata if isinstance(m, str)] or [param_name]

                # Skip ignored parameters
                if arg_spec and arg_spec.ignore:
                    continue

                # Build argument kwargs
                arg_kwargs = {}
                if param.default is not param.empty:
                    arg_kwargs.setdefault("default", param.default)

                type_ = hint
                if arg_spec and arg_spec.type == NOT_SET:
                    type_ = get_args(hint)[0]
                if type_ in auto_types:
                    arg_kwargs["type"] = type_

                if arg_spec and arg_spec.nargs:
                    arg_kwargs["nargs"] = arg_spec.nargs

                if arg_spec:
                    arg_kwargs |= {
                        k: v
                        for k, v in asdict(arg_spec).items()
                        if v is not NOT_SET
                        and k not in ["default", "type", "ignore", "nargs"]
                    }

                subparser.add_argument(*arg_names, **arg_kwargs)

            params = list(parameters)

            @wraps(func)
            def command_wrapper(*args, **kwargs):
                # Filter kwargs to only include parameters the function expects
                return func(*args, **{k: v for k, v in kwargs.items() if k in params})

            subparser.set_defaults(func=command_wrapper)

            return command_wrapper

        return decorator

    return register_command
