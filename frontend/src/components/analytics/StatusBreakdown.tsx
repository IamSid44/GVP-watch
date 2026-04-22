import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { StatusStats } from "../../types";
import { STATUS_COLORS } from "../../types";
import { useDarkMode } from "../../context/DarkModeContext";

export default function StatusBreakdown({ data }: { data: StatusStats[] }) {
  const filtered = data.filter((d) => d.count > 0);
  const { dark } = useDarkMode();

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-4">
        Status Breakdown
      </h3>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie
            data={filtered}
            dataKey="count"
            nameKey="status"
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={90}
            paddingAngle={2}
          >
            {filtered.map((entry) => (
              <Cell
                key={entry.status}
                fill={STATUS_COLORS[entry.status] || "#9ca3af"}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: dark ? "#111827" : "#ffffff",
              borderColor: dark ? "#374151" : "#e5e7eb",
              color: dark ? "#f3f4f6" : "#111827",
            }}
          />
          <Legend
            wrapperStyle={{ color: dark ? "#d1d5db" : "#4b5563" }}
            formatter={(value) =>
              value.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c: string) => c.toUpperCase())
            }
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
