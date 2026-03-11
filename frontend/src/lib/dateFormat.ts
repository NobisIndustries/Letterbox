const LS_KEY = "date_format";

export type DateFormat = "auto" | "de" | "iso" | "us";

export function getDateFormat(): DateFormat {
  return (localStorage.getItem(LS_KEY) as DateFormat) ?? "auto";
}

export function setDateFormat(fmt: DateFormat) {
  localStorage.setItem(LS_KEY, fmt);
}

/** Format a date string (YYYY-MM-DD or ISO datetime) for display. */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const fmt = getDateFormat();
  // Normalise to a local-midnight Date to avoid timezone shifts
  const iso = dateStr.includes("T") ? dateStr : dateStr + "T00:00:00";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return dateStr;
  switch (fmt) {
    case "de":
      return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
    case "iso":
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    case "us":
      return `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}/${d.getFullYear()}`;
    default:
      return d.toLocaleDateString();
  }
}
