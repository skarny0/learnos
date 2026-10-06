import { useEffect, useRef, useState } from "react";
import { useWorkspace, Empty } from "./common";
import { clock } from "../time";

const DEFAULT_CHANNELS = ["#course", "dm:student", "dm:instructor"];

export default function Messages() {
  const ws = useWorkspace();
  const [chan, setChan] = useState("dm:student");
  const end = useRef(null);
  const msgs = (ws?.messages || []).filter((m) => m.channel === chan);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [msgs.length, chan]);
  if (!ws) return <Empty>No episode.</Empty>;

  const channels = [...new Set([...DEFAULT_CHANNELS, ...ws.messages.map((m) => m.channel)])];
  const unread = (c) => ws.messages.filter((m) => m.channel === c && !m.read && m.author !== "agent").length;

  return (
    <div className="split">
      <ul className="side">
        {channels.map((c) => (
          <li key={c} className={c === chan ? "sel" : ""} onClick={() => setChan(c)}>
            {c.startsWith("#") ? c : "@ " + c.slice(3)}
            {unread(c) > 0 && <span className="count">{unread(c)}</span>}
          </li>
        ))}
        <li className="hint">Unread = not yet read by the agent</li>
      </ul>
      <div className="main chat">
        {msgs.length === 0 && <Empty>No messages.</Empty>}
        {msgs.map((m) => (
          <div key={m.id} className={"bubble " + (m.author === "agent" ? "me" : m.author === "student" ? "student" : "other")}>
            <div className="meta">
              {m.author === "agent" ? "🤖 agent" : m.author} · {clock(m.t)}
              {m.intent && <span className={"intent " + m.intent}>{m.intent}</span>}
            </div>
            <div>{m.text}</div>
          </div>
        ))}
        <div ref={end} />
      </div>
    </div>
  );
}
