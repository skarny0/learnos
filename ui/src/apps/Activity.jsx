import { useWorkspace, Empty } from "./common";
import { clock } from "../time";

export const ACT_COLORS = {
  reader: "#3b6fd8", messages: "#2f9e6a", quiz: "#8a5cd6", notes: "#c28a1e",
  feed: "#e0457b", idle: "#9a9a9a",
};

// The tracker's view of the student. Screen-level and noisy: 'idle' may be rest OR an off-screen phone.
export default function Activity() {
  const ws = useWorkspace();
  if (!ws) return <Empty>No episode.</Empty>;
  const acts = ws.student_activity;
  if (!acts.length) return <Empty>No tracked activity yet. It appears whenever learner time passes.</Empty>;

  const span = Math.max(ws.t, 1);
  const totals = {};
  for (const a of acts) totals[a.app] = (totals[a.app] || 0) + a.minutes;

  return (
    <div className="activity">
      <div className="timeline">
        {acts.map((a, i) => (
          <div key={i} title={`${clock(a.t)} · ${a.app} · ${a.minutes}m`}
               style={{ left: `${(100 * a.t) / span}%`, width: `${(100 * a.minutes) / span}%`,
                        background: ACT_COLORS[a.app] || "#555" }} />
        ))}
      </div>
      <div className="axis"><span>{clock(0)}</span><span>{clock(ws.t)}</span></div>
      <div className="legend">
        {Object.entries(totals).sort((a, b) => b[1] - a[1]).map(([app, m]) => (
          <span key={app}><i style={{ background: ACT_COLORS[app] || "#555" }} />{app} {m}m</span>
        ))}
        <span className="dim">gaps = tracker missed it</span>
      </div>
      <div className="log">
        {acts.slice(-30).reverse().map((a, i) => (
          <div key={i}><code>{clock(a.t)}</code> <i style={{ background: ACT_COLORS[a.app] || "#555" }} /> {a.app} · {a.minutes}m</div>
        ))}
      </div>
    </div>
  );
}
