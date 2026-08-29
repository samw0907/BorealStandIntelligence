# boreal-stand-intelligence/src/b_harvest_detection.py
"""Module B — harvest change detection.

Detects fellings between two Sentinel composite windows using a change metric
(dNBR by default, with dNDMI and Sentinel-1 log-ratio cross-checks), scores
detections against forest use declarations by felling type (regeneration,
thinning, salvage), and runs a threshold sweep to find optimal thresholds per
type. Produces precision/recall/F1 by felling type and by stand area class, the
declared-but-not-detected and detected-but-not-declared sets, a stated minimum
reliably detectable stand area, and a per-stand `inventory_stale` flag written
to GeoPackage for Module A to consume.

Data tiers: Sentinel DERIVE ONLY; forest use declarations and stand boundaries
FETCH; forest mask FETCH.

No implementation yet — scaffold only.
"""
