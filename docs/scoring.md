# Scoring

RAG Health is a product-defined summary, not a scientifically validated measure. The provisional configurable weights are Knowledge 20%, Retrieval 25%, Answer Reliability 20%, Security 20%, Freshness 10%, and Efficiency 5%.

A score policy needs a version, weights, finding-to-penalty mapping, severity/confidence treatment, critical-security cap, minimum evidence, unavailable/skipped-check handling, and calibration provenance. Category and overall reports must display coverage and uncertainty/limitations. A scan with no retrieval tests must not imply retrieval quality was proven; use “not assessed” or a documented partial-score policy.

Before release, validate monotonicity, gaming resistance, stable comparisons, sensitivity, false confidence, and representative corpora. Never label the formula “scientifically proven.”

