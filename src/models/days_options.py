from enum import Enum


class DaysOptions(Enum):
    """
    Enum for different days options.
    """

    MONTH = "30d"
    WEEK = "7d"

    @classmethod
    def from_name(cls, name: str, default=None):
        try:
            return cls(name.lower())
        except ValueError:
            return default
