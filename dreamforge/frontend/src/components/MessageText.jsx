import { parseMessageSegments } from "../utils/messageFormat";
import "./MessageText.css";

export default function MessageText({ content }) {
  const segments = parseMessageSegments(content);
  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === "action") {
          return (
            <span className="msg-action" key={i}>
              {seg.text}
            </span>
          );
        }
        if (seg.type === "thought") {
          return (
            <span className="msg-thought" key={i}>
              {seg.text}
            </span>
          );
        }
        return <span key={i}>{seg.text}</span>;
      })}
    </>
  );
}
