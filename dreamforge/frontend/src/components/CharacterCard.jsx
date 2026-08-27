import { useNavigate } from "react-router-dom";
import "./CharacterCard.css";

export default function CharacterCard({ character }) {
  const navigate = useNavigate();
  return (
    <div className="char-card" onClick={() => navigate(`/characters/${character.id}`)}>
      <div className="char-card__image">
        {character.avatar_path ? (
          <img src={`/uploads/${character.avatar_path}`} alt={character.name} />
        ) : (
          <div className="char-card__placeholder">☾</div>
        )}
      </div>
      <div className="char-card__body">
        <div className="char-card__name">{character.name}</div>
        <div className="char-card__desc">{character.personality || "Характер не указан"}</div>
        <button
          className="char-card__chat-btn"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/chat/${character.id}`);
          }}
        >
          Заговорить
        </button>
      </div>
    </div>
  );
}

export function CreateCard({ onClick, label = "Создать" }) {
  return (
    <div className="char-card char-card--create" onClick={onClick}>
      <span className="char-card__plus">+</span>
      <span>{label}</span>
    </div>
  );
}

export function AICreateCard({ onClick, label = "Придумать с ИИ" }) {
  return (
    <div className="char-card char-card--ai-create" onClick={onClick}>
      <span className="char-card__ai-glyph">✦</span>
      <span>{label}</span>
    </div>
  );
}
