"""Narrow instructional state-transition routing; source authority stays separate."""
import re
from src.digital_twin.action_router import DeterministicActionRouterV3
from .audited_instruction import AuditedInstructionalGenerator

_TRANSITION_QUESTION = re.compile(
    r'\bwhat happens\s+if\b.{0,120}\b(?:release|material|source|document)\b'
    r'.{0,40}\b(?:is|gets|was)\s+(?:withdrawn|unpublished|restricted)\b', re.I)
_ACCESS_OR_OVERRIDE = re.compile(
    r'\b(?:use|using|quote|read|retrieve|summari[sz]e|show|provide|give|extract|send|'
    r'reveal|disclose|download|access|ignore|bypass|override|disregard|pretend)\b', re.I)


class InstructionalSourceStateRouter(DeterministicActionRouterV3):
    implementation_id = 'instructional-source-state-router-v1'
    version = 'v1-experimental'

    def _route(self, question, *, defer_demonstrative_ambiguity):
        route = super()._route(question, defer_demonstrative_ambiguity=defer_demonstrative_ambiguity)
        normalized = ' '.join(question.split())
        if (route is not None and route.matched_rule == 'current-authorized-evidence-only-v3'
                and _TRANSITION_QUESTION.search(normalized)
                and normalized.count('?') <= 1 and ';' not in normalized
                and not _ACCESS_OR_OVERRIDE.search(normalized)):
            # Admission means only that this is not an explicit request to read
            # unavailable material. Retrieval, actual permissions, final source
            # association and the fallible content audit are still mandatory.
            return None
        return route


class SourceStateInstructionalGenerator(AuditedInstructionalGenerator):
    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.policy_enforcer.action_router = InstructionalSourceStateRouter()
        self.implementation_id = 'question-specific-profile-grounded-v19'
        self.version = 'v19-development'
