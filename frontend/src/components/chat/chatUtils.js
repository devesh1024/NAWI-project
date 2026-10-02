// Small presentation helpers shared by the TeamDesk pieces.

export const NOTIFICATION_PREVIEW_CHARS = 25;

/** First 25 characters of a message, with an ellipsis when it was cut. */
export function preview(text, max = NOTIFICATION_PREVIEW_CHARS) {
  const flat = (text || "").replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max).trimEnd()}…` : flat;
}

export function roleLabel(role) {
  if (!role) return "";
  const words = role.toLowerCase().replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function initials(name = "") {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// Theme-colored avatar fills; the same person always gets the same one.
const AVATAR_TONES = [
  "bg-primary text-primary-foreground",
  "bg-rail text-rail-foreground",
  "bg-accent text-accent-foreground",
  "bg-status-na text-white",
];

export function avatarTone(id = "") {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  return AVATAR_TONES[hash % AVATAR_TONES.length];
}

const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();

export function clock(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** Time for the conversation list: clock today, then Yesterday, weekday, date. */
export function listTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const days = Math.round((startOfDay(new Date()) - startOfDay(date)) / 86400000);
  if (days <= 0) return clock(iso);
  if (days === 1) return "Yesterday";
  if (days < 7) return date.toLocaleDateString([], { weekday: "long" });
  return date.toLocaleDateString([], { day: "2-digit", month: "short", year: "numeric" });
}

/** Label for the date dividers inside a chat. */
export function dayLabel(iso) {
  const date = new Date(iso);
  const days = Math.round((startOfDay(new Date()) - startOfDay(date)) / 86400000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  return date.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

export const dayKey = (iso) => new Date(iso).toDateString();
