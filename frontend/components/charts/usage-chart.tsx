// components/charts/usage-chart.tsx
"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DataPoint {
  name: string;
  requests: number;
  date?: string;
}

interface UsageChartProps {
  data?: DataPoint[];
  className?: string;
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
  }>;
  label?: string;
}

export function UsageChart({ 
  data = [
    { name: 'Mon', requests: 1200 },
    { name: 'Tue', requests: 1850 },
    { name: 'Wed', requests: 2100 },
    { name: 'Thu', requests: 1900 },
    { name: 'Fri', requests: 2400 },
    { name: 'Sat', requests: 2200 },
    { name: 'Sun', requests: 2847 }
  ],
  className = "h-48"
}: UsageChartProps) {
  
  const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
    if (active && payload && payload.length > 0) {
      return (
        <div className="bg-black/80 backdrop-blur-sm border border-white/20 rounded-lg p-3 shadow-xl">
          <p className="text-white text-sm font-medium">{label}</p>
          <p className="text-blue-400 text-sm">
            {`${payload[0].value.toLocaleString()} requests`}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
          <XAxis 
            dataKey="name" 
            stroke="#9ca3af"
            fontSize={12}
            tick={{ fill: '#9ca3af' }}
            axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
          />
          <YAxis hide />
          <Tooltip content={<CustomTooltip />} />
          <Line 
            type="monotone" 
            dataKey="requests" 
            stroke="#60a5fa"
            strokeWidth={2}
            dot={{ fill: '#60a5fa', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#ffffff', strokeWidth: 2, fill: '#3b82f6' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}