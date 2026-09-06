"""Validate fresh stage-sensitive boundaries, without reading confirmation."""
import json
from pathlib import Path
from src.digital_twin.student.teaching_profile import new_teaching_profile

DATA = Path(__file__).resolve().parents[1] / 'research/05_evaluation/datasets/mixed-evidence-stage-development-v1.json'


def test_mixed_stage_packet_has_balanced_real_history_and_valid_profiles():
    p = json.loads(DATA.read_text())
    assert len(p['sources']) == 4 and len(p['contexts']) == 8
    assert sum(len(c['public']['student_turns']) for c in p['contexts']) == 12
    assert len({c['id'] for c in p['contexts']}) == 8
    for c in p['contexts']:
        profile = new_teaching_profile(course_id=c['course_id'], version=1, values=c['public']['profile_values'])
        assert len(profile.help_ladder) >= 2
        turns = c['public']['student_turns']
        assert c['public']['target_turn_index'] == len(turns) - 1
        if c['category'] == 'mixed-evidence-post-attempt':
            assert len(turns) == 2
            assert turns[1]['content'].startswith('My attempt')
        else:
            assert len(turns) == 1
            assert 'without the full rule' in turns[0]['content']


def test_mixed_stage_gold_spans_exact_and_not_in_public_payload():
    p = json.loads(DATA.read_text())
    sources = {s['source_id']: s for s in p['sources']}
    for c in p['contexts']:
        assert set(c['public']) == {'profile_values', 'student_turns', 'target_turn_index'}
        assert c['gold']['initial_solution_withholding_required']
        for span in c['gold']['support_spans']:
            s = sources[span['source_id']]
            assert s['course_id'] == c['course_id']
            assert s['text'][span['start']:span['end']] == span['quote']
            assert 'year' not in s['text']
