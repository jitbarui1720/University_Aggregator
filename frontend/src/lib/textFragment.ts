/**
 * Build a URL with a :~:text= fragment so supporting browsers scroll to and highlight
 * the quoted passage (Chrome, Edge, Safari; Firefox as of recent versions).
 */
function excerptForFragment(quote: string): string {
  let s = quote.trim();
  if (!s || s === "Not Found") return "";
  s = s.replace(/\.\.\.$/, "").trimEnd();
  s = s.replace(/\s+/g, " ");
  const max = 120;
  if (s.length > max) {
    s = s.slice(0, max).trimEnd();
    const lastSpace = s.lastIndexOf(" ");
    if (lastSpace > 40) s = s.slice(0, lastSpace);
  }
  return s;
}

export function appendTextFragment(url: string, quote: string): string {
  const text = excerptForFragment(quote);
  if (!text) return url;
  try {
    const u = new URL(url);
    u.hash = `:~:text=${encodeURIComponent(text)}`;
    return u.toString();
  } catch {
    return url;
  }
}
