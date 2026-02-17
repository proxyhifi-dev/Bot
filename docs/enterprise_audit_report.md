# Enterprise Audit Report — Python Trading Bot

## Scope & Method

This review audits architecture, integration quality, runtime behavior, OAuth flow integrity, and production safety across the current repository implementation. It is a research/audit document (not a refactor diff).

---

## 1) Project Structure Review

### Observed Topology

The repo currently contains **multiple overlapping bot implementations**:

- Primary FastAPI + threaded engine stack (`api/`, `engine/`, `execution/`).
- Legacy synchronous bot script at repository root (`main.py`).
- Separate CLI-oriented bot subtree (`bot/`).
- Additional prototype-like core abstractions (`core/`).

### Structural Weaknesses

1. **Parallel architecture tracks in one runtime repo**
   - `engine/trading_engine.py` is the effective orchestrator for API mode.
   - `main.py` (root) implements a second full loop with different dependencies (`data_provider`, root-level `auth`) and incompatible assumptions.
   - `bot/` has another OAuth manager and adapter style.
   - Result: high drift risk and duplicated bug surface.

2. **Redundant broker/auth implementations**
   - `execution/fyers_adapter.py` has one OAuth/token model.
   - `bot/auth.py` has a second OAuth/token model with different payload contract.
   - This is a direct source of inconsistent behavior across environments and deployments.

3. **Namespace collision and import fragility**
   - In `bot/`, imports are relative-in-practice but written as top-level (`from health import ...`, `from auth import ...`).
   - This is brittle and can import the wrong module when run from different working directories.

4. **Mixed maturity artifacts in production tree**
   - `__pycache__` and runtime logs are tracked in project tree, increasing noise and operational ambiguity.

### Architectural Anti-patterns

- **God-object orchestration**: `TradingEngine` owns auth adapter, market data, risk, strategy, execution, pending-state, threading and lifecycle.
- **Global mutable singleton**: `engine = TradingEngine()` at module import in FastAPI.
- **Runtime side effects during import**: env loading and adapter initialization are effectively triggered during import path.

### Scalability Risks

- Current loop uses polling + synchronous HTTP calls; cannot scale to multi-symbol or low-latency use without significant event-driven redesign.
- No queue-based decoupling between signal generation and execution path.

### Refactoring Direction (high level)

- Keep one canonical runtime (FastAPI + engine) and move others to `legacy/` or separate repos.
- Extract broker auth lifecycle into dedicated `auth/` service with strict interface.
- Introduce dependency-injected runtime container (startup-only initialization).

---

## 2) Authentication Flow Audit (Critical)

### Current Flow (Primary stack)

1. Environment loaded via `load_dotenv()` in adapter import path.
2. `FyersAdapter` reads `FYERS_*` variables in constructor.
3. Token loaded from `FYERS_TOKEN_FILE` if present.
4. Token validated with `GET /api/v3/profile`.
5. If invalid and interactive mode requested, manual login URL shown.
6. User pastes callback URL or auth code.
7. Auth code exchanged at `POST /api/v3/token` using `grant_type=authorization_code` and `appIdHash`.
8. Token saved to local file and chmod 600.

### Breakpoints & Likely Root Causes for Reported Errors

- **503 Service Temporarily Unavailable**
  - Typically broker infra/load or temporary upstream degradation; code retries on 503, so repeated failures imply prolonged upstream outage or wrong base URL host/domain for service state.

- **410 Deprecated Endpoint**
  - Likely from old v2 endpoints or stale URLs used in legacy modules (`bot/` or older scripts), while primary adapter uses v3 paths.

- **401 Unauthorized**
  - Invalid/expired token, wrong `client_id:token` auth header pairing, token from one app/environment used against another base URL.

- **KeyError: access_token**
  - Legacy code expecting token response shape without robust validation; current primary adapter avoids KeyError via `.get()`, but duplicate/older modules may still assume presence.

- **Missing env variables / timing issues**
  - Adapter is constructed eagerly from global engine instance in API module; if environment not loaded prior to import, startup crashes before app boot.

- **Unexpected keyword argument errors**
  - Signature drift between duplicate adapters and callers across `bot/`, root scripts, and `execution/` path.

- **Multiple adapter versions conflict**
  - Confirmed by coexisting implementations with different interfaces and token exchange schemas.

