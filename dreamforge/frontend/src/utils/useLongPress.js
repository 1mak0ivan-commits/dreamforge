import { useRef } from "react";

const LONG_PRESS_MS = 450;
const MOVE_CANCEL_PX = 10;

/**
 * Возвращает обработчики для навешивания на элемент: если палец/курсор задержался
 * дольше LONG_PRESS_MS без существенного сдвига — вызывается onLongPress(event).
 * Обычный короткий тап при этом не блокируется — можно вешать поверх onClick.
 */
export function useLongPress(onLongPress) {
  const timerRef = useRef(null);
  const startPos = useRef({ x: 0, y: 0 });
  const firedRef = useRef(false);

  const clear = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
  };

  const onPointerDown = (e) => {
    firedRef.current = false;
    startPos.current = { x: e.clientX, y: e.clientY };
    clear();
    timerRef.current = setTimeout(() => {
      firedRef.current = true;
      onLongPress(e);
    }, LONG_PRESS_MS);
  };

  const onPointerMove = (e) => {
    const dx = Math.abs(e.clientX - startPos.current.x);
    const dy = Math.abs(e.clientY - startPos.current.y);
    if (dx > MOVE_CANCEL_PX || dy > MOVE_CANCEL_PX) clear();
  };

  const onPointerUp = () => clear();
  const onPointerLeave = () => clear();

  return { onPointerDown, onPointerMove, onPointerUp, onPointerLeave };
}
