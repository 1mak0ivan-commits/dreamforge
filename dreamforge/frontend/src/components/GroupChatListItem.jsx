import { useNavigate } from "react-router-dom";
import DreamAvatar from "./DreamAvatar";
import SwipeableRow from "./SwipeableRow";
import { formatRelativeTime } from "../utils/time";
import "./ChatListItem.css";
import "../screens/GroupChatScreen.css";

export default function GroupChatListItem({ chat, onDeleted }) {
  const navigate = useNavigate();
  const lastMessage = chat.chat_history?.[chat.chat_history.length - 1];
  return (
    <SwipeableRow actionLabel="Удалить" onAction={() => onDeleted?.(chat.id)}>
      <div className="chat-item" onClick={() => navigate(`/group/${chat.id}`)}>
        <div className="group-stack" style={{ width: 54 }}>
          {chat.characters.slice(0, 3).map((c) => (
            <DreamAvatar key={c.id} src={c.avatar_path ? `/uploads/${c.avatar_path}` : null} name={c.name} size={40} glow={false} />
          ))}
        </div>
        <div className="chat-item__body">
          <div className="chat-item__top-row">
            <div className="chat-item__name">{chat.name}</div>
            {lastMessage?.timestamp && <div className="chat-item__time">{formatRelativeTime(lastMessage.timestamp)}</div>}
          </div>
          <div className="chat-item__preview">{lastMessage ? lastMessage.content : `${chat.characters.length} участников`}</div>
        </div>
      </div>
    </SwipeableRow>
  );
}
