# GitHub Project Link

Project board: https://github.com/users/horiiiiii032929/projects/1

This repository is scaffolded to create issues that are automatically added to
the linked GitHub Project by using the `projects: ["horiiiiii032929/1"]` key in
the issue form templates.

## Project Fields

The project currently exposes these planning fields:

- Status: Todo, In Progress, Done
- Decision: Pending, Keep, Refine, Go Deeper, Drop
- Work Type: Feature, Research, Design, Prototype, Documentation, Evaluation, Bug
- Iteration: I1 Instructor Onboarding, I2 Student Active Tutoring, I3 Proactive
  Interaction, I4 Learning Gap Report, I5 Evaluation and Refinement
- Area: Instructor, Student, AI Agent, RAG, Analytics, Architecture,
  Documentation, Evaluation
- Risk: Low, Medium, High
- Evidence: free text
- Sprint: free text
- Target Date: date

## Local Workflow

1. Create work through the `Research Task` or `Decision Record` issue form.
2. Fill in Iteration, Work Type, Area, Risk, and Evidence in the issue body.
3. After the issue appears on the project board, mirror those values into the
   matching project fields.
4. Link pull requests back to the issue and include verification evidence.

Note: GitHub requires the person opening the issue to have write access to the
target project for automatic project assignment from issue forms.
