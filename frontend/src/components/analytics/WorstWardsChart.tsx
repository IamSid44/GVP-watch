import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { WardStats } from "../../types";

export default function WorstWardsChart({ data }: { data: WardStats[] }) {
  const top10 = data.slice(0, 10);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-4">
        Worst Wards (Most Open Reports)
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={top10} layout="vertical">
          <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="ward_name"
            width={120}
            tick={{ fontSize: 11 }}
          />
          <Tooltip />
          <Bar dataKey="open" name="Open" stackId="a" fill="#ef4444" radius={[0, 0, 0, 0]} />
          <Bar dataKey="resolved" name="Resolved" stackId="a" fill="#22c55e" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
