import { useState } from "react";
import { Markdown, useWorkspace, usePayload, lastAction, sliceSection, Empty } from "./common";

// Shows what the agent last opened for the student (reader_open_section), or lets you browse.
export default function Reader() {
  const ws = useWorkspace();
  const p = usePayload();
  const [pick, setPick] = useState(null);
  if (!ws) return <Empty>No episode.</Empty>;

  const last = lastAction(p.action_log, "reader");
  const assigned = last && last.action === "reader_open_section" && !last.output.startsWith("Section not found") ? last.args : null;
  const files = Object.values(ws.files).filter((f) => f.kind === "file");
  const cur = pick || (assigned && { path: assigned.path, section: assigned.section }) ||
              (files[0] && { path: files[0].path, section: files[0].sections[0] });
  const file = cur && ws.files[cur.path];

  return (
    <div className="split">
      <ul className="side">
        {files.map((f) => (
          <li key={f.path}>
            <div className="group">{f.path.split("/").pop()}</div>
            <ul>
              {f.sections.map((s) => (
                <li key={s} className={cur && cur.path === f.path && cur.section === s ? "sel" : ""}
                    onClick={() => setPick({ path: f.path, section: s })}>
                  {s}
                  {assigned && assigned.path === f.path && assigned.section === s && <span className="badge student">📖 assigned</span>}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
      <div className="main">
        {assigned && (
          <div className="banner">
            Agent assigned <b>{assigned.section}</b> (concept: <code>{assigned.concept}</code>)
            {pick && <button onClick={() => setPick(null)}>Show assigned</button>}
          </div>
        )}
        {file ? <Markdown text={sliceSection(file.content, cur.section)} /> : <Empty>Nothing open.</Empty>}
      </div>
    </div>
  );
}
