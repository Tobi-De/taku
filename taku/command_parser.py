import argparse
import inspect
from dataclasses import asdict
from dataclasses import dataclass
from functools import wraps
from typing import Any
from typing import Callable
from typing import get_type_hints
from typing import Iterable

NOT_SET = ...


@dataclass(frozen=True)
class ArgSpec:
    action: str | type[argparse.Action] = NOT_SET  # type :ignore
    nargs: int | str | None = NOT_SET  # type: ignore
    help: str | None = NOT_SET  # type: ignore
    type: Any = NOT_SET  # type: ignore
    choices: Iterable | None = NOT_SET  # type: ignore
    required: bool | None = NOT_SET  # type: ignore
    metavar: str | tuple[str, ...] | None = NOT_SET  # type: ignore
    const: Any = NOT_SET
    dest: str | None = NOT_SET

    ignore: bool = False


def command(subparsers: argparse._SubParsersAction):
    """Decorator factory for creating subcommand parsers from type hints."""

    def register_command(command_name: str):
        def decorator(func: Callable):
            subparser: argparse.ArgumentParser = subparsers.add_parser(
                command_name, help=func.__doc__
            )

            hints = get_type_hints(func, include_extras=True)
            parameters = inspect.signature(func).parameters

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

                if arg_spec:
                    arg_kwargs |= {
                        k: v
                        for k, v in asdict(arg_spec).items()
                        if v is not NOT_SET and k != "ignore"
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
