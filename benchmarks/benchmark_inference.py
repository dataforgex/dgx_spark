#!/usr/bin/env python3
"""
Inference Benchmark Script
Compares Time to First Token (TTFT) and Tokens per Second (TPS) across models.

Models tested:
- TRT-LLM Qwen3-30B-A3B-FP4 (port 8202) - MoE
- TRT-LLM Qwen3-32B-FP4 (port 8203) - Dense
- vLLM Qwen3-Coder-30B (port 8100) - Full precision

Usage:
    python benchmark_inference.py [--models all|trtllm|vllm] [--iterations 3]
"""

import argparse
import json
import time
import requests
import statistics
from dataclasses import dataclass
from typing import Optional


@dataclass
class BenchmarkResult:
    model_name: str
    prompt_type: str
    ttft_seconds: float  # Time to first token
    total_time_seconds: float
    output_tokens: int
    tokens_per_second: float
    input_tokens: int


# Model configurations
MODELS = {
    "trtllm-qwen3-30b-fp4": {
        "name": "TRT-LLM Qwen3-30B-A3B-FP4 (MoE)",
        "url": "http://localhost:8202/v1/chat/completions",
        "model_id": "nvidia/Qwen3-30B-A3B-FP4",
    },
    "trtllm-qwen3-32b-fp4": {
        "name": "TRT-LLM Qwen3-32B-FP4 (Dense)",
        "url": "http://localhost:8203/v1/chat/completions",
        "model_id": "nvidia/Qwen3-32B-FP4",
    },
    "vllm-qwen3-coder-30b": {
        "name": "vLLM Qwen3-Coder-30B",
        "url": "http://localhost:8100/v1/chat/completions",
        "model_id": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    },
    "vllm-qwen3-coder-30b-awq": {
        "name": "vLLM Qwen3-Coder-30B-AWQ",
        "url": "http://localhost:8104/v1/chat/completions",
        "model_id": "cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit",
    },
}

# Test prompts of varying complexity
TEST_PROMPTS = {
    "short": {
        "description": "Short prompt (~20 tokens input)",
        "messages": [{"role": "user", "content": "Write a hello world program in Python."}],
        "max_tokens": 100,
    },
    "medium": {
        "description": "Medium prompt (~50 tokens input)",
        "messages": [
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "Write a Python function that implements binary search on a sorted list. Include docstring and type hints."},
        ],
        "max_tokens": 300,
    },
    "long": {
        "description": "Long prompt (~100 tokens input)",
        "messages": [
            {"role": "system", "content": "You are an expert software architect with deep knowledge of design patterns and best practices."},
            {"role": "user", "content": """Design a REST API for a task management system. Include:
1. Endpoint definitions (GET, POST, PUT, DELETE)
2. Request/response schemas
3. Authentication approach
4. Error handling strategy
Provide code examples in Python using FastAPI."""},
        ],
        "max_tokens": 500,
    },
}


def check_model_available(url: str) -> bool:
    """Check if a model server is running."""
    try:
        # Try health endpoint first
        health_url = url.replace("/v1/chat/completions", "/health")
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200
    except:
        try:
            # Try models endpoint
            models_url = url.replace("/v1/chat/completions", "/v1/models")
            response = requests.get(models_url, timeout=5)
            return response.status_code == 200
        except:
            return False


def benchmark_streaming(url: str, model_id: str, messages: list, max_tokens: int) -> Optional[BenchmarkResult]:
    """
    Benchmark a model using streaming to measure TTFT accurately.
    """
    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": True,
    }

    start_time = time.perf_counter()
    first_token_time = None
    output_tokens = 0

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=300,
        )

        if response.status_code != 200:
            print(f"    Error: {response.status_code} - {response.text[:200]}")
            return None

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str.strip() == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                if first_token_time is None:
                                    first_token_time = time.perf_counter()
                                # Rough token count (actual would need tokenizer)
                                output_tokens += len(content.split()) + content.count('\n')
                    except json.JSONDecodeError:
                        pass

        end_time = time.perf_counter()

        if first_token_time is None:
            first_token_time = end_time

        total_time = end_time - start_time
        ttft = first_token_time - start_time

        # More accurate token counting using usage if available
        # For streaming, we estimate based on content

        return BenchmarkResult(
            model_name=model_id,
            prompt_type="",
            ttft_seconds=ttft,
            total_time_seconds=total_time,
            output_tokens=max(output_tokens, 1),
            tokens_per_second=output_tokens / (total_time - ttft) if (total_time - ttft) > 0 else 0,
            input_tokens=0,
        )

    except Exception as e:
        print(f"    Error: {e}")
        return None


