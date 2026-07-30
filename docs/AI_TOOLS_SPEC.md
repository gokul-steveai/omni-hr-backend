# AI Agent Tool-Calling Specification (OmniBot)

## 1. Architecture Overview
The conversational AI agent is implemented using **LangGraph** on the FastAPI backend. It maintains multi-turn conversational state using Redis/PostgreSQL checkpointers and interacts with backend services strictly through defined **Function Tools**. The LLM is prohibited from guessing data or executing direct raw SQL; all interactions must pass through validated service functions.

## 2. Tool Definitions

### Tool 1: `get_leave_balance`
*   **Description:** Retrieves the current leave allocation and remaining balance for a specific user across all leave types.
*   **Parameters:**
    *   `user_id` (string, UUID): The unique identifier of the user (Validated against authenticated JWT session).
    *   `year` (integer, optional): The target year (defaults to current year).
*   **Return Schema:** JSON object containing leave types, allocated quotas, used days, and remaining balance.

### Tool 2: `apply_leave_request`
*   **Description:** Submits a new leave request on behalf of the user based on natural language date extraction.
*   **Parameters:**
    *   `user_id` (string, UUID): The user requesting leave.
    *   `leave_type_enum` (string): 'casual', 'sick', 'earned', or 'unpaid'.
    *   `start_date` (string, ISO 8601 Date YYYY-MM-DD): Start date of leave.
    *   `end_date` (string, ISO 8601 Date YYYY-MM-DD): End date of leave.
    *   `half_day_type` (string, optional): 'none' (default), 'first_half', or 'second_half'.
    *   `reason` (string): Description or reason for leave.
*   **Return Schema:** Confirmation object with `request_id`, status ('pending'), calculated `total_days` (excluding weekends and public holidays), and remaining balance preview.

### Tool 3: `update_user_profile`
*   **Description:** Updates permissible employee profile fields (e.g., phone number, emergency contact, address).
*   **Parameters:**
    *   `user_id` (string, UUID): The user whose profile is being updated.
    *   `field_name` (string): Field to update (`phone_number`, `emergency_contact`, `address`).
    *   `new_value` (string): The new value to store.
*   **Return Schema:** Success confirmation and updated profile snippet.

### Tool 4: `get_company_holidays`
*   **Description:** Retrieves the official company holiday calendar for the current or specified year.
*   **Parameters:**
    *   `year` (integer, optional): Target year.
*   **Return Schema:** List of holiday objects with dates, holiday names, and optional status.

## 3. Safety Guardrails & Validation
*   **Authorization Enforcement:** The `user_id` parameter passed to tools MUST match the authenticated user's ID extracted from the bearer token. Standard employees cannot query or update other employees' records.
*   **Self-Approval Prevention:** The AI tool must reject any attempt to auto-approve leave requests; all requests default to `pending` status requiring manager intervention.
*   **Date & Overlap Validation:** Start dates cannot precede the current date unless approved by HR policy override. Submissions must check for weekend/holiday exclusions and overlapping existing leaves.
*   **Ambiguous Date Resolution:** When natural language date references are ambiguous (e.g., "leave for 3 days next week"), the bot MUST prompt for confirmation of exact start and end dates before executing `apply_leave_request`.