/**
 * Date helpers. The backend emits datetimes as UTC ISO strings without an
 * explicit timezone marker (e.g. "2024-01-15T10:30:00"), which JS would
 * otherwise interpret as local time. We treat them as UTC and render in IST.
 */

export function parseUTC(dateStr: string): Date {
  if (!/[Zz]|[+-]\d{2}:?\d{2}$/.test(dateStr)) {
    return new Date(dateStr + "Z");
  }
  return new Date(dateStr);
}

export function timeAgoIST(dateStr: string): string {
  const diff = Date.now() - parseUTC(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function daysSinceIST(dateStr: string): number {
  const diff = Date.now() - parseUTC(dateStr).getTime();
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
}

export function formatIST(dateStr: string): string {
  return parseUTC(dateStr).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }) + " IST";
}

export function formatDateIST(dateStr: string): string {
  return parseUTC(dateStr).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  });
}
