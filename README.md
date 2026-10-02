# Iraqi public university rankings: robustness dataset

Data and code for a study of (a) how stable a composite ranking of Iraqi public
universities is when indicator weights change and (b) how far the national
ranking agrees with international rankings.

This repository is independent of any application repository.

## Contents

| Path | What it is |
| --- | --- |
| `data/universities.csv` | 37 public institutions x 13 indicator columns (one row per institution) |
| `data/the_wur_2027_pillars.csv` | THE WUR 2027 pillar scores for the 23 ranked institutions |
| `data/raw/compare_snapshot.json` | Values of the original 20 institutions as extracted from the comparison app |
| `scripts/build_dataset.py` | Rebuilds `universities.csv` and checks it against the snapshot |

## Population

The 37 institutions listed under "public universities" in the Iraqi University
Ranking (IRU) 2025: 35 universities and 2 university colleges
(`type = university college`). Al-Shatrah University is excluded by the ranking
itself (no graduating cohort yet). Kurdistan Region universities are outside
the IRU and outside this dataset.

## Columns and sources (all collected 2026-10-02)

| Column | Source |
| --- | --- |
| `iru2025_rank`, `iru2025_score` | MoHESR, IRU 2025 results, iru.mohesr.gov.iq/result |
| `iru2024_rank`, `iru2024_score` | MoHESR, IRU 2024 results, iru.asse-gate.gov.iq |
| `the_wur_2027` | Times Higher Education World University Rankings 2027 table |
| `qs_wur_2027` | QS World University Rankings 2027 (MoHESR announcement, 18 June 2026, for the added institutions) |
| `sir2026_overall/research/innovation/societal` | SCImago Institutions Rankings 2026, Higher education sector, Iraq; global rank |
| `the_impact_2026` | THE Sustainability Impact Ratings 2026 table |
| `students_the2027`, `students_per_staff_the2027` | THE institution profiles (WUR 2027 data); published for ranked institutions only |

## Missing-value codes

- `NR`: not listed in that ranking edition.
- `Reporter`: THE status for an institution that submitted data but did not meet
  the criteria to be ranked (7 institutions). Distinct from `NR`.
- blank: value not published (students and staff ratio for unranked institutions).

## Notes for the analysis

1. Circularity: "international rankings" is one axis (10%) of the IRU, so
   national-international agreement is not fully independent.
2. The IRU used 10 axes in 2024 and 9 axes in 2025 with different weights; the
   2024-2025 comparison is itself a natural reweighting experiment.
3. THE publishes bands, not exact ranks. A continuous score can be rebuilt from
   the pillar file with THE weights (teaching 29.5, research environment 29,
   research quality 30, industry 4, international outlook 7.5). The rebuilt
   score falls inside the published overall band for all 23 institutions.
4. IRU scores are rounded to 4 decimals.
5. Founding year (a descriptive field in the app) is not included; it was not
   verified for the added institutions and is not used in the analysis.
