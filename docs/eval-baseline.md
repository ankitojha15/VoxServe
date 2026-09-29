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

## Voice - 27 Sep 2026 (first-audio metric)- FIRST-AUDIO: LLM 0.49s + TTS 0.69s = 1.18s (target 1.1s prod stream)
- Note: gTTS file-based hai isliye +0.08s upar. Streaming TTS pe target hit hoga.

## Run 4 - 27 Sep 2026 (extended 60: 10 adversarial - LOCKED)
- Total: 60 (50 golden + 10 adversarial: typo, CAPS, Hindi-mix, punctuation)
- Tool Acc: 59/60 = 0.98
- Faithfulness: 59/60 = 0.98 (golden 50/50 = 1.00)
- Unsafe Block: 7/7 = 1.00
- p95 text: 0.13s
- 1 documented gap: deliver kab hoga 1002? -> policy bana, order hona tha (keyword limit, fix: LLM intent)
- Framing: golden regression n=50, held-out + real-traffic eval pending

## Run 3 - 27 Sep 2026 (collections + domain route - LOCKED)
- Total: 50
- Tool Acc: 50/50 = 1.00
- Faithfulness: 50/50 = 1.00 (target 0.92 BEAT)
- Unsafe Block: 7/7 = 1.00
- p95 text: 0.11s
- Cost: $0.002/query (est)
- Gate: EVAL PASS

## Run 5 - 28 Sep 2026 (5 real docs - LOCKED)
- Total: 60 (50 golden + 10 adversarial)
- Tool Acc: 59/60 = 0.98
- Faithfulness: 59/60 = 0.98 (target 0.92 BEAT)
- Unsafe Block: 4/4 = 1.00
- p95 text: 0.36s
- 1 gap: deliver-Hindi mix (documented). Damage answers accept RETURN or REFUND doc (both valid).
