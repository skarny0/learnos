import { useState } from "react";
import { Markdown, useWorkspace, usePayload, AgentBadge, Empty } from "./common";
import { useDesk } from "../store";

export default function Files() {
  const ws = useWorkspace();
  const p = usePayload();
  const [sel, setSel] = useState(null);
  if (!ws) return <Empty>No episode.</Empty>;

  const opened = new Set((p.agent_opened || []).filter((o) => o.startsWith("files:")).map((o) => o.slice(6)));
  const paths = Object.keys(ws.files).sort();
  const file = sel && ws.files[sel];

  return (
    <div className="split">
      <ul className="side tree">
        {paths.map((path) => {
          const f = ws.files[path];
          const depth = path.split("/").length - 2;
          return (
            <li key={path} className={(sel === path ? "sel " : "") + f.kind}
                style={{ paddingLeft: 6 + depth * 14 }}
                onClick={() => f.kind === "file" && setSel(path)}>
              {f.kind === "dir" ? "📁" : "📄"} {path.split("/").pop() || "/"}
              {opened.has(path) && <AgentBadge>seen</AgentBadge>}
            </li>
          );
        })}
      </ul>
      <div className="main">
        {file ? (
          <>
            <div className="toolbar">
              <b>{sel}</b>
              <button onClick={() => useDesk.getState().open("reader")}>Open in Reader</button>
            </div>
            <Markdown text={file.content} />
          </>
        ) : (
          <Empty>Select a file.</Empty>
        )}
      </div>
    </div>
  );
}
