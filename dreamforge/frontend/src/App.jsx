import { Route, Routes, useLocation, useNavigate, useNavigationType } from "react-router-dom";
import { useEffect } from "react";
import BottomNav from "./components/BottomNav";
import ChatsScreen from "./screens/ChatsScreen";
import CharactersScreen from "./screens/CharactersScreen";
import CharacterDetailScreen from "./screens/CharacterDetailScreen";
import CharacterFormScreen from "./screens/CharacterFormScreen";
import WorldsScreen from "./screens/WorldsScreen";
import WorldDetailScreen from "./screens/WorldDetailScreen";
import WorldFormScreen from "./screens/WorldFormScreen";
import ProfileScreen from "./screens/ProfileScreen";
import ChatScreen from "./screens/ChatScreen";
import GroupChatFormScreen from "./screens/GroupChatFormScreen";
import GroupChatScreen from "./screens/GroupChatScreen";
import CreationChatScreen from "./screens/CreationChatScreen";
import NarrativeScreen from "./screens/NarrativeScreen";

const TOP_LEVEL_PATHS = ["/", "/characters", "/worlds", "/profile"];

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const navigationType = useNavigationType(); // PUSH | POP | REPLACE
  const isTopLevel = TOP_LEVEL_PATHS.includes(location.pathname);

  // Кнопка "назад" Telegram: показываем на вложенных экранах, прячем на вкладках.
  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg?.BackButton) return;
    if (isTopLevel) {
      tg.BackButton.hide();
    } else {
      tg.BackButton.show();
    }
    const handler = () => navigate(-1);
    tg.BackButton.onClick(handler);
    return () => tg.BackButton.offClick(handler);
  }, [isTopLevel, navigate]);

  // Направление перехода: вкладки переключаются мгновенно (как табы, не "экраны"),
  // переход вглубь (PUSH) заезжает справа, "назад" (POP) — слева. REPLACE без анимации,
  // чтобы не дёргалось при сохранении форм (navigate(..., {replace:true})).
  let transitionClass = "";
  if (!isTopLevel) {
    if (navigationType === "PUSH") transitionClass = "screen-transition--push";
    else if (navigationType === "POP") transitionClass = "screen-transition--pop";
  }

  return (
    <div className="app-shell">
      <div key={location.pathname} className={"screen-transition " + transitionClass}>
        <Routes location={location}>
          <Route path="/" element={<ChatsScreen />} />
          <Route path="/characters" element={<CharactersScreen />} />
          <Route path="/characters/new" element={<CharacterFormScreen />} />
          <Route path="/characters/:id" element={<CharacterDetailScreen />} />
          <Route path="/characters/:id/edit" element={<CharacterFormScreen />} />
          <Route path="/worlds" element={<WorldsScreen />} />
          <Route path="/worlds/new" element={<WorldFormScreen />} />
          <Route path="/worlds/:id" element={<WorldDetailScreen />} />
          <Route path="/worlds/:id/narrative" element={<NarrativeScreen />} />
          <Route path="/worlds/:id/edit" element={<WorldFormScreen />} />
          <Route path="/profile" element={<ProfileScreen />} />
          <Route path="/chat/:id" element={<ChatScreen />} />
          <Route path="/group/new" element={<GroupChatFormScreen />} />
          <Route path="/group/:id" element={<GroupChatScreen />} />
        <Route path="/creation/:id" element={<CreationChatScreen />} />
        </Routes>
      </div>
      {isTopLevel && <BottomNav />}
    </div>
  );
}
