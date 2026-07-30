# OmniHR Enterprise System - Backend Project Overview

OmniHR is a high-performance, enterprise-grade Human Resource Management System (HRMS) & Work Operating System designed for multi-entity, global organizations.

---

## 1. Core Business Modules & Capabilities

- **Auth & RBAC Identity Engine**: Single-use JWT refresh token rotation, bcrypt security, and strict Role-Based Access Control (`Super Admin`, `HR Manager`, `Department Lead`, `Employee`).
- **Leave Management & Accrual Engine**: Multi-tier approval workflows, automated accruals, holiday/weekend exclusions, half-day leaves, Loss of Pay (LOP) deductions, and year-end encashments.
- **Timesheet & Time Tracking Engine**: Daily work status logging, project task allocation, manager approval queues, and overtime calculations.
- **Automated Payroll Engine**: Prorated salary calculations based on attendance and leave deductions, tax deductions, and automated payslip generation.
- **AI Agent Tool Registry**: Dynamic tool-calling interfaces for conversational HR AI assistants.

---

## 2. Business Flow & Domain Lifecycle

```
[ Employee Onboarding ] ──> [ Identity Provisioning ] ──> [ Active Session (JWT) ]
                                                                  │
      ┌───────────────────────────┼───────────────────────────────┤
      ▼                           ▼                               ▼
[ Leave Application ]    [ Timesheet Entry ]            [ Profile Self-Service ]
      │                           │
      ▼                           ▼
[ Manager Approval ]     [ Lead Verification ]
      │                           │
      └───────────────────────────┴───────────────────────────────┐
                                                                  ▼
                                                      [ Payroll Processing & Payslip ]
```
