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

export default function StatusBreakdown({ data }: { data: StatusStats[] }) {
  const filtered = data.filter((d) => d.count > 0);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-4">
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
          <Tooltip />
          <Legend
            formatter={(value) =>
              value.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c: string) => c.toUpperCase())
            }
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
