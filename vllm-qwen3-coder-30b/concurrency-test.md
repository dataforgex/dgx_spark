# vLLM Concurrency Test Results

## Configuration

- Max concurrent sequences: 256
- GPU memory utilization: 85%
- Features: Prefix caching, chunked prefill enabled

## Test 1: Simple Inference

**Task:** "Count from 1 to 5"
**Max tokens:** 50

| Concurrent Requests | Total Time | Avg Response | Throughput |
|---------------------|------------|--------------|------------|
| 1                   | 0.75s      | 0.75s        | 1.33 req/s |
| 5                   | 1.52s      | 1.51s        | 3.29 req/s |
| 10                  | 3.98s      | 2.42s        | 2.51 req/s |
| 20                  | 4.49s      | 3.19s        | 4.46 req/s |

**Result:** All requests succeeded. Throughput increased 3.4x with 20 concurrent requests.

## Test 2: Complex Inference

**Task:** "Write a Python function that implements a binary search tree with insert, search, and delete operations. Include proper error handling and docstrings."
**Max tokens:** 800

| Concurrent Requests | Total Time | Avg Response | Throughput |
|---------------------|------------|--------------|------------|
| 1                   | 35.52s     | 35.52s       | 0.03 req/s |
| 5                   | 87.83s     | 87.79s       | 0.06 req/s |
| 10                  | 127.51s    | 127.50s      | 0.08 req/s |
| 20                  | 129.50s    | 129.40s      | 0.15 req/s |

**Result:** All requests succeeded. Throughput increased 5x with 20 concurrent requests.

## Summary

- API processes multiple requests simultaneously
- 100% success rate across all test cases (55 total requests)
- Concurrent processing reduces total time compared to sequential execution
- Configured limit: 256 concurrent sequences
