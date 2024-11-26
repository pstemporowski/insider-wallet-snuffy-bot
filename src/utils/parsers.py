def convert_profic_string_to_float(profit_str: str) -> float:
    """
    Convert a string representation of a profit to a float.
    """
    if "--" in profit_str:
        return None

    profit_str = profit_str.replace("$", "")
    profit_str = profit_str.replace(",", "")
    profit_str = profit_str.replace("(", "")
    profit_str = profit_str.replace(")", "")
    if "K" in profit_str:
        profit_str = profit_str.replace("K", "")
        try:
            return float(profit_str) * 1000
        except Exception:
            return None

    if "M" in profit_str:
        profit_str = profit_str.replace("M", "")
        try:
            return float(profit_str) * 1000000
        except Exception:
            return None

    try:
        return float(profit_str)
    except Exception:
        return None


def convert_percentage_to_float(percentage_str: str) -> float:
    """
    Convert a string representation of a percentage to a float.
    """
    if "--" in percentage_str:
        return None

    percentage_str = percentage_str.replace("%", "")
    percentage_str = percentage_str.replace(",", "")
    percentage_str = percentage_str.replace("(", "")
    percentage_str = percentage_str.replace(")", "")
    try:
        return round(float(percentage_str) / 100.0, 4)
    except Exception:
        return None
