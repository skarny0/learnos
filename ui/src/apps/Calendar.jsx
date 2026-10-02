import { useWorkspace, Empty } from "./common";
import { clock, dayAndMinute, dayName } from "../time";

const H0 = 8, H1 = 22, PX = 32; // visible hours, pixels per hour

export default function Calendar() {
  const ws = useWorkspace();
  if (!ws) return <Empty>No episode.</Empty>;
  const events = Object.values(ws.calendar);
  const days = Math.max(3, ...events.map((e) => dayAndMinute(e.start).day + 1));
  const now = dayAndMinute(ws.t);
  const y = (min) => (Math.min(Math.max(min, H0 * 60), H1 * 60) - H0 * 60) / 60 * PX;

  return (
    <div className="calendar">
      <div className="cal-head">
        <div className="gutter" />
        {Array.from({ length: days }, (_, d) => (
          <div key={d} className={"cal-day-name" + (d === now.day ? " today" : "")}>{dayName(d)}</div>
        ))}
      </div>
      <div className="cal-grid" style={{ height: (H1 - H0) * PX }}>
        <div className="gutter">
          {Array.from({ length: H1 - H0 }, (_, i) => (
            <div key={i} className="hour" style={{ height: PX }}>{H0 + i}:00</div>
          ))}
        </div>
        {Array.from({ length: days }, (_, d) => (
          <div key={d} className="cal-col">
            {Array.from({ length: H1 - H0 }, (_, i) => <div key={i} className="cell" style={{ height: PX }} />)}
            {events.map((e) => {
              const s = dayAndMinute(e.start);
              if (s.day !== d) return null;
              const top = y(s.minute), h = Math.max(14, y(s.minute + e.duration) - top);
              return (
                <div key={e.id} className={"event " + e.kind} style={{ top, height: h }}
                     title={`${e.title}\n${clock(e.start)} · ${e.duration} min${e.note ? "\n" + e.note : ""}`}>
                  <b>{e.title}</b>
                  <span>{clock(e.start).slice(4)}</span>
                </div>
              );
            })}
            {d === now.day && now.minute >= H0 * 60 && now.minute <= H1 * 60 && (
              <div className="now-line" style={{ top: y(now.minute) }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
