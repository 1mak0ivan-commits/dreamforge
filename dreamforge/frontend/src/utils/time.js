// Относительное время в духе мессенджеров: "только что", "5м назад", "вчера", дата для старого.

export function formatRelativeTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";

  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 30) return "только что";
  if (diffMin < 1) return `${diffSec}с назад`;
  if (diffMin < 60) return `${diffMin}м назад`;
  if (diffHour < 24) return `${diffHour}ч назад`;
  if (diffDay === 1) return "вчера";
  if (diffDay < 7) return `${diffDay}д назад`;

  const sameYear = date.getFullYear() === now.getFullYear();
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    year: sameYear ? undefined : "numeric",
  });
}

/** Короткое время для метки под сообщением в чате — просто часы:минуты. */
export function formatMessageTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}
