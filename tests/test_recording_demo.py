import asyncio

from scripts.build_recording_demo import build_trace


def test_recording_trace_keeps_identities_and_pause_outcomes_separate(tmp_path):
    trace = asyncio.run(build_trace(tmp_path / "recording.sqlite3"))
    assert len(trace["courses"]) == 2
    assert len({course["professor"] for course in trace["courses"]}) == 2
    assert len({student["id"] for student in trace["students"]}) == 4
    by_student = {student["id"]: student["course"] for student in trace["students"]}
    turns = [event for event in trace["events"] if event["kind"] == "turn"]
    assert len(turns) == 4
    conversations = set()
    for event in turns:
        assert event["course"] == by_student[event["student"]]
        turn = event["data"]["turn"]
        conversations.add(turn["student_message"]["conversation_id"])
        assert turn["citations"]
        assert all(citation["course_id"] == event["course"] for citation in turn["citations"])
        assert event["data"]["saved_message_count"] == 2
        assert event["data"]["state"]["revision"] >= 1
    assert len(conversations) == 4
    support = [event for event in trace["events"] if event["kind"] == "support"]
    assert len(support[0]["data"]["inbox"]) == 1
    assert support[1]["data"]["inbox"] == []
    assert support[1]["data"]["opportunity"]["status"] == "pending"
    retry = trace["events"][-1]
    assert retry["kind"] == "retry"
    assert sum(retry["data"]["inbox_counts"].values()) == 1
    assert [event["at"] for event in trace["events"]] == sorted(event["at"] for event in trace["events"])

