import { type ClassValue } from "clsx";
import clsx from "clsx";
import { twMerge } from "tailwind-merge";
import type React from "react";

// Tailwind className merge
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Safely set a CSS custom property inline with TS support
export function cssVar(
  name: `--${string}`,
  value: string | number
): React.CSSProperties {
  return { [name]: value } as React.CSSProperties;
}

// Small helpers (optional)
export const px = (n: number) => `${n}px`;
export const pct = (n: number) => `${n}%`;
