import { useEffect, useState } from "react";
import { hapticImpact, hapticNotify } from "../utils/haptics";
import "./MessageActionSheet.css";

export default function MessageActionSheet({ target, onClose, onEdit, onRegenerate }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (target) hapticImpact("medium");
  }, [target]);

  if (!target) return null;
  const { message, isUser, canEdit, canRegenerate } = target;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      hapticNotify("success");
      setTimeout(() => {
        setCopied(false);
        onClose();
      }, 700);
    } catch {
      onClose();
    }
  };

  return (
    <div className="action-sheet-backdrop" onClick={onClose}>
      <div className="action-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="action-sheet__preview">{message.content}</div>
        <button className="action-sheet__item" onClick={handleCopy}>
          {copied ? "✓ Скопировано" : "⧉ Копировать"}
        </button>
        {isUser && canEdit && (
          <button
            className="action-sheet__item"
            onClick={() => {
              onClose();
              onEdit(message.content);
            }}
          >
            ✎ Редактировать
          </button>
        )}
        {!isUser && canRegenerate && (
          <button
            className="action-sheet__item"
            onClick={() => {
              onClose();
              onRegenerate();
            }}
          >
            ↻ Перегенерировать
          </button>
        )}
        <button className="action-sheet__item action-sheet__item--cancel" onClick={onClose}>
          Отмена
        </button>
      </div>
    </div>
  );
}
