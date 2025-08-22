// frontend/components/ui/progress.tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value = 0, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "relative h-4 w-full overflow-hidden rounded-full bg-gray-100",
          className
        )}
        {...props}
      >
        <div
          className="h-full w-full flex-1 bg-blue-600 transition-all"
          style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
        />
      </div>
    );
  }
);
Progress.displayName = "Progress";

export { Progress };