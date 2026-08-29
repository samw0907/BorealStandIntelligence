# boreal-stand-intelligence/src/c1_beetle_susceptibility.py
"""Module C1 — bark beetle stand susceptibility.

Logistic regression of stand-level bark beetle damage occurrence on transparent
predictors (spruce volume share, mean height, stand age, site fertility, edge
exposure, distance to prior damage, climatic water balance). Reports a
coefficient table with confidence intervals, a precision-recall curve and
average precision (not accuracy), and a driver ranking compared against
published Finnish findings. Logistic regression is chosen for interpretability.

Data tiers: stand attributes and prior damage records FETCH; climatic water
balance DERIVE ONLY (from FMI daily data).

No implementation yet — scaffold only.
"""
