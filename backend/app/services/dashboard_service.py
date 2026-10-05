# backend/app/services/dashboard_service.py
"""
Role-specific dashboards, built from live data.

Every role gets the same response shape (kpis, queues, charts, activity) but
different content, because each role has a different job:

  Lab Head ........ signatures waiting, lab health, staff, calibration
  Technical Mgr ... what needs review/signature, calibration, who is authorised
  Quality Mgr ..... calibration schedule, returned work, audit activity
  Reviewer ........ work waiting to be checked
  Signatory ....... reports waiting for a signature
  Tester .......... their own sessions, returned work, instruments ready to test
  Assistant ....... open sessions that need readings
  Records ......... instruments received / waiting to be allocated
  Custodian ....... reference weights and calibration status
  Auditor ......... read-only overview of the lab and its audit trail
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog
from backend.app.models.instrument import Instrument
from backend.app.models.report import Report
from backend.app.models.test_equipment import TestEquipment
from backend.app.models.test_observation import TestObservation
from backend.app.models.test_session import TestSession
from backend.app.models.test_session_test import TestSessionTest
from backend.app.models.user import User
from backend.app.services import permissions as perm

CALIBRATION_WARNING_DAYS = 30
QUEUE_LIMIT = 8


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def _utc(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def _iso(value):
    v = _utc(value)
    return v.isoformat().replace("+00:00", "Z") if v else None


def _name(user: User | None) -> str | None:
    if not user:
        return None
    return " ".join(p for p in (user.first_name, user.last_name) if p) or user.email


def _kpi(key, label, value, tone="default", suffix="", href=None):
    return {"key": key, "label": label, "value": value, "tone": tone,
            "suffix": suffix, "href": href}


def _queue(key, title, empty, items, href=None):
    return {"key": key, "title": title, "empty": empty, "items": items[:QUEUE_LIMIT],
            "total": len(items), "href": href}


class Context:
    """Everything about the lab loaded once, then sliced per role."""

    def __init__(self, db: Session, user: User):
        self.db, self.user = db, user
        lab = user.laboratory_id
        self.now = datetime.now(timezone.utc)
        self.today = self.now.date()

        self.users = {u.user_id: u for u in db.query(User).filter(User.laboratory_id == lab).all()}
        self.instruments = {i.instrument_id: i for i in db.query(Instrument).filter(Instrument.laboratory_id == lab).all()}
        self.equipment = db.query(TestEquipment).filter(TestEquipment.laboratory_id == lab).all()

        all_sessions = db.query(TestSession).filter(TestSession.laboratory_id == lab).all()
        self.all_sessions = all_sessions
        # What this user's role is allowed to see.
        self.sessions = [s for s in all_sessions if perm.session_visible_to(user, s)]
        ids = [s.test_session_id for s in self.sessions]

        self.reports: dict = {}
        if ids:
            for r in (db.query(Report).filter(Report.test_session_id.in_(ids))
                      .order_by(Report.generated_at.asc()).all()):
                self.reports[r.test_session_id] = r   # ends up as the latest

        self.test_results: Counter = Counter()
        if ids:
            rows = (db.query(TestSessionTest.applicability_status, TestSessionTest.result, func.count())
                    .filter(TestSessionTest.test_session_id.in_(ids))
                    .group_by(TestSessionTest.applicability_status, TestSessionTest.result).all())
            for applic, result, n in rows:
                if applic == "NOT_APPLICABLE":
                    self.test_results["N/A"] += n
                elif result in ("PASS", "FAIL"):
                    self.test_results[result] += n

    # ---- session helpers ----
    def by_status(self, *statuses):
        return [s for s in self.sessions if s.status in statuses]

    def pending_signature(self):
        return [s for s in self.sessions
                if s.status == "UNDER REVIEW"
                and getattr(self.reports.get(s.test_session_id), "report_status", None) == "PENDING_APPROVAL"]

    def instrument_label(self, s) -> str:
        i = self.instruments.get(s.instrument_id)
        if not i:
            return "Instrument"
        return " ".join(p for p in (i.manufacturer, i.model) if p) or i.instrument_code or "Instrument"

    def session_item(self, s, badge=None, note=None):
        report = self.reports.get(s.test_session_id)
        return {
            "id": str(s.test_session_id),
            "title": s.session_number or str(s.test_session_id)[:8],
            "subtitle": self.instrument_label(s),
            "meta": _name(self.users.get(s.tester_id)),
            "status": s.status,
            "result": s.overall_result,
            "badge": badge or s.status,
            "note": note,
            "report_status": getattr(report, "report_status", None),
            "href": f"/app/test-sessions/{s.test_session_id}",
            "at": _iso(getattr(s, "updated_at", None) or getattr(s, "created_at", None)),
        }

    # ---- equipment helpers ----
    def calibration_bucket(self, e) -> str:
        due = e.calibration_due_date
        if due is None:
            return "unknown"
        d = due.date() if isinstance(due, datetime) else due
        if d < self.today:
            return "overdue"
        if d <= self.today + timedelta(days=CALIBRATION_WARNING_DAYS):
            return "due_soon"
        return "valid"

    def equipment_item(self, e):
        bucket = self.calibration_bucket(e)
        due = e.calibration_due_date
        d = due.date() if isinstance(due, datetime) else due
        days = (d - self.today).days if d else None
        return {
            "id": str(e.equipment_id),
            "title": e.equipment_code or e.serial_number or "Equipment",
            "subtitle": e.equipment_name,
            "meta": f"Calibration due {d.isoformat()}" if d else "No calibration date",
            "badge": ("OVERDUE" if bucket == "overdue" else "DUE SOON" if bucket == "due_soon" else "VALID"),
            "note": (f"{abs(days)} day(s) overdue" if days is not None and days < 0
                     else f"{days} day(s) left" if days is not None else None),
            "href": "/app/equipment",
        }

    def equipment_by_bucket(self):
        out = defaultdict(list)
        for e in self.equipment:
            out[self.calibration_bucket(e)].append(e)
        return out

    # ---- charts ----
    def monthly(self, months=6):
        first = (self.today.replace(day=1))
        labels = []
        y, m = first.year, first.month
        for _ in range(months):
            labels.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        labels.reverse()
        counts = Counter((_utc(s.created_at).year, _utc(s.created_at).month)
                         for s in self.sessions if s.created_at)
        return [{"month": date(y, m, 1).strftime("%b"), "tests": counts.get((y, m), 0)} for y, m in labels]

    def results_chart(self):
        return [{"name": k, "value": self.test_results.get(k, 0)} for k in ("PASS", "FAIL", "N/A")]

    def pipeline(self):
        c = Counter(s.status for s in self.sessions)
        return [{"status": st, "count": c.get(st, 0)} for st in
                ("DRAFT", "IN PROGRESS", "SUBMITTED", "UNDER REVIEW", "APPROVED", "REJECTED")]

    def pass_rate(self):
        done = [s for s in self.sessions if s.status in ("SUBMITTED", "UNDER REVIEW", "APPROVED")
                and s.overall_result in ("PASS", "FAIL")]
        if not done:
            return None
        return round(100 * sum(1 for s in done if s.overall_result == "PASS") / len(done))

    def approved_this_month(self):
        return sum(1 for r in self.reports.values()
                   if r.report_status == "APPROVED" and r.approved_at
                   and _utc(r.approved_at).year == self.today.year
                   and _utc(r.approved_at).month == self.today.month)

    def activity(self, limit=8, days=None, user_only=False):
        q = self.db.query(AuditLog).filter(AuditLog.laboratory_id == self.user.laboratory_id,
                                           AuditLog.action.notin_(["DOWNLOAD_REPORT", "LOGIN"]))
        if days:
            q = q.filter(AuditLog.timestamp >= self.now - timedelta(days=days))
        rows = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        return [{
            "action": r.action, "entity_type": r.entity_type, "remarks": r.remarks,
            "by": _name(self.users.get(r.user_id)),
            "by_role": perm.label_for(getattr(self.users.get(r.user_id), "role", None)),
            "at": _iso(r.timestamp),
        } for r in rows]

    def audit_count(self, days):
        return (self.db.query(func.count(AuditLog.audit_id))
                .filter(AuditLog.laboratory_id == self.user.laboratory_id,
                        AuditLog.timestamp >= self.now - timedelta(days=days)).scalar() or 0)


# --------------------------------------------------------------------------
# one builder per role
# --------------------------------------------------------------------------
def _lab_head(c: Context):
    sign = c.pending_signature()
    cal = c.equipment_by_bucket()
    staff = [u for u in c.users.values() if u.status == "ACTIVE"]
    return dict(
        headline="Laboratory overview",
        hint="Reports waiting for your signature, the health of the lab and your team.",
        kpis=[
            _kpi("sign", "Awaiting your signature", len(sign), "warn" if sign else "default", href="/app/test-sessions"),
            _kpi("sessions", "Test sessions", len(c.sessions), href="/app/test-sessions"),
            _kpi("pass", "Pass rate", c.pass_rate() if c.pass_rate() is not None else 0, suffix="%"),
            _kpi("approved", "Reports approved this month", c.approved_this_month(), "good", href="/app/reports"),
            _kpi("staff", "Active staff", len(staff), href="/app/users"),
            _kpi("cal", "Calibration overdue", len(cal["overdue"]), "bad" if cal["overdue"] else "default", href="/app/equipment"),
        ],
        queues=[
            _queue("sign", "Awaiting your signature", "Nothing is waiting for a signature.",
                   [c.session_item(s, "READY TO SIGN") for s in sign]),
            _queue("cal", "Calibration needing attention", "All equipment calibrations are in date.",
                   [c.equipment_item(e) for e in cal["overdue"] + cal["due_soon"]], "/app/equipment"),
        ],
        charts=dict(monthly=c.monthly(), results=c.results_chart(), pipeline=c.pipeline()),
        activity=c.activity(),
    )


def _technical_manager(c: Context):
    review = c.by_status("SUBMITTED")
    sign = c.pending_signature()
    cal = c.equipment_by_bucket()
    testers = [u for u in c.users.values() if u.role in ("TESTER",) and u.status == "ACTIVE"]
    unscoped = [u for u in testers if not (u.authorization_scope or {}).get("test_codes")]
    fails = c.test_results.get("FAIL", 0)
    total = c.test_results.get("PASS", 0) + fails
    return dict(
        headline="Technical oversight",
        hint="Work to check, equipment calibration and who is authorised for which tests.",
        kpis=[
            _kpi("review", "Waiting for review", len(review), "warn" if review else "default", href="/app/test-sessions"),
            _kpi("sign", "Awaiting signature", len(sign), href="/app/test-sessions"),
            _kpi("cal", "Calibration overdue", len(cal["overdue"]), "bad" if cal["overdue"] else "default", href="/app/equipment"),
            _kpi("fail", "Test failure rate", round(100 * fails / total) if total else 0, suffix="%"),
            _kpi("auth", "Testers without a test list", len(unscoped), "warn" if unscoped else "default", href="/app/users"),
        ],
        queues=[
            _queue("review", "Waiting for review", "No submitted work to review.",
                   [c.session_item(s, "SUBMITTED") for s in review]),
            _queue("sign", "Awaiting signature", "Nothing is waiting for a signature.",
                   [c.session_item(s, "READY TO SIGN") for s in sign]),
            _queue("auth", "Testers authorised for all tests", "Every tester has an authorisation list.",
                   [{"id": str(u.user_id), "title": perm.label_for(u.role), "subtitle": _name(u),
                     "badge": "NO LIST", "note": "Authorised for every test", "href": "/app/users"}
                    for u in unscoped], "/app/users"),
        ],
        charts=dict(monthly=c.monthly(), results=c.results_chart(), pipeline=c.pipeline()),
        activity=[],
    )


def _quality_manager(c: Context):
    cal = c.equipment_by_bucket()
    returned = c.by_status("REJECTED")
    return dict(
        headline="Quality system",
        hint="Calibration schedule, returned work and audit activity. You stay independent of testing.",
        kpis=[
            _kpi("overdue", "Calibration overdue", len(cal["overdue"]), "bad" if cal["overdue"] else "default", href="/app/equipment"),
            _kpi("soon", f"Due in {CALIBRATION_WARNING_DAYS} days", len(cal["due_soon"]), "warn" if cal["due_soon"] else "default", href="/app/equipment"),
            _kpi("returned", "Returned / rejected work", len(returned), "warn" if returned else "default", href="/app/test-sessions"),
            _kpi("audit", "Audit events (7 days)", c.audit_count(7), href="/app/audit-log"),
            _kpi("pass", "Pass rate", c.pass_rate() if c.pass_rate() is not None else 0, suffix="%"),
        ],
        queues=[
            _queue("cal", "Calibration schedule", "All equipment calibrations are in date.",
                   [c.equipment_item(e) for e in cal["overdue"] + cal["due_soon"]], "/app/equipment"),
            _queue("returned", "Returned or rejected sessions", "No sessions have been returned.",
                   [c.session_item(s, "RETURNED") for s in returned]),
        ],
        charts=dict(results=c.results_chart(), pipeline=c.pipeline()),
        activity=c.activity(limit=10),
    )


def _reviewer(c: Context):
    me = c.user.user_id
    ready = [s for s in c.by_status("SUBMITTED")]
    mine = [s for s in c.by_status("UNDER REVIEW") if perm.same_user(s.reviewer_id, me)]
    forwarded = [s for s in mine if getattr(c.reports.get(s.test_session_id), "report_status", None) == "PENDING_APPROVAL"]
    in_check = [s for s in mine if s not in forwarded]
    returned = [s for s in c.by_status("REJECTED") if perm.same_user(s.reviewer_id, me)]
    return dict(
        headline="Review queue",
        hint="Check each tester's work and report. Return it for correction or forward it for signature.",
        kpis=[
            _kpi("ready", "Ready to review", len(ready), "warn" if ready else "default", href="/app/test-sessions"),
            _kpi("checking", "In my review", len(in_check), href="/app/test-sessions"),
            _kpi("forwarded", "Forwarded for signature", len(forwarded)),
            _kpi("returned", "Returned by me", len(returned)),
        ],
        queues=[
            _queue("ready", "Ready to review", "Nothing has been submitted for review.",
                   [c.session_item(s, "SUBMITTED") for s in ready]),
            _queue("checking", "In my review", "You have no review in progress.",
                   [c.session_item(s, "IN REVIEW") for s in in_check]),
            _queue("forwarded", "Waiting for signature", "No forwarded reports.",
                   [c.session_item(s, "FORWARDED") for s in forwarded]),
        ],
        charts=None, activity=[],
    )


def _signatory(c: Context):
    me = c.user.user_id
    sign = c.pending_signature()
    signed = [r for r in c.reports.values() if perm.same_user(r.approved_by, me) and r.report_status == "APPROVED"]
    sid = {s.test_session_id: s for s in c.sessions}
    month_signed = [r for r in signed if r.approved_at and _utc(r.approved_at).month == c.today.month
                    and _utc(r.approved_at).year == c.today.year]
    return dict(
        headline="Signature queue",
        hint="Reports a reviewer has checked and forwarded to you. Signing makes them final.",
        kpis=[
            _kpi("sign", "Awaiting my signature", len(sign), "warn" if sign else "default", href="/app/test-sessions"),
            _kpi("signed", "Signed by me this month", len(month_signed), "good"),
            _kpi("signed_all", "Signed by me, all time", len(signed)),
        ],
        queues=[
            _queue("sign", "Awaiting my signature", "No reports are waiting for you.",
                   [c.session_item(s, "READY TO SIGN") for s in sign]),
            _queue("signed", "Recently signed by me", "You have not signed any report yet.",
                   [c.session_item(sid[r.test_session_id], "SIGNED") for r in
                    sorted(signed, key=lambda r: _utc(r.approved_at) or c.now, reverse=True)
                    if r.test_session_id in sid]),
        ],
        charts=None, activity=[],
    )


def _tester(c: Context):
    mine = c.sessions   # already limited to this tester's own
    open_ = [s for s in mine if s.status in ("DRAFT", "IN PROGRESS")]
    returned = [s for s in mine if s.status == "REJECTED"]
    with_reviewer = [s for s in mine if s.status in ("SUBMITTED", "UNDER REVIEW")]
    used = {s.instrument_id for s in c.all_sessions}
    ready = [i for i in c.instruments.values() if (i.status or "ACTIVE").upper() == "ACTIVE" and i.instrument_id not in used]
    attention = returned + open_
    return dict(
        headline="My testing",
        hint="Your sessions, work sent back for correction, and instruments waiting to be tested.",
        kpis=[
            _kpi("returned", "Returned for correction", len(returned), "bad" if returned else "default", href="/app/test-sessions"),
            _kpi("open", "In progress", len(open_), href="/app/test-sessions"),
            _kpi("review", "With reviewer", len(with_reviewer)),
            _kpi("passed", "Tests passed", c.test_results.get("PASS", 0), "good"),
            _kpi("failed", "Tests failed", c.test_results.get("FAIL", 0), "bad" if c.test_results.get("FAIL") else "default"),
        ],
        queues=[
            _queue("attention", "Needs your attention", "Nothing needs your attention right now.",
                   [c.session_item(s, "RETURNED" if s.status == "REJECTED" else s.status) for s in attention]),
            _queue("with_reviewer", "Submitted, with the reviewer", "Nothing is waiting on a reviewer.",
                   [c.session_item(s) for s in with_reviewer]),
            _queue("ready", "Instruments ready to test", "Every instrument already has a session.",
                   [{"id": str(i.instrument_id), "title": i.instrument_code or "Instrument",
                     "subtitle": " ".join(p for p in (i.manufacturer, i.model) if p) or i.instrument_code,
                     "badge": "RECEIVED", "href": "/app/instruments"}
                    for i in ready], "/app/instruments"),
        ],
        charts=dict(results=c.results_chart(), monthly=c.monthly()),
        activity=[],
    )


def _assistant(c: Context):
    me = c.user.user_id
    open_ = c.by_status("DRAFT", "IN PROGRESS")
    start = c.now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = (c.db.query(func.count(TestObservation.observation_id))
             .filter(TestObservation.entered_by == me, TestObservation.observed_at >= start).scalar()) or 0
    total = c.db.query(func.count(TestObservation.observation_id)).filter(TestObservation.entered_by == me).scalar() or 0
    return dict(
        headline="Bench work",
        hint="Sessions that need readings. You enter data; the tester calculates and submits.",
        kpis=[
            _kpi("open", "Open sessions", len(open_), href="/app/test-sessions"),
            _kpi("today", "Readings entered today", today, "good"),
            _kpi("total", "Readings entered, all time", total),
        ],
        queues=[
            _queue("open", "Sessions needing readings", "No open sessions need data.",
                   [c.session_item(s) for s in open_]),
        ],
        charts=None, activity=[],
    )


def _records(c: Context):
    used = {s.instrument_id for s in c.all_sessions}
    waiting = [i for i in c.instruments.values() if (i.status or "ACTIVE").upper() == "ACTIVE" and i.instrument_id not in used]
    this_month = [i for i in c.instruments.values() if i.created_at and _utc(i.created_at).month == c.today.month and _utc(i.created_at).year == c.today.year]
    inactive = [i for i in c.instruments.values() if (i.status or "").upper() == "INACTIVE"]

    def item(i, badge):
        return {"id": str(i.instrument_id), "title": i.instrument_code or "Instrument",
                "subtitle": " ".join(p for p in (i.manufacturer, i.model) if p) or i.instrument_code,
                "meta": i.serial_number, "badge": badge, "href": "/app/instruments"}

    recent = sorted(c.instruments.values(), key=lambda i: _utc(i.created_at) or c.now, reverse=True)
    return dict(
        headline="Receiving & records",
        hint="Instruments received from applicants and their records.",
        kpis=[
            _kpi("total", "Instruments on record", len(c.instruments), href="/app/instruments"),
            _kpi("month", "Received this month", len(this_month), "good"),
            _kpi("waiting", "Waiting for a tester", len(waiting), "warn" if waiting else "default", href="/app/instruments"),
            _kpi("inactive", "Retired (inactive)", len(inactive)),
        ],
        queues=[
            _queue("waiting", "Received, not yet tested", "Every instrument has been taken up for testing.",
                   [item(i, "RECEIVED") for i in waiting], "/app/instruments"),
            _queue("recent", "Recently recorded", "No instruments recorded yet.",
                   [item(i, (i.status or "ACTIVE").upper()) for i in recent]),
        ],
        charts=None, activity=[],
    )


def _custodian(c: Context):
    cal = c.equipment_by_bucket()
    return dict(
        headline="Reference standards",
        hint="Reference weights and test equipment, and when each is due for calibration.",
        kpis=[
            _kpi("total", "Equipment on record", len(c.equipment), href="/app/equipment"),
            _kpi("overdue", "Calibration overdue", len(cal["overdue"]), "bad" if cal["overdue"] else "default", href="/app/equipment"),
            _kpi("soon", f"Due in {CALIBRATION_WARNING_DAYS} days", len(cal["due_soon"]), "warn" if cal["due_soon"] else "default"),
            _kpi("valid", "In calibration", len(cal["valid"]), "good"),
        ],
        queues=[
            _queue("overdue", "Calibration overdue", "Nothing is overdue.",
                   [c.equipment_item(e) for e in cal["overdue"]], "/app/equipment"),
            _queue("soon", "Due soon", "Nothing falls due in the next 30 days.",
                   [c.equipment_item(e) for e in cal["due_soon"]], "/app/equipment"),
        ],
        charts=None, activity=[],
    )


def _auditor(c: Context):
    approved = [r for r in c.reports.values() if r.report_status == "APPROVED"]
    sid = {s.test_session_id: s for s in c.sessions}
    return dict(
        headline="Audit overview",
        hint="A read-only view of the laboratory and its audit trail.",
        kpis=[
            _kpi("sessions", "Test sessions", len(c.sessions), href="/app/test-sessions"),
            _kpi("approved", "Approved reports", len(approved), "good", href="/app/reports"),
            _kpi("pass", "Pass rate", c.pass_rate() if c.pass_rate() is not None else 0, suffix="%"),
            _kpi("audit", "Audit events (30 days)", c.audit_count(30), href="/app/audit-log"),
        ],
        queues=[
            _queue("approved", "Recently approved reports", "No reports have been approved yet.",
                   [c.session_item(sid[r.test_session_id], "APPROVED") for r in
                    sorted(approved, key=lambda r: _utc(r.approved_at) or c.now, reverse=True)
                    if r.test_session_id in sid]),
        ],
        charts=dict(monthly=c.monthly(), results=c.results_chart(), pipeline=c.pipeline()),
        activity=c.activity(limit=10),
    )


BUILDERS = {
    "LAB_ADMIN": _lab_head,
    "TECHNICAL_MANAGER": _technical_manager,
    "QUALITY_MANAGER": _quality_manager,
    "REVIEWER": _reviewer,
    "APPROVER": _signatory,
    "TESTER": _tester,
    "ASSISTANT": _assistant,
    "RECORDS_OFFICER": _records,
    "STANDARDS_CUSTODIAN": _custodian,
    "AUDITOR": _auditor,
}


def build_dashboard(db: Session, user: User) -> dict:
    ctx = Context(db, user)
    builder = BUILDERS.get((user.role or "").upper(), _auditor)
    data = builder(ctx)
    data.update(
        role=user.role,
        role_label=perm.label_for(user.role),
        user_name=_name(user),
        laboratory_id=str(user.laboratory_id),
    )
    return data
