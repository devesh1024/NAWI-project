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

Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully")