"""V15 shares contracts without silently changing the V14 control prompt."""
import pytest
from src.digital_twin.generation.conditional_revision import INSTRUCTION, conditionally_revise_instructional_proposal
from src.digital_twin.generation.global_support_revision import GLOBAL_INSTRUCTION, globally_assess_instructional_proposal
from tests.test_conditional_revision_generation import Client, decision
from tests.test_compact_instruction_generation import proposal

@pytest.mark.asyncio
async def test_versioned_assessment_keeps_public_input_and_original_proposal():
    draft=proposal()
    payload={'question':'Explain the permitted rule.', 'evidence':[]}
    control=Client();candidate=Client()
    old=await conditionally_revise_instructional_proposal(control,payload=payload,draft=draft)
    new=await globally_assess_instructional_proposal(candidate,payload=payload,draft=draft)
    assert control.calls[0][1][0].content==INSTRUCTION
    assert candidate.calls[0][1][0].content==GLOBAL_INSTRUCTION
    assert control.calls[0][1][1]==candidate.calls[0][1][1]
    assert old.proposal==new.proposal and old.draft_sha256==new.draft_sha256
    assert len(candidate.calls)==1

@pytest.mark.asyncio
async def test_global_assessment_retains_shared_repair_schema():
    replacement=proposal();replacement['units'][0]['text']='A supported replacement.'
    client=Client(decision(replacement))
    result=await globally_assess_instructional_proposal(client,payload={},draft=proposal())
    assert result.decision.disposition=='repair'
    assert result.proposal.model_dump(mode='json')==replacement
