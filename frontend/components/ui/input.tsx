"use client";
import { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export function Input(props: InputProps) {
  return <input className="w-full px-3 py-2 border border-gray-300 rounded" {...props} />;
}
