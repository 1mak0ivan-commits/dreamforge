import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ScreenHeader } from "../components/Common";
import { SkeletonChatList } from "../components/Skeleton";
import WorldCard from "../components/WorldCard";
import "./WorldsScreen.css";

export default function WorldsScreen() {
  const [worlds, setWorlds] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.listWorlds().then(setWorlds);
  }, []);

  const startAICreation = async () => {
    const session = await api.startCreation({ kind: "world" });
    navigate(`/creation/${session.id}`);
  };

  return (
    <div className="screen">
      <ScreenHeader title="Миры" />
      <div className="scroll-fade-top" />
      {worlds === null ? (
        <SkeletonChatList />
      ) : (
        <>
          <div className="world-create-row">
            <button className="world-create-btn world-create-btn--manual" onClick={() => navigate("/worlds/new")}>
              + Создать мир
            </button>
            <button className="world-create-btn world-create-btn--ai" onClick={startAICreation}>
              ✦ Придумать с ИИ
            </button>
          </div>
          {worlds.map((w) => (
            <WorldCard key={w.id} world={w} />
          ))}
        </>
      )}
    </div>
  );
}
