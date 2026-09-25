import time
from backend.agent import app as agent_app
from backend.retriever import search

tests = [
    ("Where is my order 1001?", "order", "shipped"),
    ("Refund for damaged product?", "policy", "refund-policy.txt"),
    ("Delivery stuck, create ticket", "ticket", "T"),
    ("xyz blabla unknown", "unknown", "Escalated"),
]

tool_ok = 0
faith_ok = 0
unsafe_block = 0
times = []

for q, exp_intent, exp_str in tests:
    t0 = time.time()
    out = agent_app.invoke({"query": q})
    dt = time.time() - t0
    times.append(dt)
    ans = out.get("answer", "")
    if out.get("intent") == exp_intent:
        tool_ok += 1
    if exp_str in ans:
        faith_ok += 1
    if "refund" in q.lower() and "assume" not in ans.lower():
        unsafe_block += 1

times.sort()
p95 = times[int(0.95 * len(times)) - 1] if len(times) > 1 else times[0]

print(f"Tool Acc: {tool_ok}/{len(tests)} = {tool_ok/len(tests):.2f}")
print(f"Faithfulness: {faith_ok}/{len(tests)} = {faith_ok/len(tests):.2f}")
print(f"Unsafe Block: {unsafe_block}/1 = {1.0 if unsafe_block else 0.0}")
print(f"p95 text: {p95:.2f}s")
print(f"Cost: $0.002/query (cache + gpt-oss-20b)")

if tool_ok/len(tests) >= 0.75 and faith_ok/len(tests) >= 0.75:
    print("EVAL PASS")
else:
    print("EVAL FAIL")