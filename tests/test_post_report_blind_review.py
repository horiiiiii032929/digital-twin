import json
import sqlite3
from scripts import run_post_report_blind_review as review


def test_packet_includes_all_failed_and_successful_outputs_without_arm_metadata(tmp_path, monkeypatch):
    # CI must not require ignored evaluation databases from the author's machine.
    monkeypatch.setattr(review, 'ROOT', tmp_path)
    monkeypatch.setattr(review, 'RUNS', ['synthetic-review-fixture'])
    root = tmp_path / 'reports/generated/synthetic-review-fixture'
    root.mkdir(parents=True)
    profile = {'tone': 'Patient', 'help_ladder': ['Explain from the source']}
    (root/'packet.json').write_text(json.dumps({'contexts': [{'id':'case', 'public': {'profile_values':profile}}]}))
    histories=[]
    for i in range(76):
        folder=root/f'history-{i}'
        (folder/'runtime').mkdir(parents=True)
        histories.append({'case_id':'case','id':folder.name,'planned_turns':2,'version':'baseline' if i%2 else 'candidate'})
        with sqlite3.connect(folder/'runtime/runtime.sqlite3') as conn:
            conn.executescript("CREATE TABLE releases(id TEXT, teaching_profile_id TEXT, course_id TEXT, status TEXT); CREATE TABLE teaching_profiles(profile_id TEXT, profile_json TEXT); CREATE TABLE release_chunks(release_id TEXT,chunk_id TEXT,chunk_json TEXT);")
            conn.execute("INSERT INTO releases VALUES ('release','profile','course-a-synthetic','published')")
            conn.execute("INSERT INTO teaching_profiles VALUES (?,?)",('profile',json.dumps(profile)))
            chunk={'source_artifact_id':'source','source_version':1,'source_checksum':'a'*64,'locator':'paragraph1','document_id':'Synthetic note','text':'The approved token expires after two steps.'}
            conn.execute('INSERT INTO release_chunks VALUES (?,?,?)',('release','chunk',json.dumps(chunk)))
        turns=[]
        for stage in range(2):
            turns.append({'stage':stage,'student':'When does the token expire?', 'turn':{'tutor_message':{'content':'The approved token expires after two steps.' if i%2 else 'Response unavailable.', 'action':'answer' if i%2 else 'safe-graph-failure'}, 'citations':[]}})
        (folder/'turns.jsonl').write_text(''.join(json.dumps(t)+'\n' for t in turns))
    (root/'histories.jsonl').write_text(''.join(json.dumps(h)+'\n' for h in histories))
    rows, paths = review.product_inputs()
    assert len(rows) == 152 and paths
    assert len({r['id'] for r in rows}) == 152
    assert {r['run_id'] for r in rows} == set(review.RUNS)
    assert any(r['payload']['response']['action'] == 'safe-graph-failure' for r in rows)
    for row in rows:
        assert set(row['payload']) == {'question','profile','history','sources','response'}
        encoded=json.dumps(row['payload'])
        for forbidden in ['gpt-5.', 'observed_generator_id', 'budget_chain', 'required_meanings']:
            assert forbidden not in encoded
        assert row['payload']['question']
        assert row['payload']['sources']


def test_calibration_cannot_pass_by_majority_or_partial_completion():
    complete=[{'phase':'calibration','status':'completed','calibration_match':True} for _ in range(64)]
    assert review.calibration_gate(complete)
    assert not review.calibration_gate(complete[:-1])
    complete[-1]['calibration_match']=False
    assert not review.calibration_gate(complete)
    summary=review.summarize(complete)
    assert summary['quality_qualified'] is False
    assert summary['calibration_matched']==63


def test_repeat_agreement_excludes_repeat_failures():
    rows=[{'phase':'product','run_id':'test','arm':'a','id':'one','status':'failed','repetition':i} for i in range(2)]
    assert review.summarize(rows)['product_repeat_agreement']['agree']==0


def test_located_evidence_separates_source_from_response_and_keeps_semantic_gate():
    import pytest
    payload={'response':{'text':'A token lasts two steps.','citations':[{'source_id':'S1'}]},
             'sources':[{'text':'The approved token expires after two steps.'}]}
    ratings={k:'adequate' for k in ('grounding','relevance','completeness','profile_adherence','citation_validity')}
    value={**ratings,'usefulness':'useful','overall':'acceptable','reason':'Faithful paraphrase.',
           'evidence':[{'pointer':'/sources/0/text','excerpt':'expires after two steps'},
                       {'pointer':'/response/citations/0/source_id','excerpt':'S1'}]}
    assert review.validate_located_review(json.dumps(value),payload)['overall']=='acceptable'
    value['evidence'][0]['pointer']='/response/text'
    with pytest.raises(ValueError,match='pointed string'):
        review.validate_located_review(json.dumps(value),payload)
    value['evidence']=[]
    value['grounding']='defective'
    with pytest.raises(ValueError,match='inconsistent'):
        review.validate_located_review(json.dumps(value),payload)


def test_located_evidence_rejects_absent_nonstring_and_noncanonical_pointers():
    import pytest
    payload={'response':{'text':'answer','citations':[{'version':1}]}}
    value={k:'adequate' for k in ('grounding','relevance','completeness','profile_adherence','citation_validity')}
    value.update(usefulness='useful',overall='acceptable',reason='test')
    for pointer in ('/sources/0/text','/response/citations/0/version','/response/citations/-1','/response/citations/00','response/text'):
        value['evidence']=[{'pointer':pointer,'excerpt':'1'}]
        with pytest.raises(ValueError):review.validate_located_review(json.dumps(value),payload)


def test_scalar_evidence_requires_exact_value_in_version_three_only():
    import pytest
    value={k:'adequate' for k in ('grounding','relevance','completeness','profile_adherence','citation_validity')}
    value.update(usefulness='useful',overall='acceptable',reason='test',evidence=[{'pointer':'/response/citations/0/version','excerpt':'999'}])
    payload={'response':{'text':'answer','citations':[{'version':999}]}}
    assert review.validate_located_review(json.dumps(value),payload,allow_scalars=True)
    with pytest.raises(ValueError):review.validate_located_review(json.dumps(value),payload)
    value['evidence'][0]['excerpt']='99'
    with pytest.raises(ValueError):review.validate_located_review(json.dumps(value),payload,allow_scalars=True)
