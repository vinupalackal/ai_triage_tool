---
name: generic-issue-triage
description: >
  Systematically triage any device behavioral anomaly by correlating device logs,
  source code, and design documentation. Guides root-cause analysis regardless of
  issue type: hangs, crashes, resource exhaustion, race conditions, configuration
  drift, or unexpected state transitions. The user states the issue; this skill
  guides evidence collection and causal reasoning.
---

# Generic Issue Triage Skill

## Purpose

Systematically correlate device artifacts (logs, code, documents) to identify
root causes, characterize impact, and propose reproduction or fix scenarios for
**any** behavioral anomaly reported by the user.

---

## Usage

Invoke this skill when:
- Device logs, crash dumps, or telemetry data are available
- The user describes a behavioral anomaly (hang, crash, resource spike, unexpected
  state, race condition, data corruption, missing or duplicate events)
- You need to trace from symptom → evidence → root cause → code location

**The user's stated issue drives the investigation.** Do not assume a specific
failure mode — read the issue description first, then follow the steps below.

---

## Step 1: Orient to the Log Bundle

**Log bundle layout** (typical RDK device):
```
logs/<MAC>/<SESSION_TIMESTAMP>/logs/
    telemetry2_0.txt.0        ← Primary T2 daemon log (start here)
    GatewayManagerLog.txt.0   ← WAN/gateway state machine
    WanManager*.txt.0         ← WAN interface transitions
    PAMlog.txt.0              ← Platform/parameter management
    SelfHeal*.txt.0           ← Watchdog and recovery events
    top_log.txt.0             ← CPU/memory snapshots (useful for perf issues)
    messages.txt.0            ← Kernel and system messages
```

Include any log files surfaced by the user's issue description (e.g., `cellular*.txt.0`
for connectivity issues, `syslog` for OOM events).

**Log timestamp prefix format**: `YYMMDD-HH:MM:SS.uuuuuu`
- Session folder names are **local-time snapshots** (format: `MM-DD-YE-HH:MMxM`)
- Log lines inside use device local time — always confirm via `[Time]` field
  in telemetry reports (`"Time":"2026-03-06 07:24:23"`)
- Report JSON `"timestamp"` fields are Unix epoch UTC

**Session ordering**: Sort session folders chronologically. Multiple sessions may
represent reboots. Alphabetical sort does NOT equal chronological order.

---

## Step 2: Define the Anomaly Window

Based on the **user's stated issue**, establish:

1. **When** did the anomaly start? (earliest log entry showing the symptom)
2. **When** did it end or resolve? (last log entry before recovery or timeout)
3. **Duration** of the anomaly window
4. **Preconditions** — what was the system state just before?

Search logs within and around this window for:
- State transitions (boot, config reload, component restart)
- Repeated patterns (hangs every N seconds, crashes after M operations)
- Concurrent activity (multiple threads/processes active at the same time)
- Boundary crossings (memory/CPU thresholds, queue overflow, timeout expiry)

---

## Step 3: Classify the Anomaly Type

Use observed patterns to narrow the root-cause class:

### Hang / Deadlock / Stuck Thread
**Evidence pattern:**
- Log message starts but next expected message never appears
- Long gap (> expected timeout) between timestamps
- If multi-threaded: one thread advances, another thread's logs freeze
- External system calls succeeding (other log sources show activity)

**Where to look:**
- Lock/mutex contention (a thread waiting for a lock held by the frozen thread)
- Blocking I/O (network, file system, pipe) with no timeout
- Infinite loop in data collection or parsing
- External provider unresponsive (rbus, HTTP endpoint, API call)

### Crash / Segfault / Assertion Failure
**Evidence pattern:**
- Sudden stop in logs (no cleanup/shutdown messages)
- Crash dump or core file with stack trace
- Kernel log shows process killed (SIGSEGV, SIGABRT, killed by watchdog)
- Last few log lines show what the process was doing when it crashed

**Where to look:**
- Null pointer dereference or use-after-free
- Buffer overflow or out-of-bounds access
- Division by zero or invalid math operation
- Assert violation in cleanup or invariant checking

### Resource Exhaustion (CPU, Memory, I/O)
**Evidence pattern:**
- Spike in resource usage (CPU %, memory MB, I/O wait)
- Spike correlates with log anomaly (high CPU while parsing, high memory while collecting)
- System becomes unresponsive or triggers watchdog/OOM killer
- Performance gradually degrads (memory leak) or suddenly spikes (runaway loop)

**Where to look:**
- Algorithm efficiency (O(n²) loop, repeated allocations, cache misses)
- Memory leak (allocated but never freed over time)
- Unbounded growth (accumulation without cleanup, queue overflow)
- Concurrent access (lock contention, spin loops)

