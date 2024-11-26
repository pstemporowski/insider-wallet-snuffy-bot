from enum import Enum


class Chain(Enum):
    ETH = "eth"
    SOL = "sol"
    BASE = "base"
    TRON = "tron"
    BLAST = "blast"

    @classmethod
    def from_name(cls, name: str):
        try:
            return cls(name.lower())
        except ValueError:
            return None
