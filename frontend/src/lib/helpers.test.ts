import { describe, expect, it } from "vitest";
import { linkCitations } from "./citations";
import { formatSource, relativeGroup, titleFrom, uid } from "./utils";

describe("linkCitations", () => {
  it("links citations within the source range", () => {
    expect(linkCitations("See [1] and [2].", 2)).toBe("See [1](#cite-1) and [2](#cite-2).");
  });

  it("leaves out-of-range numbers, existing links and code untouched", () => {
    const input = "Use [3] or [link](http://x) [1](#a)\n```yaml\nports: [1]\n```\nand `arr[1]`";
    const out = linkCitations(input, 2);
    expect(out).toContain("[3]");
    expect(out).toContain("ports: [1]");
    expect(out).toContain("`arr[1]`");
    expect(out).not.toContain("[1](#cite-1)(#a)");
  });

  it("returns content unchanged when there are no sources", () => {
    expect(linkCitations("text [1]", 0)).toBe("text [1]");
  });

  it("handles an unterminated code fence while streaming", () => {
    expect(linkCitations("Answer [1]\n```bash\nkubectl get [1]", 1)).toBe("Answer [1](#cite-1)\n```bash\nkubectl get [1]");
  });
});

describe("utils", () => {
  it("creates short titles", () => {
    expect(titleFrom("  How   do I\nscale pods?  ")).toBe("How do I scale pods?");
    expect(titleFrom("x".repeat(80))).toHaveLength(49);
    expect(titleFrom("   ")).toBe("New chat");
  });

  it("formats source names", () => {
    expect(formatSource("monitor_job.docx")).toBe("monitor job");
    expect(formatSource("pods-autoscale.html")).toBe("pods autoscale");
  });

  it("groups timestamps", () => {
    const now = new Date("2026-10-16T12:00:00").getTime();
    expect(relativeGroup(now - 1000, now)).toBe("Today");
    expect(relativeGroup(now - 86_400_000, now)).toBe("Yesterday");
    expect(relativeGroup(now - 3 * 86_400_000, now)).toBe("Previous 7 days");
    expect(relativeGroup(now - 20 * 86_400_000, now)).toBe("Previous 30 days");
    expect(relativeGroup(now - 90 * 86_400_000, now)).toBe("Older");
  });

  it("generates unique ids", () => {
    expect(new Set(Array.from({ length: 100 }, uid)).size).toBe(100);
  });
});
