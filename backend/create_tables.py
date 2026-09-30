# Allow running this file directly from anywhere (`python backend/create_tables.py` from the
# repo root, or `python create_tables.py` from backend/) as well as `python -m backend.create_tables`.
# The app imports as `backend.app...`, so the repo root must be on sys.path.
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.database.connection import Base, engine

from backend.app.models.laboratory import Laboratory
from backend.app.models.user import User
from backend.app.models.instrument import Instrument
from backend.app.models.standard import Standard
from backend.app.models.test_definition import TestDefinition
from backend.app.models.test_applicability_rule import TestApplicabilityRule
from backend.app.models.mpe_rule import MPERule
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.test_observation import TestObservation
from backend.app.models.test_calculation import TestCalculation
from backend.app.models.test_result import TestResult
from backend.app.models.report import Report
from backend.app.models.environmental_condition import EnvironmentalCondition
from backend.app.models.test_equipment import TestEquipment
from backend.app.models.test_equipment_usage import TestEquipmentUsage
from backend.app.models.observation_import import ObservationImport
from backend.app.models.report_version import ReportVersion
from backend.app.models.attachment import Attachment
from backend.app.models.audit_log import AuditLog
from backend.app.models.digital_signature import DigitalSignature

Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully")