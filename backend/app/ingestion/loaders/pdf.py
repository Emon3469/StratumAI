from pypdf import PdfReader


def parse_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages: dict[int, str] = {}
    blank: list[int] = []

    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages[index] = text
        else:
            blank.append(index)

    if blank:
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                for index in blank:
                    text = pdf.pages[index].extract_text() or ""
                    if text.strip():
                        pages[index] = text
        except Exception:
            pass

    return "\n\n".join(pages[i] for i in sorted(pages))
