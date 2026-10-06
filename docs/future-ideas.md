# Future ideas

Ideas we want to keep but are not building now. Each has enough context to pick it up later.

## Classroom: one teacher agent, many simulated students
*Tabled 2026-10-01.*

**Idea.** Scale from one tutor and one student to one teacher agent coordinating a whole class: many
simulated students of mixed learner types in the same workspace at once, each with their own hidden state,
activity stream and DMs. The teacher's time is the budget, so every minute spent on one student is a minute not
spent on another. Questions become about allocation: who needs help now, the struggling student or the bored
one, and who is quietly drifting to the feed?

**Where it would sit.** After "many kinds of learners" and "add a cognitive brick" in `curriculum.md`, before
the in-the-wild module. Students would carry their tutor agent forward into a teacher agent, and their reward
forward into a class-level reward (mean? worst student? equity across learner types?). Observability changes
shape: one run contains a timeline per student, and the question is who got neglected and why.

**How to build it without breaking anything.**
- Episodes hold several learners instead of one.
- Learner-facing tools (`messages_send_to_student`, `quiz_run`, `reader_open_section`, ...) gain an optional
  `student` argument that defaults to the only student, so one-on-one is a class of size 1 and every existing
  tool, notebook and test keeps working (same tool names; non-negotiable 7).
- Activity events and DMs are tagged by student; the desktop gets a student switcher.
- Budget becomes the teacher's minutes rather than one learner's.
- Depends on the construct ("brick") refactor and the learner-type library, so it should come after both.

**Open question.** Do students affect each other (one student's scrolling distracts a neighbour; students help
each other), or are they independent learners who only share a teacher? Independent is much simpler; peer
effects are richer and closer to a real classroom.

## Screen-based tutor: a vision model that sees and clicks the desktop
*Noted 2026-10-05.*

**Idea.** Today the tutor acts through text tools and the desktop only replays what happened (and, in live mode,
is where the human studies). The extension: give the tutor screenshots of the desktop plus its accessibility tree,
and have it act by clicking and typing, the way computer-use agents (OpenAI's Operator, Anthropic's computer use,
OSWorld) navigate real app and OS UI hierarchies.

**Why it is not the base workshop.** It moves the difficulty from "what is good for this student?" to "can the
model find the button?". Small models mostly fail at the clicking, which hides the cognitive-outcome question the
workshop is about. Runs are also slower and costlier, which hurts pass^k over many seeds.

**How to build it without breaking anything.**
- The desktop already renders every app from the websocket payload, so a screenshot is one headless-browser capture.
- Add an accessibility tree export (window titles, buttons, list items with ids) next to the screenshot.
- A thin action layer maps `click(id)` / `type(text)` onto the same tool calls the text agent uses, so the tool
  names, traces and grader stay identical (non-negotiable 7). Screen and text tutors can then be compared on the
  same seeds.
