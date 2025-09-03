// components/ui/progress.tsx
"use client";
import { safeToFixed } from '@/lib/safe-formatters';
import React from "react";
import { cn } from "@/lib/utils";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
  showValue?: boolean;
  variant?: "default" | "gradient" | "glow";
}

export function Progress({ 
  value = 0, 
  max = 100, 
  className, 
  showValue = false,
  variant = "default",
  ...props
}: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const variants = {
    default: "bg-blue-500",
    gradient: "bg-gradient-to-r from-red-500 via-yellow-500 to-green-500",
    glow: "bg-blue-500 shadow-lg shadow-blue-500/30"
  };

  return (
    <div 
      className={cn("relative w-full overflow-hidden rounded-full bg-white/20 h-2", className)} 
      {...props}
    >
      <div
        className={cn(
          "h-full w-full flex-1 transition-all duration-500 ease-out",
          variants[variant]
        )}
        style={{ transform: `translateX(-${100 - percentage}%)` }}
      />
      {showValue && (
        <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white">
          {safeToFixed(percentage, 1)}%
        </div>
      )}
    </div>
  );
}