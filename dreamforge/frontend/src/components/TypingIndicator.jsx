import "./TypingIndicator.css";

export default function TypingIndicator({ name }) {
  return (
    <div className="typing-indicator">
      {name && <div className="typing-indicator__name">{name}</div>}
      <div className="typing-indicator__dots">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
