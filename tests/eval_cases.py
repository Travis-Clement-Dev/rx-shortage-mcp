"""Curated evaluation scenarios — the KPI Bucket-1 measuring stick (chain success).

Each case is a diverse drug (generic, brand, or abbreviation) with a stable RxNorm
normalization and a clean single-ingredient ATC-4 class. `test_evals.py` runs the full
chain per case and scores STRUCTURAL success (target ≥90%).

Expectations are deliberately stable — normalization + "has a pure class with siblings" +
"returns a valid shortage status" — NOT live shortage status, which drifts day to day. The
cascade behaviour (an alternative that is also short) is demonstrated in the live demo run,
where current data makes it observable.
"""

# (input as a user might type it, substring expected in the normalized RxNorm name)
CASES = [
    ("furosemide", "furosemide"),        # loop diuretic
    ("atorvastatin", "atorvastatin"),    # statin
    ("lisinopril", "lisinopril"),        # ACE inhibitor
    ("metoprolol", "metoprolol"),        # beta blocker
    ("omeprazole", "omeprazole"),        # PPI
    ("sertraline", "sertraline"),        # SSRI
    ("amlodipine", "amlodipine"),        # calcium channel blocker
    ("albuterol", "albuterol"),          # beta-2 agonist
    ("gabapentin", "gabapentin"),        # antiepileptic
    ("ondansetron", "ondansetron"),      # 5-HT3 antagonist
    ("ciprofloxacin", "ciprofloxacin"),  # fluoroquinolone
    ("amoxicillin", "amoxicillin"),      # penicillin
    ("levothyroxine", "levothyroxine"),  # thyroid hormone
    ("Lipitor", "Lipitor"),              # brand name → resolves
    ("HCTZ", "hydrochlorothiazide"),     # abbreviation → expands
]
