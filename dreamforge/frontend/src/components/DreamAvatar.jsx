import "./DreamAvatar.css";

const PLACEHOLDER_GLYPHS = ["☾", "✦", "◈", "❋"];

function glyphFor(name) {
  if (!name) return PLACEHOLDER_GLYPHS[0];
  const code = name.charCodeAt(0) || 0;
  return PLACEHOLDER_GLYPHS[code % PLACEHOLDER_GLYPHS.length];
}

export default function DreamAvatar({ src, name, size = 52, glow = true }) {
  const style = { width: size, height: size };
  return (
    <div className={"dream-avatar" + (glow ? " dream-avatar--glow" : "")} style={style}>
      {src ? (
        <img src={src} alt={name} />
      ) : (
        <span className="dream-avatar__glyph" style={{ fontSize: size * 0.42 }}>
          {glyphFor(name)}
        </span>
      )}
    </div>
  );
}
