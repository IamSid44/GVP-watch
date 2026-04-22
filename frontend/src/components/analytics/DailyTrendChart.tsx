import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { DailyTrend } from "../../types";
import { useDarkMode } from "../../context/DarkModeContext";

export default function DailyTrendChart({ data }: { data: DailyTrend[] }) {
  const { dark } = useDarkMode();

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-4">
        Daily Reports (Last 30 Days)
      </h3>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={dark ? "#374151" : "#e5e7eb"} />
          <XAxis
            dataKey="date"
            tickFormatter={(d) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
            tick={{ fontSize: 11, fill: dark ? "#d1d5db" : "#4b5563" }}
            stroke={dark ? "#4b5563" : "#d1d5db"}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 11, fill: dark ? "#d1d5db" : "#4b5563" }}
            stroke={dark ? "#4b5563" : "#d1d5db"}
            allowDecimals={false}
          />
          <Tooltip
            labelFormatter={(d) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
            contentStyle={{
              backgroundColor: dark ? "#111827" : "#ffffff",
              borderColor: dark ? "#374151" : "#e5e7eb",
              color: dark ? "#f3f4f6" : "#111827",
            }}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#ef4444"
            fillOpacity={1}
            fill="url(#colorCount)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