### Security Weaknesses in Auth Path

- Interactive login endpoint exposed via API route can block worker threads waiting on terminal `input()`.
- Token persistence is local file-based only (acceptable for prototype, not institutional production).
- No explicit token expiry metadata lifecycle beyond profile validation check.

### Correct OAuth Lifecycle (Production Pattern)

1. **Startup**: load config once, validate required settings.
2. **Token bootstrap**: read token record (access token + issued/expiry metadata).
3. **Preflight validation**: verify token with profile endpoint.
4. **If invalid**: transition auth state to `NEEDS_LOGIN`; do not block API worker.
5. **Out-of-band login completion**: dedicated callback handler or operator workflow updates token store.
6. **Post-update validation**: activate live broker client only after successful validation.
7. **Runtime**: periodic token health monitor + controlled re-auth state machine.

### Sequence Diagram (text)

Operator → Auth Service: request login URL  
Auth Service → Operator: URL with state  
Operator → Fyers: authenticate  
Fyers → Callback endpoint: authorization code  
Auth Service → Fyers token API: code exchange  
Fyers token API → Auth Service: access token  
Auth Service → Secure store: persist token  
Execution Engine → Auth Service: get valid token  
Auth Service → Execution Engine: token/invalid state

---

## 3) API Layer Review (FastAPI)

### Findings

- Engine is created at import time and started at startup hook.
- API routes call engine methods directly; many paths are synchronous and can block.
- `/auth/login` takes a process-wide lock but then calls interactive terminal input path — incompatible with HTTP server execution model.
- Shared global engine is mutable state across requests + background thread.

### Concurrency / Startup Risks

- Race potential between engine background loop mutating pending signal and simultaneous route actions (mitigated partially by locks, but not comprehensive).
- Startup can fail hard if adapter env checks fail before server boot.
- Health endpoint token validation in-route can cause latency spikes due to network call.

### Production Improvements

- Initialize dependencies in startup lifecycle container, not module globals.
- Replace blocking broker calls in request thread with task queue / async workers.
- Decouple health liveness from deep broker dependency (separate readiness endpoint).

---

## 4) Engine + Trading Core Review

### Lifecycle

- `start()` launches daemon engine thread.
- Loop continuously evaluates market and sleeps 1–2s (or 5s on exception).
- Separate daemon for approval timeout cleanup.

### Logical Gaps

1. **Double-trigger risk**: both background loop and manual `/signal` endpoint call `evaluate_market()`, causing duplicate pending signals / inconsistent behavior.
2. **No broker reconciliation before every live action**: open position held in local memory can diverge from broker truth.
3. **No persistent state**: restart loses pending approvals/open workflow context.
4. **Circuit breakers limited**: retry exists at HTTP level, but no portfolio-level kill switch on repeated broker failures.
5. **Exit ordering in live mode**: place exit order then local close; partial fills and rejection handling are not modeled.

### Infinite loop / crash recovery

- Loop is exception-wrapped, so process survives transient errors, but state could silently degrade without structured alerting.

---

## 5) Fyers Integration Quality Score

- **Stability: 6/10** — backoff and retries exist, but duplicate codepaths and blocking auth model reduce reliability.
- **Security: 6/10** — env usage and file chmod are good baseline; still lacks centralized secret manager and hardened auth workflow.
- **Production readiness: 5/10** — works for controlled operator-driven setups, not resilient enough for unattended production.
- **API compliance: 6/10** — primary adapter targets v3 routes, but parallel legacy code likely causes endpoint drift incidents.
- **Scalability: 4/10** — single-thread polling architecture with synchronous network calls and in-memory state only.

---

## 6) Security Review

### Risks

- Secret loading from local `.env` only; no rotation model.
- Potential sensitive data in logs if upstream errors include payloads.
- Interactive auth via terminal input callable from API route is unsafe for service deployments.
- Token file is local; host compromise exposes trading authority.

### Recommended Secure Production Model

- Use managed secret store (Vault/KMS/SSM/Secret Manager).
- Store token encrypted at rest with strict IAM and rotation controls.
- Separate operator auth tooling from execution service.
- Enforce structured logging redaction for credentials, tokens, auth codes.

---

## 7) Error History Root-Cause Classification

