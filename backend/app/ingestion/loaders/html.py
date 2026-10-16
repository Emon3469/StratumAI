from bs4 import BeautifulSoup


def parse_html(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
        soup = BeautifulSoup(handle.read(), "html.parser")

    for tag in soup(["script", "style", "meta", "noscript", "nav", "footer", "header", "svg"]):
        tag.decompose()

    root = soup.find("main") or soup.find("article") or soup.body or soup
    blocks: list[str] = []
    for element in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre", "td", "th"]):
        if element.find_parent(["pre", "li", "td", "th"]) is not None and element.name != "pre":
            continue
        text = element.get_text("\n" if element.name == "pre" else " ", strip=True)
        if not text:
            continue
        if element.name in ("h1", "h2", "h3", "h4"):
            blocks.append(f"{'#' * int(element.name[1])} {text}")
        elif element.name == "pre":
            blocks.append(text)
        elif element.name == "li":
            blocks.append(f"- {text}")
        else:
            blocks.append(text)

    if not blocks:
        text = root.get_text("\n", strip=True)
        return "\n".join(line for line in text.splitlines() if line.strip())
    return "\n\n".join(blocks)
