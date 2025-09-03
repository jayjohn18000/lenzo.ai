// components/ui/model-visualization.tsx
"use client";
import { cn } from '@/lib/utils';
import { safeToFixed } from '@/lib/safe-formatters';

interface ModelVisualizationProps {
  models: string[];
  activeModels: string[];
  className?: string;
}

export function ModelVisualization({ 
  models, 
  activeModels, 
  className 
}: ModelVisualizationProps) {
  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-4 gap-4 p-6 bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl", className)}>
      {models.map((model) => {
        const isActive = activeModels.includes(model);
        const raw = Math.random() * 15 + 85;
        const score = isActive ? safeToFixed(raw, 1) : '--';
        
        return (
          <div
            key={model}
            className={cn(
              "flex flex-col items-center p-4 rounded-xl transition-all duration-500",
              isActive 
                ? "bg-gradient-to-br from-blue-500 to-blue-600 text-white scale-105 shadow-lg shadow-blue-500/30" 
                : "bg-white/10 text-gray-400"
            )}
          >
            <div className="text-xs font-bold mb-2 tracking-wide">{model}</div>
            <div className="text-lg font-bold">{score}</div>
            {isActive && (
              <div className="w-2 h-2 bg-green-400 rounded-full mt-2 animate-pulse" />
            )}
          </div>
        );
      })}
    </div>
  );
}