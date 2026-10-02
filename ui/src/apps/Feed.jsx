import { useWorkspace, Empty } from "./common";
import { ago } from "../time";

const hue = (s) => [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);

export default function Feed() {
  const ws = useWorkspace();
  if (!ws) return <Empty>No episode.</Empty>;
  const muted = new Set(ws.feed_muted);
  const posts = ws.feed.filter((p) => p.t <= ws.t).sort((a, b) => b.t - a.t);

  return (
    <div className="feed">
      {muted.size > 0 && <div className="banner">Muted by agent: {[...muted].join(", ")}</div>}
      {posts.length === 0 && <Empty>Nothing here.</Empty>}
      {posts.map((p) => {
        const isMuted = muted.has("all") || muted.has(p.source);
        return (
          <div key={p.id} className={"post" + (isMuted ? " muted" : "")}>
            <div className="avatar" style={{ background: `hsl(${hue(p.source)} 55% 55%)` }}>
              {p.source.replace(/[#@]/, "").slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="meta"><b>{p.source}</b> · {ago(ws.t, p.t)}{isMuted && " · muted"}</div>
              <div>{p.text}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
