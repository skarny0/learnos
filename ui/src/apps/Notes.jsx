import { useState } from "react";
import { Markdown, useWorkspace, AgentBadge, Empty } from "./common";

export default function Notes() {
  const ws = useWorkspace();
  const [sel, setSel] = useState(null);
  if (!ws) return <Empty>No episode.</Empty>;
  const notes = Object.values(ws.notes);
  const note = ws.notes[sel] || notes[0];

  return (
    <div className="split">
      <ul className="side">
        {notes.map((n) => (
          <li key={n.id} className={note && note.id === n.id ? "sel" : ""} onClick={() => setSel(n.id)}>
            {n.title}
            {n.modified_at > 0 && <AgentBadge>edited</AgentBadge>}
          </li>
        ))}
      </ul>
      <div className="main paper">{note ? <Markdown text={note.body} /> : <Empty>No notes.</Empty>}</div>
    </div>
  );
}
