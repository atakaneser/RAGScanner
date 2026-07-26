# Scoring

RAG Health is a product-defined, versioned summary of assessed evidence. It is not a scientifically
validated guarantee and it never treats an unavailable assessment as a zero or a pass.

Policy `1.0.0` uses the following available dimensions:

| Dimension | Weight | Current evidence |
|---|---:|---|
| Security | 35% | Confidence-adjusted deterministic security findings |
| Knowledge quality | 20% | Token-weighted chunk quality |
| Efficiency | 15% | Material duplicate percentage |

Retrieval quality, answer reliability, and freshness remain `not assessed` until representative
queries, relevance labels, answer evaluation, and source-time evidence exist. The overall score
normalizes weights across assessed dimensions only and records the assessment coverage ratio. At
least two dimensions must be assessed before an overall score is emitted.

Security penalties are critical 25, high 15, medium 8, low 3, and informational 1, multiplied by
finding confidence. A critical deterministic security finding caps the overall result at 54.99 so
it cannot be averaged away. Chunk-quality scores are weighted by chunk token count rather than by
the number of chunks. Duplicate cost uses the larger of estimated redundant token or character
percentage.

Each report stores the policy version, weights, penalties, assessed dimensions, coverage ratio,
formula, dimension inputs, and any applied cap. Policy comparison must treat a version change as a
methodology change rather than an ordinary health trend.

The policy is provisional. Validate monotonicity, gaming resistance, sensitivity, false confidence,
and representative corpora before making product claims. Use `ragscanner quality calibrate` to
measure deterministic rule precision and recall on an explicitly labelled local corpus; see
[Quality calibration](quality-calibration.md).
