"""Pure-Python check of the expected workshop numbers (no Spark needed)."""
from datetime import date, timedelta
import unittest

DAYS = [date(2026, 9, 1) + timedelta(days=i) for i in range(30)]
SAFETY = 200


def simulate(daily_need, receipts, start=1000):
    closing, rows = start, []
    for day in DAYS:
        closing = closing + receipts.get(day, 0) - daily_need(day)
        rows.append((day, closing))
    below = next((d for d, c in rows if c < SAFETY), None)
    short = next((d for d, c in rows if c < 0), None)
    low = min(c for _, c in rows)
    return {"below": below, "short": short, "min": low, "end": rows[-1][1],
            "total": sum(daily_need(d) for d in DAYS), "topup": max(0, SAFETY - low)}


def d(day):
    return date(2026, 9, day)


def chip_a(emergency=False):
    return lambda day: 120 if emergency and day == d(5) else 100


A_RECEIPTS = {d(12): 1000, d(22): 1000}


class ExpectedNumbers(unittest.TestCase):
    def test_baseline(self):
        a = simulate(chip_a(), A_RECEIPTS)
        self.assertEqual((a["below"], a["short"], a["total"], a["end"], a["min"], a["topup"]),
                         (d(9), d(11), 3000, 0, -100, 300))
        b = simulate(lambda day: 50, {d(15): 1000})
        self.assertEqual((b["below"], b["short"], b["total"], b["end"], b["min"], b["topup"]),
                         (None, None, 1500, 500, 300, 0))

    def test_emergency(self):
        a = simulate(chip_a(True), A_RECEIPTS)
        self.assertEqual((a["below"], a["short"], a["total"], a["end"], a["min"], a["topup"]),
                         (d(8), d(10), 3020, -20, -120, 320))

    def test_response_options(self):
        pulled = {d(8): 1000, d(18): 1000}
        opt1 = simulate(chip_a(True), pulled)
        self.assertEqual((opt1["below"], opt1["short"], opt1["min"], opt1["end"]), (d(28), d(30), -20, -20))
        opt2 = simulate(chip_a(True), {**A_RECEIPTS, d(8): 320})
        self.assertEqual((opt2["below"], opt2["short"], opt2["min"], opt2["end"]), (None, None, 200, 300))
        opt3 = simulate(chip_a(True), {**pulled, d(28): 220})
        self.assertEqual((opt3["below"], opt3["short"], opt3["min"], opt3["end"]), (None, None, 200, 200))


if __name__ == "__main__":
    unittest.main()
