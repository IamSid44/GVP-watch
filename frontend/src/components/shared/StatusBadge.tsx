import { STATUS_COLORS } from "../../types";

const LABELS: Record<string, string> = {
  INITIATED: "Initiated",
  AWAITING_PHOTO: "Awaiting Photo",
  OPEN: "Open",
  PENDING_VERIFICATION: "Pending",
  RESOLVED: "Resolved",
  UNRESPONSIVE: "Unresponsive",
};

export default function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || "#9ca3af";
  const label = LABELS[status] || status;

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium text-white"
      style={{ backgroundColor: color }}
    >
      {label}
    </span>
  );
}
