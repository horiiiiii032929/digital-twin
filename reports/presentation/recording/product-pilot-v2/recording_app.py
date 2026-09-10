from pathlib import Path
from datetime import UTC,datetime
from dotenv import load_dotenv
from scripts.recording_app import ACTORS
from scripts.recording_controls import install_controls
from services.api.app.config import AppSettings,AutonomyPlannerMode,EvidenceGateMode,StudentTutoringMode
from services.api.app.factory import create_app
from services.llm import OpenAiResponsesClient
from scripts.run_final_profile_longitudinal import RecordedRunClient
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.student import SQLiteStudentRepository
from src.digital_twin.student.models import Account,AccountRole
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
ROOT=Path('/Users/hikaru/Documents/dev/digital-twin')
def create():
 load_dotenv(ROOT/'.env',override=False)
 root=ROOT/'output/playwright/product-pilot-v2/runtime';root.mkdir(parents=True,exist_ok=True)
 settings=AppSettings(data_root=root,database_path=root/'recording.sqlite3',learning_gap_hmac_secret=b'synthetic-recording-only-not-private',student_tutoring_mode=StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,evidence_gate_mode=EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3,autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE,provider_max_calls_per_process=12,provider_cost_cap_usd=1.92)
 model='gpt-5.6-luna'
 client=RecordedRunClient(OpenAiResponsesClient(model,max_output_tokens=3000,reasoning_effort='low',timeout_seconds=45),root.parent/'provider.jsonl',maximum_calls=12,maximum_cost_usd=1.92,reservation_usd=.16,expected_model=model,max_output_tokens=3000,reasoning_effort='low',network_mode='live')
 clock=VirtualUtcClock(datetime(2026,9,7,12,tzinfo=UTC))
 app=create_app(settings=settings,clock=clock,student_repository=SQLiteStudentRepository(settings.database_path),source_root=root/'sources',region_crop_root=root/'regions',autonomy_planner_client=client,**experimental_tutoring_configuration('v4')['runtime_flags'])
 for _,id,_,role in ACTORS:app.state.student_repository.save_account(Account(id=id,role=AccountRole(role)))
 install_controls(app,clock,runtime_name='synthetic-model-backed-v4')
 return app
