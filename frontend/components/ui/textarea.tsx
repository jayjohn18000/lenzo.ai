"use client";
import { TextareaHTMLAttributes } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {}

export function Textarea(props: TextareaProps) {
  return (
    <textarea
      className="w-full p-2 border border-gray-300 rounded"
      rows={4}
      {...props}
    />
  );
}
