// components/charts/model-performance-chart.tsx
"use client";
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Legend } from 'recharts';

interface ModelData {
  model: string;
  accuracy: number;
  speed: number;
  cost: number;
  reliability: number;
}

interface RadarData {
  subject: string;
  GPT4: number;
  Claude: number;
  Gemini: number;
  Mistral: number;
}

interface ModelPerformanceChartProps {
  data?: ModelData[];
  className?: string;
}

export function ModelPerformanceChart({ 
  data = [
    { model: 'GPT-4', accuracy: 95, speed: 75, cost: 60, reliability: 92 },
    { model: 'Claude', accuracy: 92, speed: 85, cost: 75, reliability: 90 },
    { model: 'Gemini', accuracy: 88, speed: 90, cost: 85, reliability: 85 },
    { model: 'Mistral', accuracy: 85, speed: 95, cost: 95, reliability: 82 }
  ],
  className = "h-64"
}: ModelPerformanceChartProps) {
  
  const radarData: RadarData[] = [
    { subject: 'Accuracy', GPT4: 95, Claude: 92, Gemini: 88, Mistral: 85 },
    { subject: 'Speed', GPT4: 75, Claude: 85, Gemini: 90, Mistral: 95 },
    { subject: 'Cost Efficiency', GPT4: 60, Claude: 75, Gemini: 85, Mistral: 95 },
    { subject: 'Reliability', GPT4: 92, Claude: 90, Gemini: 85, Mistral: 82 }
  ];

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={radarData}>
          <PolarGrid stroke="rgba(255, 255, 255, 0.1)" />
          <PolarAngleAxis 
            dataKey="subject" 
            tick={{ fill: '#9ca3af', fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: '#9ca3af', fontSize: 10 }}
            tickCount={5}
          />
          <Radar
            name="GPT-4"
            dataKey="GPT4"
            stroke="#60a5fa"
            fill="#60a5fa"
            fillOpacity={0.1}
            strokeWidth={2}
          />
          <Radar
            name="Claude"
            dataKey="Claude"
            stroke="#34d399"
            fill="#34d399"
            fillOpacity={0.1}
            strokeWidth={2}
          />
          <Radar
            name="Gemini"
            dataKey="Gemini"
            stroke="#fbbf24"
            fill="#fbbf24"
            fillOpacity={0.1}
            strokeWidth={2}
          />
          <Radar
            name="Mistral"
            dataKey="Mistral"
            stroke="#f87171"
            fill="#f87171"
            fillOpacity={0.1}
            strokeWidth={2}
          />
          <Legend 
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="circle"
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}