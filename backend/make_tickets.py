import json
import random

random.seed(42)

ISSUES = [
    ("delivery stuck for 48 hours", "Arranged redelivery, delivered in 2 days"),
    ("damaged product received", "Refund approved in 7 days with photo proof"),
    ("wrong item delivered", "Replacement shipped, pickup scheduled"),
    ("refund not received after 7 days", "Bank transfer initiated, 3 days ETA"),
    ("tracking id not updating", "Carrier escalated, live status shared"),
    ("COD refund pending", "Bank details collected, transfer in 7 days"),
    ("failed delivery twice", "Returned to warehouse, redelivery booked"),
    ("coupon refund as store credit", "Store credit issued, explained policy"),
]

with open("data/past-tickets.json", "w") as f:
    for i in range(1, 5001):
        oid = str(random.choice([1001, 1002, 1003]) if random.random() < 0.7 else random.randint(2000, 9999))
        issue, reso = random.choice(ISSUES)
        t = {
            "ticket_id": f"OLD{i:04d}",
            "order_id": oid,
            "issue": issue,
            "resolution": reso,
            "status": "closed",
            "day": random.randint(1, 90),
        }
        f.write(json.dumps(t) + "\n")

print("Wrote 5000 tickets to data/past-tickets.json")