def benchmark_non_streaming(url: str, model_id: str, messages: list, max_tokens: int) -> Optional[BenchmarkResult]:
    """
    Benchmark a model without streaming, using usage stats for accurate token counts.
    """
    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": False,
    }

    start_time = time.perf_counter()

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300,
        )

        end_time = time.perf_counter()

        if response.status_code != 200:
            print(f"    Error: {response.status_code} - {response.text[:200]}")
            return None

        data = response.json()

        usage = data.get('usage', {})
        output_tokens = usage.get('completion_tokens', 0)
        input_tokens = usage.get('prompt_tokens', 0)

        total_time = end_time - start_time

        # For non-streaming, we can't measure TTFT directly
        # We estimate it as a fraction of total time
        # A better approach would use streaming for TTFT measurement

        return BenchmarkResult(
            model_name=model_id,
            prompt_type="",
            ttft_seconds=0,  # Can't measure without streaming
            total_time_seconds=total_time,
            output_tokens=output_tokens,
            tokens_per_second=output_tokens / total_time if total_time > 0 else 0,
            input_tokens=input_tokens,
        )

    except Exception as e:
        print(f"    Error: {e}")
        return None


def run_benchmark(model_key: str, model_config: dict, iterations: int = 3, use_streaming: bool = True) -> dict:
    """Run benchmark for a single model across all prompt types."""
    results = {}

    print(f"\n{'='*60}")
    print(f"Benchmarking: {model_config['name']}")
    print(f"URL: {model_config['url']}")
    print(f"{'='*60}")

    if not check_model_available(model_config['url']):
        print(f"  SKIPPED - Model not available")
        return results

    for prompt_key, prompt_config in TEST_PROMPTS.items():
        print(f"\n  Prompt: {prompt_key} - {prompt_config['description']}")

        ttft_times = []
        tps_values = []
        total_times = []

        for i in range(iterations):
            print(f"    Iteration {i+1}/{iterations}...", end=" ", flush=True)

            if use_streaming:
                result = benchmark_streaming(
                    model_config['url'],
                    model_config['model_id'],
                    prompt_config['messages'],
                    prompt_config['max_tokens'],
                )
            else:
                result = benchmark_non_streaming(
                    model_config['url'],
                    model_config['model_id'],
                    prompt_config['messages'],
                    prompt_config['max_tokens'],
                )

            if result:
                ttft_times.append(result.ttft_seconds)
                tps_values.append(result.tokens_per_second)
                total_times.append(result.total_time_seconds)
                print(f"TTFT: {result.ttft_seconds:.3f}s, TPS: {result.tokens_per_second:.1f}, Total: {result.total_time_seconds:.2f}s")
            else:
                print("FAILED")

            # Small delay between iterations
            time.sleep(1)

        if ttft_times:
            results[prompt_key] = {
                "ttft_avg": statistics.mean(ttft_times),
                "ttft_std": statistics.stdev(ttft_times) if len(ttft_times) > 1 else 0,
                "tps_avg": statistics.mean(tps_values),
                "tps_std": statistics.stdev(tps_values) if len(tps_values) > 1 else 0,
                "total_time_avg": statistics.mean(total_times),
                "iterations": len(ttft_times),
            }

    return results


