import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PrimaryButton, SecondaryButton, EmptyState } from "../components/Common";
import { SkeletonHero } from "../components/Skeleton";
import DreamAvatar from "../components/DreamAvatar";
import { formatRelativeTime } from "../utils/time";
import "./WorldDetailScreen.css";

export default function WorldDetailScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [world, setWorld] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const load = () => api.getWorld(id).then(setWorld);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!world) return <SkeletonHero />;

  const handleDelete = async () => {
    await api.deleteWorld(id);
    navigate("/worlds", { replace: true });
  };

  const handleRemoveChar = async (charId) => {
    await api.removeCharacterFromWorld(charId);
    load();
  };

  const startAICreation = async () => {
    const session = await api.startCreation({ kind: "character", world_id: world.id });
    navigate(`/creation/${session.id}?world_id=${world.id}`);
  };

  return (
    <div className="screen world-detail">
      <div className="world-detail__banner">
        {world.image_path ? (
          <img src={`/uploads/${world.image_path}`} alt={world.name} />
        ) : (
          <div className="world-detail__banner-placeholder">◈</div>
        )}
        <div className="world-detail__banner-scrim" />
        <h1 className="font-display world-detail__name">{world.name}</h1>
      </div>

      <div className="stat-row" style={{ margin: "14px 0 4px" }}>
        <span className="stat-row__item">◈ {world.characters?.length || 0} персонажей</span>
        {world.created_at && <span className="stat-row__item">✦ создан {formatRelativeTime(world.created_at)}</span>}
      </div>

      <div className="world-detail__enter-row">
        <PrimaryButton onClick={() => navigate(`/worlds/${world.id}/narrative`)}>▶ Войти в мир</PrimaryButton>
      </div>

      <p className="world-detail__desc">{world.description || "Нет описания"}</p>

      <div className="world-detail__section-title">Персонажи мира</div>
      {world.characters?.length ? (
        <div className="world-detail__chars">
          {world.characters.map((c) => (
            <div key={c.id} className="world-detail__char-row">
              <div className="world-detail__char-info" onClick={() => navigate(`/characters/${c.id}`)}>
                <DreamAvatar src={c.avatar_path ? `/uploads/${c.avatar_path}` : null} name={c.name} size={42} glow={false} />
                <span>{c.name}</span>
              </div>
              <button className="world-detail__remove" onClick={() => handleRemoveChar(c.id)}>
                Убрать
              </button>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState icon="✦" title="Пока никого нет" description="Персонажи мира — это население истории, необязательно с ними разговаривать напрямую: можно встретить их прямо внутри «Войти в мир»." />
      )}

      <div className="world-detail__actions">
        <SecondaryButton onClick={() => navigate(`/characters/new?world_id=${world.id}`)}>+ Добавить персонажа</SecondaryButton>
        <SecondaryButton onClick={startAICreation}>✦ Придумать персонажа с ИИ</SecondaryButton>
        <SecondaryButton onClick={() => navigate(`/worlds/${world.id}/edit`)}>Изменить мир</SecondaryButton>
        {!confirmDelete ? (
          <SecondaryButton danger onClick={() => setConfirmDelete(true)}>
            Удалить мир
          </SecondaryButton>
        ) : (
          <div className="world-detail__confirm">
            <p>Удалить мир «{world.name}»? Персонажи останутся, но без мира.</p>
            <div className="world-detail__confirm-row">
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
