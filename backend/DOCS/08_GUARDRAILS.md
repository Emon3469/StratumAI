# Guardrails

Input guardrails run in parallel with the planner, so they add no latency to allowed requests.

## Layers

1. **Size limit**: messages over 4,000 characters receive a polite refusal before any model call.
2. **Pattern rules**: regular expressions catch common injection phrasing such as "ignore previous instructions", requests to reveal the system prompt, "developer mode" and attempts to disable safety rules.
3. **Classifier**: Meta's Prompt Guard 2 (86M) on Groq scores the message; scores at or above `GUARD_THRESHOLD` are blocked. It has a 2-second timeout and fails open, so an outage never blocks legitimate users.
4. **Topical routing**: the planner labels clearly unrelated requests as `off_topic`, which receive a scope message instead of a model call.

## Responses

Blocked and off-topic messages are routed to the `refuse` node, which streams a fixed policy message. The `done` event records the decision in `plan`, for example `Guardrail: blocked (injection)`.

## Tuning

- Raise `GUARD_THRESHOLD` if legitimate security questions are being blocked.
- Set `GUARD_ENABLED=false` to disable input guardrails, for example during evaluation runs.
- Edit `app/guardrails/policies.py` to change patterns, scope or wording.
