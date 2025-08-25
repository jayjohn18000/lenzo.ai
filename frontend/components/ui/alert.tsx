// components/ui/alert.tsx
"use client";
import { ReactNode, HTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle, XCircle, Info } from "lucide-react";

interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: "default" | "destructive" | "success" | "warning";
}

export function Alert({ children, className, variant = "default", ...props }: AlertProps) {
  const variants = {
    default: "bg-blue-500/20 border-blue-500/30 text-blue-200",
    destructive: "bg-red-500/20 border-red-500/30 text-red-200",
    success: "bg-green-500/20 border-green-500/30 text-green-200",
    warning: "bg-yellow-500/20 border-yellow-500/30 text-yellow-200"
  };

  return (
    <div
      className={cn(
        "relative w-full rounded-lg border px-4 py-3 text-sm backdrop-blur-sm",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function AlertDescription({ children, className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <div
      className={cn("text-sm [&_p]:leading-relaxed", className)}
      {...props}
    >
      {children}
    </div>
  );
}