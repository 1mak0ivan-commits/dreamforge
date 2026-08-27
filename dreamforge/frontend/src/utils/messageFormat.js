// Разбирает текст ответа персонажа на сегменты по разметке из системного промпта:
// *звёздочки* — действие, "кавычки" (и «ёлочки»/“изогнутые”, на случай если модель
// использует другой вид кавычек) — мысль, всё остальное — обычная речь.
// Маркеры-символы в разбор не попадают — стиль (курсив/цвет) уже сам говорит,
// что это за сегмент, дублировать значками незачем.

const SEGMENT_REGEX = /\*([^*]+)\*|["«“]([^"»”]+)["»”]/g;

export function parseMessageSegments(text) {
  if (!text) return [];
  const segments = [];
  let lastIndex = 0;
  let match;
  SEGMENT_REGEX.lastIndex = 0;

  while ((match = SEGMENT_REGEX.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "speech", text: text.slice(lastIndex, match.index) });
    }
    if (match[1] !== undefined) {
      segments.push({ type: "action", text: match[1] });
    } else {
      segments.push({ type: "thought", text: match[2] });
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    segments.push({ type: "speech", text: text.slice(lastIndex) });
  }

  // Совсем пустые "речевые" огрызки (просто пробел между двумя маркерами) не несут смысла —
  // но не выкидываем их полностью, иначе потеряются переносы строк между сегментами.
  return segments;
}
