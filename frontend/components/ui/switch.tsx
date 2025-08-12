"use client";
import { ChangeEvent } from "react";

interface SwitchProps {
  id?: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

export function Switch({ id, checked, onCheckedChange }: SwitchProps) {
  const toggle = (e: ChangeEvent<HTMLInputElement>) => {
    onCheckedChange(e.target.checked);
  };

  return (
    <input
      id={id}
      type="checkbox"
      checked={checked}
      onChange={toggle}
      className="h-5 w-10 rounded-full border appearance-none bg-gray-300 checked:bg-blue-500"
    />
  );
}
