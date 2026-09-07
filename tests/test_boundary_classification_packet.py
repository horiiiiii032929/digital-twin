"""Validate the separate privacy interpretation packet without reading confirmation."""
import json
from collections import Counter
from pathlib import Path

from src.digital_twin.student.teaching_profile import new_teaching_profile

DATA = Path(__file__).resolve().parents[1] / 'research/05_evaluation/datasets/boundary-classification-development-v1.json'


def test_boundary_packet_balanced_and_product_compatible():
    packet = json.loads(DATA.read_text())
    assert len(packet['contexts']) == 8
    assert set(Counter(c['category'] for c in packet['contexts']).values()) == {2}
    assert len({c['id'] for c in packet['contexts']}) == 8
    for c in packet['contexts']:
        profile = new_teaching_profile(course_id=c['course_id'], version=1, values=c['public']['profile_values'])
        assert len(profile.help_ladder) >= 2
        assert len(c['public']['student_turns']) == 1
        assert c['public']['target_turn_index'] == 0
        assert not c['gold']['initial_solution_withholding_required']
        assert set(c['public']) == {'profile_values', 'student_turns', 'target_turn_index'}


def test_boundary_gold_has_exact_approved_spans_and_no_personal_values():
    packet = json.loads(DATA.read_text())
    sources = {s['source_id']: s for s in packet['sources']}
    for c in packet['contexts']:
        assert c['gold']['expected_request_interpretation']
        for span in c['gold']['support_spans']:
            s = sources[span['source_id']]
            assert s['course_id'] == c['course_id']
            assert s['text'][span['start']:span['end']] == span['quote']
    assert all('@' not in s['text'] for s in sources.values())
    assert all('gold' not in c['public'] for c in packet['contexts'])
