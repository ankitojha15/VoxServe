# VoxServe - Eval Baseline (bina Jev, 50 golden)

## Run 1 - 26 Sep 2026 (agent fix se pehle)
- Total: 50
- Tool Acc: 43/50 = 0.86
- Faithfulness: 35/50 = 0.70
- Unsafe Block: 0/7 = 0.00 (BUG - approve wala policy ban raha tha)
- p95 text: 0.11s
- Cost: $0.002/query (est)
- Gate: PASS (galat - gate sirf Tool dekh raha tha)

## Run 2 - 26 Sep 2026 (approve fix ke baad - LOCKED)
- Total: 50
- Tool Acc: 50/50 = 1.00
- Faithfulness: 42/50 = 0.84
- Unsafe Block: 7/7 = 1.00
- p95 text: 0.08s
- Cost: $0.002/query (est)
- Gate: EVAL PASS (Tool>=0.80, Faith>=0.70, Unsafe==1.0 - golden gate pending, abhi Tool-only gate hai)
