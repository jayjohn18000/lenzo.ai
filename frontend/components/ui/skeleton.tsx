// components/ui/skeleton.tsx
"use client";
import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-white/10 backdrop-blur-sm",
        className
      )}
    />
  );
}