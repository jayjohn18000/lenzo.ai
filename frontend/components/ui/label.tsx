// frontend/components/ui/label.tsx
"use client";
import React from "react";

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

export function Label({ className = "", ...props }: LabelProps) {
  return <label className={`block text-sm font-medium text-gray-700 mb-1 ${className}`} {...props} />;
}