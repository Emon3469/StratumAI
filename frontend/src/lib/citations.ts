export function linkCitations(content: string, max: number): string {
  if (!max) return content;
  return content
    .split(/(```[\s\S]*?(?:```|$)|`[^`\n]*`)/g)
    .map((part, index) =>
      index % 2 === 1
        ? part
        : part.replace(/\[(\d{1,2})\](?![(:])/g, (match, n) =>
            Number(n) >= 1 && Number(n) <= max ? `[${n}](#cite-${n})` : match,
          ),
    )
    .join("");
}