def print_comparison_table(all_results: dict):
    """Print a formatted comparison table."""
    print("\n")
    print("=" * 100)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 100)

    # Header
    print(f"\n{'Model':<40} {'Prompt':<10} {'TTFT (s)':<12} {'TPS':<12} {'Total (s)':<12}")
    print("-" * 100)

    for model_key, model_results in all_results.items():
        model_name = MODELS[model_key]['name']
        for prompt_key, metrics in model_results.items():
            ttft = f"{metrics['ttft_avg']:.3f} ± {metrics['ttft_std']:.3f}"
            tps = f"{metrics['tps_avg']:.1f} ± {metrics['tps_std']:.1f}"
            total = f"{metrics['total_time_avg']:.2f}"
            print(f"{model_name:<40} {prompt_key:<10} {ttft:<12} {tps:<12} {total:<12}")
        print()

    # Summary comparison
    print("\n" + "=" * 100)
    print("COMPARISON SUMMARY (averaged across all prompts)")
    print("=" * 100)

    summary = {}
    for model_key, model_results in all_results.items():
        if model_results:
            avg_ttft = statistics.mean([m['ttft_avg'] for m in model_results.values()])
            avg_tps = statistics.mean([m['tps_avg'] for m in model_results.values()])
            summary[model_key] = {"avg_ttft": avg_ttft, "avg_tps": avg_tps}

    print(f"\n{'Model':<45} {'Avg TTFT (s)':<15} {'Avg TPS':<15}")
    print("-" * 75)

    for model_key, metrics in sorted(summary.items(), key=lambda x: x[1]['avg_tps'], reverse=True):
        model_name = MODELS[model_key]['name']
        print(f"{model_name:<45} {metrics['avg_ttft']:<15.3f} {metrics['avg_tps']:<15.1f}")

    # Winner
    if summary:
        fastest_ttft = min(summary.items(), key=lambda x: x[1]['avg_ttft'])
        highest_tps = max(summary.items(), key=lambda x: x[1]['avg_tps'])

        print(f"\nFastest TTFT: {MODELS[fastest_ttft[0]]['name']} ({fastest_ttft[1]['avg_ttft']:.3f}s)")
        print(f"Highest TPS:  {MODELS[highest_tps[0]]['name']} ({highest_tps[1]['avg_tps']:.1f} tokens/s)")


def main():
    parser = argparse.ArgumentParser(description="Benchmark inference speed across models")
    parser.add_argument(
        "--models",
        choices=["all", "trtllm", "vllm", "trtllm-30b", "trtllm-32b"],
        default="all",
        help="Which models to benchmark",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per test (default: 3)",
    )
    parser.add_argument(
        "--no-streaming",
        action="store_true",
        help="Use non-streaming mode (can't measure TTFT accurately)",
    )
    args = parser.parse_args()

    # Select models based on argument
    if args.models == "all":
        models_to_test = MODELS
    elif args.models == "trtllm":
        models_to_test = {k: v for k, v in MODELS.items() if k.startswith("trtllm")}
    elif args.models == "vllm":
        models_to_test = {k: v for k, v in MODELS.items() if k.startswith("vllm")}
    elif args.models == "trtllm-30b":
        models_to_test = {"trtllm-qwen3-30b-fp4": MODELS["trtllm-qwen3-30b-fp4"]}
    elif args.models == "trtllm-32b":
        models_to_test = {"trtllm-qwen3-32b-fp4": MODELS["trtllm-qwen3-32b-fp4"]}

    print("=" * 60)
    print("INFERENCE BENCHMARK")
    print("=" * 60)
    print(f"Models to test: {list(models_to_test.keys())}")
    print(f"Iterations per test: {args.iterations}")
    print(f"Streaming mode: {not args.no_streaming}")
    print(f"Prompt types: {list(TEST_PROMPTS.keys())}")

    # Check which models are available
    print("\nChecking model availability...")
    available_models = {}
    for model_key, model_config in models_to_test.items():
        available = check_model_available(model_config['url'])
        status = "AVAILABLE" if available else "NOT RUNNING"
        print(f"  {model_config['name']}: {status}")
        if available:
            available_models[model_key] = model_config

    if not available_models:
        print("\nNo models available! Please start at least one model server.")
        print("\nTo start models:")
        print("  TRT-LLM 30B: cd trtllm-qwen3-30b-fp4 && ./serve.sh")
        print("  TRT-LLM 32B: cd trtllm-qwen3-32b-fp4 && ./serve.sh")
        print("  vLLM 30B:    cd vllm-qwen3-coder-30b && ./serve.sh")
        return

    # Run benchmarks
    all_results = {}
    for model_key, model_config in available_models.items():
        results = run_benchmark(
            model_key,
            model_config,
            iterations=args.iterations,
            use_streaming=not args.no_streaming,
        )
        if results:
            all_results[model_key] = results

    # Print comparison
    if all_results:
        print_comparison_table(all_results)

        # Save results to JSON
        output_file = f"benchmark_results_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "iterations": args.iterations,
                "streaming": not args.no_streaming,
                "results": all_results,
            }, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    else:
        print("\nNo results collected!")


if __name__ == "__main__":
    main()
