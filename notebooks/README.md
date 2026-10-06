# Notebooks (student-facing)

learnos_workshop.ipynb   The workshop, in one notebook. Runs locally (`make notebook`) and in Colab; with no API
                         key every cell falls back to recorded runs in data/reference/.
  Setup                  keys, start LearnOS in the kernel, Langfuse tracing, the desktop
  Part A                 the environment (properties, the simulated student, the task, known limits, under the
                         hood: drive it by hand, the grader, how a tool is made), replay of a real AI tutor,
                         how we'd know it worked, Langfuse + student record, scaling up across seeds
  Part B (20 pts)        design a tutor and watch it, diagnose from the evidence, change one thing across
                         5 mixed students, change the student (a rule plugin), optional: success(), add a tool
