// components/charts/usage-chart.tsx
"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useTheme } from 'next-themes';
import { getThemeAwareColors } from '@/lib/chart-theme';

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
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const colors = getThemeAwareColors(isDark);
  
  const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
    if (active && payload && payload.length > 0) {
      return (
        <div 
          className="backdrop-blur-sm rounded-lg p-3 shadow-xl border"
          style={{
            backgroundColor: colors.tooltipBg,
            borderColor: colors.tooltipBorder,
            color: colors.tooltipText
          }}
        >
          <p className="text-sm font-medium">{label}</p>
          <p 
            className="text-sm"
            style={{ color: colors.tooltipAccent }}
          >
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
          <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} />
          <XAxis 
            dataKey="name" 
            stroke={colors.axis}
            fontSize={12}
            tick={{ fill: colors.axis }}
            axisLine={{ stroke: colors.axisLine }}
          />
          <YAxis hide />
          <Tooltip content={<CustomTooltip />} />
          <Line 
            type="monotone" 
            dataKey="requests" 
            stroke={colors.primary}
            strokeWidth={2}
            dot={{ fill: colors.primary, strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: colors.tooltipText, strokeWidth: 2, fill: colors.primaryHover }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}