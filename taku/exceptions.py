class TakuError(Exception):
    pass


class ScriptNotFoundError(TakuError):
    pass


class ScriptAlreadyExistsError(TakuError):
    pass


class TemplateNotFoundError(TakuError):
    pass
