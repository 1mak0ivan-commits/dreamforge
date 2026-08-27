import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PrimaryButton, SecondaryButton } from "../components/Common";
import { SkeletonHero } from "../components/Skeleton";
import DreamAvatar from "../components/DreamAvatar";
import { formatRelativeTime } from "../utils/time";
import "./CharacterDetailScreen.css";

export default function CharacterDetailScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [character, setCharacter] = useState(null);
  const [world, setWorld] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    api.getCharacter(id).then(async (c) => {
      setCharacter(c);
      if (c.world_id) setWorld(await api.getWorld(c.world_id).catch(() => null));
    });
  }, [id]);

  if (!character) return <SkeletonHero />;

  const handleDelete = async () => {
    await api.deleteCharacter(id);
    navigate("/characters", { replace: true });
  };

  const totalMessages = character.chat_history?.length || 0;

  return (
    <div className="screen char-detail">
      <div className="char-detail__hero">
        <div className="hero-glow">
          <DreamAvatar
            src={character.avatar_path ? `/uploads/${character.avatar_path}` : null}
            name={character.name}
            size={128}
          />
        </div>
        <h1 className="font-display char-detail__name">{character.name}</h1>
        {character.personality && <div className="char-detail__personality">{character.personality}</div>}
        {world && (
          <button className="char-detail__world-chip" onClick={() => navigate(`/worlds/${world.id}`)}>
            ◈ {world.name}
          </button>
        )}
        <div className="stat-row" style={{ marginTop: 10 }}>
          {totalMessages > 0 && <span className="stat-row__item">💬 {totalMessages} сообщений</span>}
          {character.created_at && <span className="stat-row__item">✦ создан {formatRelativeTime(character.created_at)}</span>}
        </div>
      </div>

      <p className="char-detail__desc">{character.description || "Описание пока не написано."}</p>

      <div className="char-detail__actions">
        <PrimaryButton onClick={() => navigate(`/chat/${character.id}`)}>Заговорить</PrimaryButton>
        <SecondaryButton onClick={() => navigate(`/characters/${character.id}/edit`)}>Изменить</SecondaryButton>
        {!confirmDelete ? (
          <SecondaryButton danger onClick={() => setConfirmDelete(true)}>
            Удалить персонажа
          </SecondaryButton>
        ) : (
          <div className="char-detail__confirm">
            <p>Удалить {character.name} и всю историю чата с ним? Это необратимо.</p>
            <div className="char-detail__confirm-row">
              <SecondaryButton onClick={() => setConfirmDelete(false)}>Отмена</SecondaryButton>
              <SecondaryButton danger onClick={handleDelete}>
                Удалить
              </SecondaryButton>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
