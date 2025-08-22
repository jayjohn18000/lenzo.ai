// frontend/components/ui/button.tsx
"use client";
import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg";
}

export function Button({ 
  children, 
  className = "", 
  variant = "default", 
  size = "md",
  ...props 
}: ButtonProps) {
  const variants = {
    default: "bg-blue-600 text-white hover:bg-blue-700",
    outline: "border border-gray-300 bg-transparent hover:bg-gray-50",
    ghost: "bg-transparent hover:bg-gray-100",
    destructive: "bg-red-600 text-white hover:bg-red-700"
  };

  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2",
    lg: "px-6 py-3 text-lg"
  };

  return (
    <button
      className={`inline-flex items-center justify-center rounded font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}