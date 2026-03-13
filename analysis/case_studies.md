# Hallucination Case Studies
## LLM Baseline vs Rule-Engine Ground Truth

The following 5 cases were automatically extracted from `logs/experiments.jsonl`
where the LLM baseline produced an **incorrect eligibility decision** compared
to the rule engine's deterministic output. They illustrate the types and
severity of hallucinations encountered.

---

## Case Study 1 — Pradhan Mantri Awas Yojana (PMAY)
**Income Hallucination: LLM ignores the EWS income cap**

| Field | Value |
|---|---|
| Age | 35 |
| Income | ₹4,50,000 |
| Category | SC |
| State | Karnataka |
| Owns House | No |
| Owns LPG | No |

### Rule Engine
> **NOT ELIGIBLE**
> Rule failed: `income (₹4,50,000) ≤ ₹3,00,000` → **FAILED**
> _"Annual income must be within EWS limit (₹3 lakh)"_

### LLM Baseline
> _"The applicant is **eligible** for Pradhan Mantri Awas Yojana due to meeting
> the income and ownership criteria."_

### Analysis
The LLM hallucinated eligibility despite an income of ₹4.5L — **50% above the
EWS limit**. The phrase "meeting the income criteria" is factually incorrect.
The LLM likely latched onto the SC category and lack of house ownership,
ignoring the disqualifying income rule entirely.

---

## Case Study 2 — PM-KISAN Samman Nidhi
**Income Exclusion Hallucination: LLM approves an excluded applicant**

| Field | Value |
|---|---|
| Age | 30 |
| Income | ₹3,00,000 |
| Category | SC |
| State | UP |
| Land Owned | 0.8 ha |

### Rule Engine
> **NOT ELIGIBLE**
> Rule passed: `land (0.8 ha) ≤ 2 ha` → ✅ PASSED
> Rule failed: `income (₹3,00,000) ≤ ₹2,50,000` → **FAILED**
> _"Applicant income must be below exclusion threshold"_

### LLM Baseline
> _"The applicant is **eligible** for PM-KISAN Samman Nidhi due to being a small
> farmer with landholding less than 2 hectares and belonging to the SC category."_

### Analysis
The LLM correctly noted the land holding qualification but **completely ignored
the income exclusion rule** — the more decisive criterion. It focused on
category and land area as positives, manufacturing an eligible verdict. This is
a classic **partial-criteria hallucination**: the LLM picks the rules that
confirm eligibility and discards the ones that don't.

---

## Case Study 3 — Ayushman Bharat PM-JAY
**Category Confusion: BPL treated as eligible, but scheme requires SC/ST**

| Field | Value |
|---|---|
| Age | 68 |
| Income | ₹1,20,000 |
| Category | **BPL** |
| State | Bihar |
| Has Health Insurance | No |

### Rule Engine
> **NOT ELIGIBLE**
> Rule failed: `category (BPL) in [SC, ST]` → **FAILED**
> _"Applicant belongs to a vulnerable social category (SC/ST)"_

### LLM Baseline
> _"The applicant is **eligible** for Ayushman Bharat – PM-JAY due to belonging
> to the BPL category and not having government health insurance."_

### Analysis
BPL (Below Poverty Line) is **not** a qualifying category for this scheme's
category rule — only SC and ST are. The LLM confused BPL with a broadly
qualifying welfare category, a reasonable commonsense assumption that is
**factually wrong** per the scheme's actual rules. This is a **rule-boundary
hallucination**: the LLM generalizes beyond what the eligibility criteria
specify.

---

## Case Study 4 — Ayushman Bharat PM-JAY
**OBC Category Hallucination: LLM grants eligibility to non-qualifying group**

| Field | Value |
|---|---|
| Age | 26 |
| Income | ₹1,80,000 |
| Category | **OBC** |
| State | Punjab |
| Has Health Insurance | No |

### Rule Engine
> **NOT ELIGIBLE**
> Rule failed: `category (OBC) in [SC, ST]` → **FAILED**
> _"Applicant belongs to a vulnerable social category (SC/ST)"_

### LLM Baseline
> _"The applicant is **eligible** for Ayushman Bharat – PM-JAY due to being from
> the OBC category and not having government health insurance."_

### Proposed System
> _"The applicant is **not eligible** for Ayushman Bharat – PM-JAY because they
> do not belong to the Scheduled Castes (SC) or Scheduled Tribes (ST), which is
> a mandatory criterion for eligibility."_

### Analysis
The LLM granted OBC-category applicants a benefit restricted to SC/ST, likely
because OBC is also a socially disadvantaged group in India and the LLM's
training data associates OBC with welfare eligibility broadly. This is a
**semantic overgeneralization hallucination**. The proposed system correctly
cites the mandatory criterion by name.

---

## Case Study 5 — PM-KISAN Samman Nidhi
**Land Ownership Hallucination: LLM denies a small farmer who holds 0.3 ha**

| Field | Value |
|---|---|
| Age | 16 |
| Income | ₹1,00,000 |
| Category | SC |
| State | Kerala |
| Land Owned | **0.3 ha** |

### Rule Engine
> **ELIGIBLE**
> `land (0.3 ha) ≤ 2 ha` → ✅ PASSED
> `income (₹1,00,000) ≤ ₹2,50,000` → ✅ PASSED

### LLM Baseline
> _"The applicant is **not eligible** for PM-KISAN Samman Nidhi due to
> **not owning any land**."_

### Proposed System
> _"The applicant is **eligible** for PM-KISAN Samman Nidhi as they are a small
> landholding farmer with an income below the exclusion threshold."_

### Analysis
The LLM hallucinated a false profile fact: the applicant **clearly owns 0.3
hectares** but the LLM output claims they own **no land**. This is a
**profile-misreading hallucination** — the most dangerous type because it
invents factual errors about the applicant's data itself. The proposed rule
engine reads the field correctly and reaches the right verdict.

---

## Summary Table

| # | Scheme | Ground Truth | LLM Output | Hallucination Type |
|---|--------|-------------|------------|-------------------|
| 1 | PMAY | NOT ELIGIBLE | ELIGIBLE | Income cap ignored |
| 2 | PM-KISAN | NOT ELIGIBLE | ELIGIBLE | Partial-criteria (income exclusion missed) |
| 3 | PM-JAY | NOT ELIGIBLE | ELIGIBLE | Rule-boundary (BPL ≠ SC/ST) |
| 4 | PM-JAY | NOT ELIGIBLE | ELIGIBLE | Semantic overgeneralization (OBC ≠ SC/ST) |
| 5 | PM-KISAN | ELIGIBLE | NOT ELIGIBLE | Profile misreading (invents "no land") |
