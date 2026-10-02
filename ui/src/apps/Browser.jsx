import { useState } from "react";
import { Markdown, useWorkspace, usePayload, lastAction, Empty } from "./common";

export default function Browser() {
  const ws = useWorkspace();
  const p = usePayload();
  const [typed, setTyped] = useState(null);
  if (!ws) return <Empty>No episode.</Empty>;

  const last = lastAction(p.action_log, "browser");
  const url = typed ?? (last?.args.url || Object.keys(ws.pages)[0] || "course://schedule");
  const page = ws.pages[url];

  return (
    <div className="browser">
      <div className="toolbar">
        <select value="" onChange={(e) => setTyped(e.target.value)}>
          <option value="" disabled>Bookmarks</option>
          {Object.keys(ws.pages).map((u) => <option key={u} value={u}>{u}</option>)}
        </select>
        <input value={url} onChange={(e) => setTyped(e.target.value)} spellCheck={false} />
      </div>
      <div className="main">
        {page ? (
          <>
            <h2>{page.title}</h2>
            <Markdown text={page.content} />
          </>
        ) : (
          <Empty>404 — {url} not found</Empty>
        )}
      </div>
    </div>
  );
}
