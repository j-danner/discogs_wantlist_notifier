import functools
import re


@functools.total_ordering
class Price(object):
    currency: str = "€"
    value: float = 0.0

    def __init__(self, string):
        price_tuple = re.split(r"(\d+)", string.strip())
        self.currency = price_tuple[0]
        value_str = "".join(price_tuple[1:]).replace(",", "")
        assert value_str != ""
        self.value = float(value_str)

    def __add__(self, other):
        if type(self) != type(other):
            raise NotImplementedError
        if self.currency != other.currency:
            raise NotImplementedError
        return Price(self.currency + str(self.value + other.value))

    def __str__(self):
        return f"{self.currency}{self.value}"

    def __repr__(self):
        return f"{self.currency}{self.value}"

    def __eq__(self, other):
        if type(self) == type(other):
            return self.currency == other.currency and self.value == other.value
        else:
            return self.value == other

    def __gt__(self, other):
        if type(self) == type(other):
            if self.currency != other.currency:
                raise ValueError(
                    f"Cannot compare Prices with different currencies: {self.currency} vs {other.currency}"
                )
            else:
                return self.value > other.value
        else:
            return self.value > other


@functools.total_ordering
class Condition(object):
    cond: str = "P"

    _MAP_TO_INTERNAL: dict[str, str] = {
        "Mint (M)": "M",
        "M": "M",
        "Near Mint (NM)": "NM",
        "Near Mint (NM or M-)": "NM",
        "NM": "NM",
        "M-": "NM",
        "Very Good Plus (VG+)": "VG+",
        "VG+": "VG+",
        "Very Good (VG)": "VG",
        "VG": "VG",
        "Good Plus (G+)": "G+",
        "G+": "G+",
        "Good (G)": "G",
        "G": "G",
        "Fair (F)": "F",
        "F": "F",
        "Poor (P)": "P",
        "P": "P",
        "Not Graded": "not_graded",
        "Generic": "generic",
        "generic": "generic",
        "No Cover": "no_cover",
        "not provided": "no_cover",
        "": "no_cover",
        "unknown": "unknown",
    }

    _RANK: dict[str, int] = {
        "M": 0,
        "NM": 1,
        "VG+": 2,
        "VG": 3,
        "G+": 4,
        "G": 5,
        "F": 6,
        "P": 7,
        "not_graded": 8,
        "generic": 9,
        "no_cover": 10,
        "unknown": 11,
    }

    def __init__(self, string):
        if string not in self._MAP_TO_INTERNAL:
            raise ValueError(f"condition cannot be determined! (for input: {string})")
        self.cond = self._MAP_TO_INTERNAL[string]

    def __int__(self):
        return self._RANK[self.cond]

    def __str__(self):
        return self.cond

    def __repr__(self):
        return chr(60) + "Condition " + self.cond + chr(62)

    def __eq__(self, other):
        if type(self) != type(other):
            raise NotImplementedError
        else:
            return self.cond == other.cond

    def __gt__(self, other):
        return int(self) < int(other)


class Stats(object):
    def __init__(self, mn: Price, md: Price, mx: Price):
        self.mn = mn
        self.md = md
        self.mx = mx

    def __repr__(self):
        inner = "min=" + str(self.mn) + " med=" + str(self.md) + " max=" + str(self.mx)
        return chr(60) + "Stats " + inner + chr(62)

    def __str__(self):
        return self.__repr__()
