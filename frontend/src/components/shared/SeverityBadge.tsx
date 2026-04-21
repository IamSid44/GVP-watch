import { SEVERITY_COLORS, SEVERITY_LABELS } from "../../types";

export default function SeverityBadge({ severity }: { severity?: string | null }) {
  const s = severity?.toUpperCase() || "MEDIUM";
  const color = SEVERITY_COLORS[s] || "#9ca3af";
  const label = SEVERITY_LABELS[s] || s;

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium text-white"
      style={{ backgroundColor: color }}
    >
      {label}
    </span>
  );
}
