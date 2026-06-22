# Course Material Schema

Draft schema for normalized course material records.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `source_id` | string | yes | Stable source identifier |
| `source_type` | string | yes | syllabus, slide, transcript, forum, assignment, rubric, faq |
| `title` | string | yes | Human-readable title |
| `author` | string | no | Instructor or source author |
| `course_id` | string | yes | Course or section identifier |
| `created_at` | date | no | Original source creation date |
| `permission` | string | yes | Approved usage scope |
| `content` | string | yes | Normalized text content |
| `metadata` | object | no | Source-specific metadata |