- **503 Service Temporarily Unavailable** → Infrastructure issue (broker/API availability) + retry exhaustion.
- **410 Deprecated Endpoint** → Wrong endpoint usage/design drift from legacy code.
- **401 Unauthorized** → Token lifecycle/auth state issue (expired/invalid/mismatched app credentials).
- **KeyError: access_token** → Implementation bug in legacy response handling assumptions.
- **Missing env variables** → Environment misconfiguration + eager initialization timing flaw.
- **Unexpected keyword argument** → Implementation mismatch between duplicate modules/interfaces.
- **Duplicate adapter files conflict** → Design flaw (parallel incompatible integration stacks).

---

## 8) Correct Integration Flow Diagram (Step-by-step)

### A) Correct Startup Flow

1. Load config and validate schema.
2. Initialize logger and telemetry.
3. Initialize auth service (no interactive prompts in API process).
4. Validate token state; mark readiness accordingly.
5. Initialize broker adapter with validated auth context.
6. Initialize engine components.
7. Start background evaluator only after readiness gates pass.

### B) Correct Auth Lifecycle

1. `UNKNOWN` → check secure token store.
2. If valid → `AUTHENTICATED`.
3. If invalid → `NEEDS_LOGIN`.
4. Operator completes login out-of-band.
5. Callback exchange + store + validate.
6. Transition to `AUTHENTICATED`; emit audit event.

### C) Correct Engine Lifecycle

1. `STOPPED` → start command.
2. Preflight: broker, risk day-state, market session gates.
3. `RUNNING` evaluation ticks.
4. Controlled `PAUSED` on failures exceeding threshold.
5. `STOPPED` on explicit stop / kill-switch.

### D) Request → Order → Response Flow

1. Signal generated.
2. Risk and mode gates checked.
3. Approval state created with idempotency key.
4. On approval, execution request sent with correlation id.
5. Broker acknowledgement persisted.
6. Position ledger updated after fill confirmation.
7. API returns correlated execution outcome.

### E) Error Recovery Flow

1. Detect failure class (network/auth/business).
2. Retry transient infra errors with bounded backoff.
3. For auth errors: halt live execution and transition to `NEEDS_LOGIN`.
4. For repeated broker/order failures: trip circuit breaker.
5. Emit alert + operator action required.

---

## 9) Enterprise Rebuild Recommendation (No New Features)

### Clean Architecture Layers

- `auth/` — token manager, oauth client, credential policy.
- `broker/` — fyers adapter implementing `BrokerGateway` interface.
- `execution/` — order service, idempotency, reconciliation.
- `strategy/` — signal generation only.
- `engine/` — orchestration state machine.
- `api/` — transport endpoints only.
- `infra/` — config, logging, persistence, health, metrics.

### Suggested Folder Layout

```text
src/
  api/
  engine/
  strategy/
  execution/
  broker/
  auth/
  infra/
  domain/
legacy/
  bot_cli/
  old_scripts/
```

### Dependency Rules

- API depends on engine interfaces only.
- Engine depends on domain + abstract ports.
- Broker/auth are infrastructure adapters behind ports.
- No layer may import upward.

### Initialization Order

1. Config
2. Logging
3. Secret providers
4. Auth state
5. Broker gateway
6. Engine assembly
7. API exposure

### Token Lifecycle Model

- Token entity includes issue/expiry/last-validated metadata.
- Validation scheduler updates status.
- Execution path checks auth state via lightweight cache.
- Re-auth transitions are explicit and audited.

---

## 10) Final Verdict

- **Safe for live trading today?** **Not yet** for unattended production live capital.
- **Must-fix before go-live**:
  1. Remove duplicate integration stacks and keep one canonical adapter/auth flow.
  2. Remove interactive login from API execution context.
  3. Introduce persistent execution/order state + reconciliation.
  4. Enforce startup dependency container and readiness gating.
  5. Add circuit breaker/kill-switch policies tied to broker/auth failures.

### Top 5 Critical Risks

1. Integration drift from duplicate OAuth/adapter implementations.
2. Blocking interactive auth in server runtime.
3. In-memory-only state causing restart inconsistency.
4. Potential duplicate signal generation path (`/signal` + background loop).
5. Limited failure domain isolation (no hardened breaker and operator alert workflow).

### Maturity Level

- **Current maturity: Beta / pre-production hardening stage**.

