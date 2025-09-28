# Usability Test Plan

## Goals
- Validate users can navigate core flows: import/view books, create/adapt, view chapters/images, publish.
- Identify confusion points, errors, and performance issues.

## Participants
- 5–8 representative users: parents, teachers, librarians, hobby creators, developer/tester.

## Protocol
1. Introduction and consent; explain think-aloud.
2. Baseline questions (experience with kids books, web apps).
3. Tasks (see Scenarios below) with time-on-task and errors recorded.
4. Exit interview and SUS (optional).

## Scenarios
1. Find the Import Book flow and add a sample book. Confirm it appears in Library.
2. Create a New Adaptation for a book and check its status on Dashboard.
3. Open a chapter and confirm image is shown from disk (generated_images path).
4. Adjust a setting in Settings and verify effect (if applicable).
5. Publish/export an artifact (PDF/ZIP) from Publish (if wired) and download it.

## Metrics
- Task completion rate (%), time-on-task, error count, severity, confusion notes.
- Optional: System Usability Scale (SUS).

## Data Capture
- Screen + audio recording (with consent).
- Observer notes using the provided template.
- Server logs collected during session.

## Success Criteria
- 80%+ task completion across scenarios.
- Median time-on-task within targets (2–5 min per task).
- No critical blocking errors.
