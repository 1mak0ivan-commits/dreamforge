import { useNavigate } from "react-router-dom";
import DreamAvatar from "./DreamAvatar";
import SwipeableRow from "./SwipeableRow";
import { formatRelativeTime } from "../utils/time";
import "./ChatListItem.css";

export default function ChatListItem({ character, lastMessage, lastMessageTime, onCleared }) {
  const navigate = useNavigate();
  if (!character) return null;
  return (
    <SwipeableRow actionLabel="Очистить" onAction={() => onCleared?.(character.id)}>
      <div className="chat-item" onClick={() => navigate(`/chat/${character.id}`)}>
        <DreamAvatar src={character.avatar_path ? `/uploads/${character.avatar_path}` : null} name={character.name} size={54} />
        <div className="chat-item__body">
          <div className="chat-item__top-row">
            <div className="chat-item__name">{character.name}</div>
            {lastMessageTime && <div className="chat-item__time">{formatRelativeTime(lastMessageTime)}</div>}
          </div>
          <div className="chat-item__preview">{lastMessage || "Нет сообщений"}</div>
        </div>
      </div>
    </SwipeableRow>
  );
}