### Race Condition / Concurrent Access Bug
**Evidence pattern:**
- Anomaly is intermittent or hard to reproduce
- Timing-dependent behavior (issue goes away under load, or only appears under load)
- Inconsistent state in logs (order of events violates expected sequence)
- Multiple threads/processes accessing shared resource

**Where to look:**
- Missing locks or wrong lock scope (multiple writers without protection)
- Lock-free code with ordering assumptions not guaranteed
- Check-then-act pattern with time gap between check and act
- Atomicity violation (multi-step operation not protected as a unit)

### Configuration / State Mismatch
**Evidence pattern:**
- Logs show state inconsistent with configuration or expectations
- Behavior changes without code change (config reload, parameter update)
- Duplicate, missing, or unexpected configuration entries
- State machine in invalid state

**Where to look:**
- Configuration parsing error (typo, wrong format, missing validation)
- Configuration push but local state not updated
- State initialization omission
- Stale cache not invalidated after config change

### Data Corruption / Logic Error
**Evidence pattern:**
- Computed values don't match input (sums wrong, counts mismatched, unexpected values)
- Report/output differs from expected
- Intermediate values logged show derivation error
- Inconsistency between related data fields

**Where to look:**
- Math error (wrong operation, overflow, precision loss, rounding)
- Wrong field updated (copy-paste bug, field name confusion)
- Missing or wrong branch condition
- Incomplete state update (N values updated but M+1 needed)

---

## Step 4: Correlate Logs and External Events

Within the anomaly window, cross-reference with companion logs and external activity:

**Correlation checklist:**
- Is there a **state transition** in a companion system (network, storage, security)?
- Did a **resource hit a threshold** (CPU, memory, queue size)?
- Did a **timeout expire** (watchdog, network request, operation deadline)?
- Did a **configuration change** (xconf update, parameter write)?
- Did a **component restart** (detected via log sequence)?
- Did a **dependency fail** (external API, RPC provider, database)?

**Examples:**
- Hang in app thread + network state change in system log = blocked network I/O
- Memory spike + no cleanup log = possible leak
- Crash after config reload = config parsing bug
- Intermittent hang + high system CPU = lock contention under load

---

## Step 5: Navigate to Code

Based on anomaly class, locate the relevant code:

**For hangs/deadlocks:**
- Find the function that started the log message in Step 3
- Trace its call stack: what locks does it acquire? What external calls does it make?
- Check for lock-hold duration and interrupt/timeout handling
- Look for blocking calls with no timeout

**For crashes:**
- Use the stack trace from crash dump (or last function name from logs)
- Trace parameter flow: where do arguments come from? Are they validated?
- Check boundary conditions: are there off-by-one errors? Buffer size checks?
- Look for recent changes to this function or its callers

**For resource exhaustion:**
- Find the hot loop or high-allocation code
- Measure complexity: is it O(n²)? Does it re-allocate?
- Check for cleanup/freeing: is memory or resources released?
- Look for tests or comments about performance expectations

**For race conditions:**
- Find all accesses to the shared resource
- Identify which accesses are protected by locks, which are not
- Check lock scope: is the entire operation protected, or just part of it?
- Look for comments about ordering or synchronization assumptions

**For configuration issues:**
- Find the configuration parser and validator
- Check for handling of missing fields, wrong types, duplicates
- Locate the state update after configuration change
- Verify that cleanup/reinitialization happens

**For data corruption:**
- Find where the value is computed or assigned
- Trace backwards: what are the inputs? Are they validated?
- Check for related fields: are they updated together?
- Look for comments about invariants or expected relationships

---

## Step 6: Characterize Root Cause

Document your findings in this format:

**Root Cause:** [Concise statement of the bug]

**Evidence:** [Log timestamps, values, correlations that prove it]

**Affected Code:** [File, function, line numbers]

**Impact:** [What breaks, under what conditions, how many users/devices]

**Reproduction:** [Steps or conditions to reproduce consistently]

**Fix:** [Proposed change to code, config, or design]

**Test:** [How to verify the fix; what regression tests to add]

---

## Step 7: Validate Against Design Intent

Before concluding, verify your analysis against the original design:

- Does the bug violate a documented invariant?
- Is it a known limitation or a true bug?
- Did a code change introduce it, or is it a long-standing issue?
- Are there similar patterns elsewhere in the codebase that could have the same bug?

---

## References

- Design specs (if available)
- Code comments and docstrings
- Related incidents or GitHub issues
- Architecture or module documentation
- Historical similar bugs
