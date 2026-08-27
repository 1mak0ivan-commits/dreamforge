import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ScreenHeader, EmptyState, IconButton } from "../components/Common";
import { SkeletonChatList } from "../components/Skeleton";
import ChatListItem from "../components/ChatListItem";
import GroupChatListItem from "../components/GroupChatListItem";

export default function ChatsScreen() {
  const [state, setState] = useState({ loading: true, chats: [], groupChats: [] });
  const navigate = useNavigate();

  useEffect(() => {
    let alive = true;
    Promise.all([api.listCharacters(), api.listGroupChats()]).then(async ([characters, groupChats]) => {
      const withHistory = await Promise.all(
        characters.map(async (c) => {
          const history = await api.getChatHistory(c.id).catch(() => []);
          const real = history.filter((m) => !m.is_greeting);
          if (real.length === 0) return null;
          const last = real[real.length - 1];
          return { character: c, lastMessage: last?.content, lastMessageTime: last?.timestamp };
        })
      );
      if (!alive) return;
      setState({ loading: false, chats: withHistory.filter(Boolean), groupChats });
    });
    return () => {
      alive = false;
    };
  }, []);

  const handleCleared = async (charId) => {
    await api.clearChat(charId);
    setState((s) => ({ ...s, chats: s.chats.filter((c) => c.character.id !== charId) }));
  };

  const handleGroupDeleted = async (chatId) => {
    await api.deleteGroupChat(chatId);
    setState((s) => ({ ...s, groupChats: s.groupChats.filter((g) => g.id !== chatId) }));
  };

  const isEmpty = state.chats.length === 0 && state.groupChats.length === 0;

  return (
    <div className="screen">
      <ScreenHeader
        title="Чаты"
        action={
          <IconButton label="Новый групповой чат" onClick={() => navigate("/group/new")}>
            +
          </IconButton>
        }
      />
      <div className="scroll-fade-top" />
      {state.loading ? (
        <SkeletonChatList />
      ) : isEmpty ? (
        <EmptyState
          icon="☾"
          title="Пока тихо"
          description="Начни разговор с персонажем во вкладке «Персонажи» — или собери групповой чат кнопкой + сверху."
        />
      ) : (
        <div style={{ padding: "0 10px 90px" }}>
          {state.groupChats.map((g) => (
            <GroupChatListItem key={g.id} chat={g} onDeleted={handleGroupDeleted} />
          ))}
          {state.chats.map(({ character, lastMessage, lastMessageTime }) => (
            <ChatListItem
              key={character.id}
              character={character}
              lastMessage={lastMessage}
              lastMessageTime={lastMessageTime}
              onCleared={handleCleared}
            />
          ))}
        </div>
      )}
    </div>
  );
}
