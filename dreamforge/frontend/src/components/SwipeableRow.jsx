import { useRef, useState } from "react";
import { hapticImpact, hapticSelect } from "../utils/haptics";
import "./SwipeableRow.css";

const ACTION_WIDTH = 88;
const OPEN_THRESHOLD = 40;

export default function SwipeableRow({ children, actionLabel, actionColor = "var(--danger)", onAction }) {
  const [dragX, setDragX] = useState(0);
  const [open, setOpen] = useState(false);
  const [settling, setSettling] = useState(false);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startDragX = useRef(0);
  const crossedThreshold = useRef(false);

  const onPointerDown = (e) => {
    dragging.current = true;
    setSettling(false);
    startX.current = e.clientX;
    startDragX.current = dragX;
    crossedThreshold.current = false;
  };

  const onPointerMove = (e) => {
    if (!dragging.current) return;
    const delta = e.clientX - startX.current;
    let next = startDragX.current + delta;
    next = Math.max(-ACTION_WIDTH, Math.min(0, next));
    if (next <= -OPEN_THRESHOLD && !crossedThreshold.current) {
      crossedThreshold.current = true;
      hapticSelect();
    } else if (next > -OPEN_THRESHOLD) {
      crossedThreshold.current = false;
    }
    setDragX(next);
  };

  const finishDrag = () => {
    if (!dragging.current) return;
    dragging.current = false;
    setSettling(true);
    if (dragX <= -OPEN_THRESHOLD) {
      setDragX(-ACTION_WIDTH);
      setOpen(true);
    } else {
      setDragX(0);
      setOpen(false);
    }
  };

  const handleContentClick = (e) => {
    if (open) {
      e.preventDefault();
      e.stopPropagation();
      setSettling(true);
      setDragX(0);
      setOpen(false);
    }
  };

  const handleAction = () => {
    hapticImpact("medium");
    setSettling(true);
    setDragX(0);
    setOpen(false);
    onAction();
  };

  return (
    <div className="swipe-row">
      <button className="swipe-row__action" style={{ background: actionColor }} onClick={handleAction}>
        {actionLabel}
      </button>
      <div
        className={"swipe-row__content" + (settling ? " swipe-row__content--settling" : "")}
        style={{ transform: `translateX(${dragX}px)` }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={finishDrag}
        onPointerLeave={finishDrag}
        onClickCapture={handleContentClick}
      >
        {children}
      </div>
    </div>
  );
}
