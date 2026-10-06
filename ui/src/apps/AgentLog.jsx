import { useEffect, useRef } from "react";
import { usePayload, Empty } from "./common";
import { useDesk, appForAction, APPS } from "../store";
import { clock } from "../time";

export default function AgentLog() {
  const p = usePayload();
  const follow = useDesk((s) => s.follow);
  const story = useDesk((s) => s.story);
  const end = useRef(null);
  const log = p?.action_log || [];
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [log.length]);
  if (!p) return <Empty>No episode.</Empty>;

  return (
    <div className="agentlog">
      <div className="toolbar">
        <label><input type="checkbox" checked={story} onChange={() => useDesk.getState().toggleStory()} /> Story mode (tutor, then student)</label>
        <label><input type="checkbox" checked={follow} onChange={() => useDesk.getState().toggleFollow()} /> Follow agent</label>
      </div>
      {log.length === 0 && <Empty>Waiting for the agent's first action…</Empty>}
      {log.map((e) => {
        const app = APPS.find((a) => a.id === appForAction(e.action));
        return (
          <div key={e.step + e.action} className="entry">
            <div className="head">
              <span className="step">#{e.step}</span> {app?.icon} <b>{e.action}</b>
              <span className="dim"> {clock(e.t)}</span>
            </div>
            {Object.keys(e.args).length > 0 && <code className="args">{JSON.stringify(e.args)}</code>}
            <pre>{e.output}</pre>
          </div>
        );
      })}
      <div ref={end} />
    </div>
  );
}
