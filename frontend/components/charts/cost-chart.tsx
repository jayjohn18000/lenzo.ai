// components/charts/cost-chart.tsx
"use client";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface CostData {
  name: string;
  cost: number;
  savings: number;
}

interface CostChartProps {
  data?: CostData[];
  className?: string;
}

interface CostTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
  }>;
  label?: string;
}

export function CostChart({ 
  data = [
    { name: 'Mon', cost: 45, savings: 12 },
    { name: 'Tue', cost: 52, savings: 15 },
    { name: 'Wed', cost: 38, savings: 18 },
    { name: 'Thu', cost: 41, savings: 11 },
    { name: 'Fri', cost: 35, savings: 22 },
    { name: 'Sat', cost: 28, savings: 8 },
    { name: 'Sun', cost: 32, savings: 14 }
  ],
  className = "h-48"
}: CostChartProps) {
  
  const CustomTooltip = ({ active, payload, label }: CostTooltipProps) => {
    if (active && payload && payload.length > 0) {
      return (
        <div className="bg-black/80 backdrop-blur-sm border border-white/20 rounded-lg p-3 shadow-xl">
          <p className="text-white text-sm font-medium">{label}</p>
          <p className="text-yellow-400 text-sm">
            Cost: ${payload[0].value}
          </p>
          {payload[1] && (
            <p className="text-green-400 text-sm">
              Saved: ${payload[1].value}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
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
          <Bar dataKey="cost" fill="#fbbf24" radius={[2, 2, 0, 0]} />
          <Bar dataKey="savings" fill="#34d399" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}