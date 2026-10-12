from datetime import date


def get_today() -> date:
    # Als Dependency, damit Tests ein festes Datum einsetzen können.
    return date.today()
