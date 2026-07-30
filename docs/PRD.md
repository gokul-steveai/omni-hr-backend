# Product Requirements Document (PRD): OmniHR Enterprise System

## 1. Executive Summary & Vision
**OmniHR** is a highly scalable, enterprise-grade Human Resource Management System (HRMS) designed for modern organizations. It combines a lightning-fast Next.js frontend with a robust FastAPI backend, featuring advanced role-based access control (RBAC), automated payroll processing, an extensive leave management suite, and a stateful conversational AI assistant powered by LLM tool-calling.

## 2. Target User Personas & RBAC Permissions Matrix
* **Super Admin**: Full system access, configuration of global policies, payroll execution override, audit log monitoring, and user role assignment.
* **HR Manager**: Employee lifecycle management, leave policy approvals, payroll generation, company holiday configuration, and team analytics dashboard access.
* **Department Lead / Manager**: Team calendar oversight, tier-1 leave request approvals/rejections, and team performance tracking.
* **Regular Employee**: Self-service profile management, leave application, payslip downloads, and conversational AI interaction for quick HR queries.

## 3. Core Functional Modules

### 3.1 Role-Based Access Control & Authentication
* **Authentication & Session Hygiene**:
  * Secure JWT-based authentication with OAuth 2.0 support and single-use refresh token rotation.
  * Multi-tier permission matrix (`users`, `roles`, `permissions`, `role_permissions`).
* **Security & Access Rules**:
  * **Token Revocation**: Blacklist revoked tokens upon logout/password reset. Expire refresh tokens after 7 days; force re-authentication on role changes.
  * **Manager Escalation**: Reassign pending leave requests automatically to HR Managers or designated leads if a Department Lead is deactivated.
  * **Data Isolation**: Scope all employee queries and AI chatbot tool executions strictly to the authenticated caller's identity.

### 3.2 Employee Directory & Profile Management
* **Directory**: Searchable, filterable directory with pagination, department/designation facets, and organizational hierarchy visualization.
* **Self-Service Profile**: Employees can update personal details, emergency contacts, and banking information.
* **Verification & Audit**: Critical banking edits log high-priority audit events before taking effect.

### 3.3 Leave Management & Accrual Suite
* **Leave Types & Allocations**: Configurable leave types (Casual, Sick, Earned, Unpaid/LWS, Comp-Off, Maternity/Paternity) with automated yearly/monthly balance accruals.
* **Multi-Tier Approvals**: Direct Manager (Tier-1) approval followed by HR Manager (Tier-2) sign-off for leaves > 3 days.
* **Auto Leave Approval Engine**: Single-day sick leaves or casual leaves requested N days in advance auto-approve if balance is sufficient. Inactive requests (> 5 business days) escalate to HR.
* **Edge Cases & Business Rules**:
  * **Unsanctioned Absences (LWS / LOP)**: Unapproved absences or rejected leave days automatically register as LWS/LOP, triggering payroll deductions.
  * **Compensatory Off (Comp-Off)**: Weekend/Holiday work logs generate redeemable Comp-Off credits subject to manager verification.
  * **Half-Day Support**: Support First-Half and Second-Half leave requests (0.5 days).
  * **Holiday & Weekend Exclusions**: Working day calculations automatically exclude weekends and official company holidays.
  * **Overlapping Leave Check**: Backend rejects duplicate or overlapping leave submissions for the same employee across the same timeframe.
  * **Balance Restoration**: Approved leaves cancelled *before* the start date automatically restore quota balances and log audit entries.
  * **Year-End Carry-Forward & Encashment**: Batch processing to cap carry-forward days (e.g. max 10 days) and compute encashment payouts for unused Earned Leave.
  * **Probation Restrictions**: Restrict leave quotas during employee probation periods or active notice periods.

### 3.4 Daily Timesheets & Work Status Tracking
* **Daily Work Status Register**: Employees log daily activity summaries, project tasks, hours spent, and standup status updates.
* **Time Tracking & Billability**: Log hours against projects/tasks with billable vs. non-billable classification.
* **Weekly Approval Workflow**: Submit weekly timesheets to Department Leads for review; locked upon approval.
* **Attendance Integration**: Minimum daily required logged hours (e.g. 8 hrs) cross-referenced against attendance clock-ins.

### 3.5 Payroll Automation & Salary Tracking
* **Salary Structures**: Modular configuration of base pay, housing allowance, transportation, medical deductions, and tax withholdings.
* **Payslip Generation**: Automated PDF payslip generation securely stored with cryptographically signed, expiring download URLs.
* **Edge Cases & Business Rules**:
  * **Loss of Pay (LOP) Integration**: Monthly payroll dynamically deducts unpaid leave days (`LOP = (Base Salary / Total Working Days in Month) * LOP Days`).
  * **Prorated Salary**: Prorate base pay and allowances based on exact active days in the joining/resignation month.
  * **Pay Run Locking & Concurrency**: Lock pay runs upon completion. Block concurrent pay runs for the same department/month.

### 3.6 Conversational AI Assistant (OmniBot)
* **LLM Tool-Calling Architecture**: Stateful AI agent executing structured actions (`apply_leave`, `get_leave_balance`, `fetch_payslip`) via dynamic tool decorators.
* **Caller Context Enforcement**: AI tools automatically extract caller identity from JWT token contexts to prevent unauthorized data access.