# Metrics and Logging Checklist

This checklist defines metrics and logs to emit for chapter processing runs.

## Metrics
- Counter: runs_started{rule, detector}
- Counter: runs_succeeded{rule, detector}
- Counter: runs_failed{rule, detector}
- Counter: runs_abandoned{rule, detector}
- Counter: merge_ops_total
- Counter: split_ops_total
- Histogram: run_duration_ms

## Required Log Fields
- rule: strict_keep_original | auto_wordcount
- detector: regex | toc | auto_wordcount
- duration_ms
- status: running|succeeded|failed
- run_id, adaptation_id, book_id
- operations_count, target_count, detected_count

## Spot-checks
- process_chapters emits start, split/merge details, and finish with meta containing merge_ops/split_ops counters.
- status endpoint logs stale-run decisions.
