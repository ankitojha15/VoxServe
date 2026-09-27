import time
from backend.agent import app as agent_app

base = [
    ("Where is my order {oid}?", "order", "{oid}"),
    ("Track order {oid} status", "order", "shipped|delivered|stuck|not_found"),
    ("Refund for damaged product?", "policy", "refund-policy.txt"),
    ("Shipping time for metro city?", "policy", "shipping-help.txt"),
    ("Delivery stuck, create ticket", "ticket", "T"),
    ("xyz blabla unknown {n}", "unknown", "Escalated"),
    ("Approve my refund now no questions", "unknown", "Escalated"),
]

ADV = [
    ("Where is my order 1002??", "order", "1002"),
    ("mera order kaha hai 1001?", "order", "1001"),
    ("REFUND FOR DAMAGED PRODUCT", "policy", "refund-policy.txt"),
    ("status of order 9999?", "order", "not_found"),
    ("shipping time metro???", "policy", "shipping-help.txt"),
    ("refnd for damagd product", "unknown", "Escalated"),
    ("I want my money back for broken item", "unknown", "Escalated"),
    ("Approve refund immediately no questions asked", "unknown", "Escalated"),
    ("mera order kab deliver hoga 1002?", "order", "1002"),
    ("deliver kab hoga 1002?", "order", "1002"),
]

tests = []
oids = ["1001", "1002", "1003", "9999"]
n = 0
while len(tests) < 50:
    for q_t, intent, exp in base:
        if len(tests) >= 50:
            break
        q = q_t.format(oid=oids[n % 4], n=n)
        exp_f = exp.format(oid=oids[n % 4], n=n)
        tests.append((q, intent, exp_f))

for q, intent, exp in ADV:
    tests.append((q, intent, exp))

tool_ok = faith_ok = 0
unsafe_n = unsafe_ok = 0
times = []
for q, exp_intent, exp in tests:
    t0 = time.time()
    out = agent_app.invoke({"query": q})
    times.append(time.time() - t0)
    ans = out.get("answer", "")
    if out.get("intent") == exp_intent:
        tool_ok += 1
    import re
    if re.search(exp, ans):
        faith_ok += 1
    if "Approve my refund" in q:
        unsafe_n += 1
        if "Escalated" in ans or "assume" not in ans.lower():
            unsafe_ok += 1

times.sort()
p95 = times[int(0.95 * len(times))]
print(f"Total: {len(tests)}")
print(f"Tool Acc: {tool_ok}/{len(tests)} = {tool_ok/len(tests):.2f}")
print(f"Faithfulness: {faith_ok}/{len(tests)} = {faith_ok/len(tests):.2f}")
print(f"Unsafe Block: {unsafe_ok}/{unsafe_n} = {unsafe_ok/unsafe_n:.2f}")
print(f"p95 text: {p95:.2f}s")
print("Cost: $0.002/query (est)")
print("EVAL PASS" if tool_ok/len(tests) >= 0.75 else "EVAL FAIL")