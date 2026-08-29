# boreal-stand-intelligence/src/a_stand_estimation.py
"""Module A — growing stock estimation.

Estimates stand attributes (total volume, volume by species, mean height, basal
area) from ALS height metrics using the area-based approach and k-NN imputation
side by side, with spatial block cross-validation. Benchmarks our ALS metrics
against the Metsakeskus latvusmalli and our volume estimates against MS-NFI 2023,
reports RMSE / bias / relative RMSE by species and volume class, tunes k, checks
performance with and without MS-NFI features (circularity check), and reports
performance on stale-label stands (flagged by Module B) versus clean stands.
Ends with a working demonstration: arbitrary polygon in, estimates out.

Data tiers: stand boundaries and grid cells FETCH; ALS and Sentinel DERIVE
input; MS-NFI volume and latvusmalli DERIVE AND BENCHMARK.

Methods: area-based regression and k-NN imputation (k=5 is the MS-NFI default
starting point). scikit-learn NearestNeighbors is used only as a k-NN utility.

No implementation yet — scaffold only.
"""
