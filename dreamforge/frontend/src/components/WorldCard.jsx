import { useNavigate } from "react-router-dom";
import { formatRelativeTime } from "../utils/time";
import "./WorldCard.css";

export default function WorldCard({ world }) {
  const navigate = useNavigate();
  return (
    <div className="world-list-card" onClick={() => navigate(`/worlds/${world.id}`)}>
      <div className="world-list-card__image">
        {world.image_path ? (
          <img src={`/uploads/${world.image_path}`} alt={world.name} />
        ) : (
          <div className="world-list-card__placeholder">◈</div>
        )}
        <div className="world-list-card__scrim" />
        <div className="world-list-card__title-overlay">
          <span className="font-display">{world.name}</span>
        </div>
      </div>
      <div className="world-list-card__body">
        <p className="world-list-card__desc">{world.description || "Нет описания"}</p>
        {world.created_at && <span className="world-list-card__time">{formatRelativeTime(world.created_at)}</span>}
      </div>
    </div>
  );
}
