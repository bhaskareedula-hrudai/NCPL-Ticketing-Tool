import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export { STATUS_STYLES, PRIORITY_STYLES } from "./constants";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "2-digit", year: "numeric",
  });
}

export function formatDateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

export function timeAgo(iso) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)     return "just now";
  if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return formatDate(iso);
}

export function initials(name) {
  if (!name) return "?";
  return name.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase();
}

export function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
}
