# Roles and permissions

The roles mirror how an ISO/IEC 17025 testing laboratory (for example a
government Regional Reference Standards Laboratory) is actually staffed.
Designations differ from lab to lab, so a person's **designation** is free text
(e.g. "Assistant Director"), while their **role** decides what the software lets
them do.

Code: `backend/app/services/permissions.py` is the single source of truth. The
backend enforces it on every request; the frontend reads the same catalogue
(`GET /api/users/roles`, and `capabilities` on `GET /api/users/me`) so what a
person sees matches what they are allowed to do.

## The roles

| Level | Role (code) | Real job | Dashboard focus |
|---|---|---|---|
| 1 | **Lab Head / In-charge** (`LAB_ADMIN`) | Answerable for the lab. Manages staff, signs off final reports. Does not test. | Reports awaiting signature, lab health, staff, calibration |
| 2 | **Technical Manager** (`TECHNICAL_MANAGER`) | Test methods, equipment, tester competence. May review and sign. | Work to review/sign, calibration, testers' authorisation |
| 2 | **Quality Manager** (`QUALITY_MANAGER`) | Quality system, audits, calibration schedule. Independent of testing: cannot test, review or sign. | Calibration schedule, returned work, audit activity |
| 3 | **Reviewer** (`REVIEWER`) | Checks the tester's work and report; returns it or forwards it for signature. | Review queue |
| 3 | **Authorised Signatory** (`APPROVER`) | Signs the reviewed report: approve or reject. | Signature queue |
| 4 | **Senior Tester / Evaluator** (`TESTER`) | Plans and runs tests, analyses results, drafts the report. | My sessions, returned work, instruments ready to test |
| 5 | **Technician / Lab Assistant** (`ASSISTANT`) | Sets up, places weights, takes readings, enters data under supervision. | Open sessions needing readings |
| Support | **Receiving / Records Officer** (`RECORDS_OFFICER`) | Receives instruments and keeps their records. | Instruments received / waiting for a tester |
| Support | **Standards Custodian** (`STANDARDS_CUSTODIAN`) | Reference weights and their calibration. | Calibration due / overdue |
| External | **Auditor** (`AUDITOR`) | Assessor (e.g. NABL) or viewer. Read-only, including the audit trail. | Read-only overview |

Outside the lab, and **not** modelled as logins: the *Applicant* (manufacturer)
who submits the instrument, the *Director / Issuing Authority* who issues the
Certificate of Approval after the lab's signed report, and the public, who use
the open `/verify` page.

The Lab Head account is created when the laboratory registers; the Lab Head
adds everyone else (Staff & Roles page) and can change a role or deactivate an
account at any time.

## The workflow

```
DRAFT -> IN PROGRESS -> SUBMITTED -> UNDER REVIEW -> report PENDING_APPROVAL -> APPROVED
            ^   ^           |              |                    |
            |   +-- recall -+              v                    v
            +-------- rework --------- REJECTED  <---------------+
```

| Step | Who | Notes |
|---|---|---|
| Start testing / Submit / Recall / Rework | the session's own **tester** | Submitting needs every applicable test to have a calculated result |
| Start review | **Reviewer** (or Lab Head / Technical Manager) | Maker-checker applies |
| Return for correction | reviewer | A reason is required; the tester sees it |
| Forward for approval | reviewer | The report must exist |
| Approve and sign / Reject | **Authorised Signatory**, Lab Head or Technical Manager | The report must have been forwarded; rejecting needs a reason |

`APPROVED` can only be reached by signing the report; the status endpoint
refuses it. Approved sessions are final and locked.

## Maker-checker

> Whoever tested a session cannot review or sign it.

"Tested" means the session's tester **and anyone who entered an observation on
it**. The rule is checked on every review, forward and sign step, so it holds
even if someone's role is changed after the testing. The session page explains
it when it blocks someone ("You took part in testing this session...").

Related guards: data can only change while a session is `DRAFT` or `IN
PROGRESS`; a tester only works on their own sessions; an assistant enters
readings but cannot plan tests, calculate, or submit.

## Who sees what

| Role | Sessions visible in lists |
|---|---|
| Tester | their own |
| Assistant | open sessions (draft / in progress) |
| Reviewer | submitted and under-review work, plus any they reviewed |
| Authorised Signatory | under review / approved / rejected |
| Lab Head, Technical Manager, Quality Manager, Auditor | all |

Roles also only get the screens they work in (Records and Custodian have no
Test Sessions page, for example); opening one by URL shows a clear explanation.

## Test authorisation (ISO 17025 competence)

The Technical Manager (or Lab Head) can list the tests a tester is competent
to run (Staff & Roles -> edit -> "Authorised for these tests"). It is stored in
`users.authorization_scope = {"test_codes": ["WP", "ZR"]}`. Planning or
calculating any other test is refused. No list means authorised for every test.

## Permission matrix

`+` = allowed. Everyone in the lab can read instruments, equipment and (within
the visibility above) sessions.

| Capability | Head | Tech Mgr | Quality | Reviewer | Signatory | Tester | Assistant | Records | Custodian | Auditor |
|---|---|---|---|---|---|---|---|---|---|---|
| Add staff, change roles | + | | | | | | | | | |
| Authorise testers for tests | + | + | | | | | | | | |
| Edit lab profile | + | | | | | | | | | |
| Receive / record instruments | + | + | | | | + | | + | | |
| Delete instruments | + | | | | | | | + | | |
| Reference weights & calibration | + | + | + | | | | | | + | |
| Standards, methods, MPE rules | + | + | | | | | | | | |
| Plan sessions and tests | | | | | | + | | | | |
| Record readings / conditions | | | | | | + | + | | | |
| Run calculations | | | | | | + | | | | |
| Submit for review | | | | | | + | | | | |
| Review work and report | + | + | | + | | | | | | |
| Approve / reject (sign) | + | + | | | + | | | | | |
| Draft / regenerate reports | + | + | | + | | + | | | | |
| Read the audit trail | + | | + | | | | | | | + |

(The Lab Head and Technical Manager can review and sign only sessions they did
not take part in testing; by role they do not test.)

## API added or changed

- `GET /api/users/roles`: the role catalogue.
- `GET /api/users/me`: now includes `role_label`, `role_level`, `capabilities`.
- `PATCH /api/users/{id}`: Lab Head changes role / status / designation; Technical Manager
  sets `authorization_scope` only. You cannot change your own role, nor deactivate the Lab Head.
- `GET /api/dashboard`: the dashboard for the signed-in role, built from live data.
- `GET /api/test-sessions/{id}/workflow`: what this user can do on the session right now
  (and why an action is blocked), plus the session's history.
- `PATCH /api/test-sessions/{id}/status`: body takes an optional `reason` (required when returning for correction).
- `PATCH /api/test-sessions/{id}/approve-report?action=REJECT&reason=...`: rejecting needs a reason.
- Calculation, observation, environmental-condition, equipment-usage, instrument, equipment,
  standards, report and audit-log endpoints now check the role's capability.

## Changing the rules

To add a role or change what one may do, edit `ROLES` in
`backend/app/services/permissions.py` (and, for the interface, the label and
tone in `frontend/src/lib/roles.js`). To change the workflow, edit
`backend/app/services/workflow_rules.py`. The tests in
`backend/tests/roles/` describe the intended behaviour.

## Demo

`python -m backend.seed_demo_lab` creates one login per role (password
`demo1234`) with sessions at every stage; the login page has a role picker.
