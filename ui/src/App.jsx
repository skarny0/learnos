import { useEffect, useState } from "react";
import { useEnv, useDesk, APPS, appForAction } from "./store";
import { clock } from "./time";
import Window from "./Window";
import Files from "./apps/Files";
import Reader from "./apps/Reader";
import Notes from "./apps/Notes";
import Calendar from "./apps/Calendar";
import Messages from "./apps/Messages";
import Quiz from "./apps/Quiz";
import Browser from "./apps/Browser";
import Feed from "./apps/Feed";
import Activity from "./apps/Activity";
import AgentLog from "./apps/AgentLog";

const VIEWS = { files: Files, reader: Reader, notes: Notes, calendar: Calendar, messages: Messages,
                quiz: Quiz, browser: Browser, feed: Feed, activity: Activity, agent: AgentLog };

function MenuBar() {
  const p = useEnv((s) => s.payload);
  const connected = useEnv((s) => s.connected);
  const focused = useDesk((s) => s.focused);
  const [menu, setMenu] = useState(false);
  const app = APPS.find((a) => a.id === focused);
  const b = p?.budget;

  return (
    <div className="menubar" onPointerLeave={() => setMenu(false)}>
      <span className="logo" onClick={() => setMenu(!menu)}>◆</span>
      {menu && (
        <div className="dropdown">
          {APPS.map((a) => (
            <div key={a.id} onClick={() => { useDesk.getState().open(a.id); setMenu(false); }}>{a.icon} {a.title}</div>
          ))}
        </div>
      )}
      <b>{app ? app.title : "LearnOS"}</b>
      <span className="spacer" />
      {p ? (
        <>
          <span className="pill">{p.mode === "live" ? "LIVE" : "sim"} · L{p.level}</span>
          <span>{p.instance_id}</span>
          <span>step {p.step}/{b.agent_steps}</span>
          <span>{p.workspace.t}/{b.learner_minutes} learner-min</span>
          {p.done && <span className="pill done">ended: {p.termination}</span>}
          <b>{clock(p.workspace.t)}</b>
        </>
      ) : (
        <span>no episode</span>
      )}
      <span className={"dot " + (connected ? "on" : "off")} title={connected ? "connected" : "reconnecting…"} />
    </div>
  );
}

function Dock() {
  const wins = useDesk((s) => s.wins);
  const ws = useEnv((s) => s.payload?.workspace);
  const unread = ws ? ws.messages.filter((m) => !m.read && m.author !== "agent").length : 0;
  const learning = APPS.filter((a) => !a.system), system = APPS.filter((a) => a.system);
  const Icon = (a) => (
    <button key={a.id} className={"dock-icon" + (wins[a.id] ? " running" : "")} title={a.title}
            onClick={() => useDesk.getState().open(a.id)}>
      <span>{a.icon}</span>
      {a.id === "messages" && unread > 0 && <i className="count">{unread}</i>}
      <small>{a.title.split(" ")[0]}</small>
    </button>
  );
  return (
    <div className="dock">
      {learning.map(Icon)}
      <div className="sep" />
      {system.map(Icon)}
    </div>
  );
}

// Follow mode: when the agent acts, bring up the window for the app it used.
function useFollowAgent() {
  const log = useEnv((s) => s.payload?.action_log);
  const last = log && log[log.length - 1];
  useEffect(() => {
    if (!last || !useDesk.getState().follow) return;
    useDesk.getState().open(appForAction(last.action));
  }, [last?.step, last?.action]);
}

export default function App() {
  const wins = useDesk((s) => s.wins);
  const p = useEnv((s) => s.payload);
  useFollowAgent();
  useEffect(() => {
    const d = useDesk.getState();
    // ?open=calendar,messages pre-opens windows (handy on a projector)
    const extra = (new URLSearchParams(location.search).get("open") || "").split(",").filter(Boolean);
    if (!Object.keys(d.wins).length) for (const id of ["agent", "activity", ...extra]) if (VIEWS[id]) d.open(id);
  }, []);

  return (
    <div className="desktop">
      <MenuBar />
      {!p && (
        <div className="hello">
          <h1>LearnOS</h1>
          <p>No episode yet. Start one with <code>POST /reset</code> (try <a href="/api/docs" target="_blank">/api/docs</a>)
          or run an agent from the client. This desktop shows whatever the environment is doing.</p>
        </div>
      )}
      {Object.keys(wins).map((id) => {
        const View = VIEWS[id];
        const a = APPS.find((x) => x.id === id);
        return <Window key={id} id={id} title={a.title}><View /></Window>;
      })}
      <Dock />
    </div>
  );
}
