import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ScreenHeader } from "../components/Common";
import { SkeletonCardGrid } from "../components/Skeleton";
import CharacterCard, { CreateCard, AICreateCard } from "../components/CharacterCard";
import "../components/CharacterCard.css";

export default function CharactersScreen() {
  const [characters, setCharacters] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.listCharacters().then(setCharacters);
  }, []);

  const startAICreation = async () => {
    const session = await api.startCreation({ kind: "character" });
    navigate(`/creation/${session.id}`);
  };

  return (
    <div className="screen">
      <ScreenHeader title="Персонажи" />
      <div className="scroll-fade-top" />
      {characters === null ? (
        <SkeletonCardGrid />
      ) : (
        <div className="card-grid">
          <CreateCard onClick={() => navigate("/characters/new")} label="Создать персонажа" />
          <AICreateCard onClick={startAICreation} />
          {characters.map((c) => (
            <CharacterCard key={c.id} character={c} />
          ))}
        </div>
      )}
    </div>
  );
}
