def get_gmgn_url(addr: str, chain_name: str = "sol") -> str:
    return f"https://gmgn.ai/{chain_name}/address/{addr}"


def get_dexscreener_url(
    chain_name: str,
    filter_args: str | None = None,
    page: int | None = None,
) -> str:
    page_str = ""
    postfix = ""

    if page and page > 1:
        page_str = f"/page-{page}"

    if filter_args:
        postfix = f"?{filter_args}"

    return f"https://dexscreener.com/{chain_name}{page_str}{postfix}"
