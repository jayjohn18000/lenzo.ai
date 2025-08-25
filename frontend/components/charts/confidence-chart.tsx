// components/charts/confidence-chart.tsx
"use client";
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface ConfidenceChartProps {
  confidence: number;
  size?: number;
  className?: string;
}

interface ChartData {
  name: string;
  value: number;
}

export function ConfidenceChart({ 
  confidence, 
  size = 120, 
  className = "" 
}: ConfidenceChartProps) {
  const data: ChartData[] = [
    { name: 'Confidence', value: confidence },
    { name: 'Remaining', value: 100 - confidence }
  ];

  const getColor = (conf: number): string => {
    if (conf >= 90) return '#34d399';
    if (conf >= 70) return '#fbbf24';
    return '#ef4444';
  };

  const COLORS = [getColor(confidence), 'rgba(255, 255, 255, 0.1)'];

  return (
    <div className={`relative ${className}`} style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={size * 0.3}
            outerRadius={size * 0.4}
            startAngle={90}
            endAngle={450}
            paddingAngle={0}
            dataKey="value"
            stroke="none"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-2xl font-bold text-white">{confidence.toFixed(1)}%</div>
          <div className="text-xs text-gray-400">Confidence</div>
        </div>
      </div>
    </div>
  );
}