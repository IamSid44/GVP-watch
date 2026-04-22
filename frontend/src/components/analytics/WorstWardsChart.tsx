import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { WardStats } from "../../types";
import { useDarkMode } from "../../context/DarkModeContext";

export default function WorstWardsChart({ data }: { data: WardStats[] }) {
  const top10 = data.slice(0, 10);
  const { dark } = useDarkMode();

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-4">
        Worst Wards (Most Open Reports)
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={top10} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke={dark ? "#374151" : "#e5e7eb"} />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: dark ? "#d1d5db" : "#4b5563" }}
            stroke={dark ? "#4b5563" : "#d1d5db"}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="ward_name"
            width={120}
            tick={{ fontSize: 11, fill: dark ? "#d1d5db" : "#4b5563" }}
            stroke={dark ? "#4b5563" : "#d1d5db"}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: dark ? "#111827" : "#ffffff",
              borderColor: dark ? "#374151" : "#e5e7eb",
              color: dark ? "#f3f4f6" : "#111827",
            }}
          />
          <Bar dataKey="open" name="Open" stackId="a" fill="#ef4444" radius={[0, 0, 0, 0]} />
          <Bar dataKey="resolved" name="Resolved" stackId="a" fill="#22c55e" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
