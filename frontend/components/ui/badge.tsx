// frontend/components/ui/badge.tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
  children?: React.ReactNode;
}

function Badge({ 
  className, 
  variant = "default", 
  children,
  ...props 
}: BadgeProps) {
  const variants: Record<BadgeVariant, string> = {
    default: "border-transparent bg-blue-600 text-white hover:bg-blue-700",
    secondary: "border-transparent bg-gray-100 text-gray-900 hover:bg-gray-200",
    destructive: "border-transparent bg-red-500 text-white hover:bg-red-600",
    outline: "text-gray-700 border-gray-300"
  };

  return (
    <div 
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variants[variant],
        className
      )} 
      {...props}
    >
      {children}
    </div>
  );
}

export { Badge };