import { Component, useRef } from "react";
import { useDesk } from "./store";
import { useStory } from "./story";

// One app crashing must not unmount the whole desktop: contain it to its own window.
class Contain extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="empty">
        This window crashed: <code>{String(this.state.error.message || this.state.error)}</code>{" "}
        <button onClick={() => this.setState({ error: null })}>Retry</button>
      </div>
    );
  }
}

// System-7-style window: striped title bar (drag), close box, collapse box, resize corner.
export default function Window({ id, title, children }) {
  const win = useDesk((s) => s.wins[id]);
  const focused = useDesk((s) => s.focused === id);
  const actor = useStory((s) => (s.beat && s.beat.app === id ? s.beat.actor : null));
  const { focus, close, minimize, move } = useDesk.getState();
  const drag = useRef(null);

  if (!win || win.min) return null;

  const startDrag = (e, kind) => {
    e.preventDefault();
    e.stopPropagation();
    focus(id);
    drag.current = { kind, sx: e.clientX, sy: e.clientY, ...win };
    const onMove = (ev) => {
      const d = drag.current;
      const dx = ev.clientX - d.sx, dy = ev.clientY - d.sy;
      if (d.kind === "move") move(id, { x: Math.max(-d.w + 80, d.x + dx), y: Math.max(22, d.y + dy) });
      else move(id, { w: Math.max(260, d.w + dx), h: Math.max(160, d.h + dy) });
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  return (
    <div
      className={"win" + (focused ? " focused" : "") + (actor ? " actor-" + actor : "")}
      style={{ left: win.x, top: win.y, width: win.w, height: win.h, zIndex: win.z }}
      onPointerDown={() => focus(id)}
    >
      <div className="titlebar" onPointerDown={(e) => startDrag(e, "move")}>
        <button className="box close" title="Close" onPointerDown={(e) => e.stopPropagation()} onClick={() => close(id)} />
        <span className="title">{title}</span>
        <button className="box collapse" title="Minimize" onPointerDown={(e) => e.stopPropagation()} onClick={() => minimize(id)} />
      </div>
      <div className="body"><Contain>{children}</Contain></div>
      <div className="grow" onPointerDown={(e) => startDrag(e, "resize")} />
    </div>
  );
}
