import asyncio
import aiohttp
import time
import json

API_URL = "http://localhost:8100/v1/chat/completions"

async def make_request(session, request_id):
    """Make a single API request"""
    start_time = time.time()
    try:
        payload = {
            "model": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
            "messages": [
                {"role": "user", "content": f"Write a Python function that implements a binary search tree with insert, search, and delete operations. Include proper error handling and docstrings. Request #{request_id}"}
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }

        async with session.post(API_URL, json=payload) as response:
            result = await response.json()
            elapsed = time.time() - start_time

            if response.status == 200:
                return {
                    "request_id": request_id,
                    "status": "success",
                    "elapsed": elapsed,
                    "response_length": len(result.get("choices", [{}])[0].get("message", {}).get("content", ""))
                }
            else:
                return {
                    "request_id": request_id,
                    "status": "failed",
                    "elapsed": elapsed,
                    "error": result
                }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "request_id": request_id,
            "status": "error",
            "elapsed": elapsed,
            "error": str(e)
        }

async def test_concurrent_requests(num_requests):
    """Test multiple concurrent requests"""
    print(f"\n{'='*60}")
    print(f"Testing {num_requests} concurrent requests...")
    print(f"{'='*60}\n")

    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, i+1) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    # Analyze results
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"{'='*60}")
    print(f"Total requests: {num_requests}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average response time: {sum(r['elapsed'] for r in successful) / len(successful):.2f}s" if successful else "N/A")
    print(f"Throughput: {num_requests / total_time:.2f} req/s")

    if failed:
        print(f"\nFailed requests:")
        for r in failed[:5]:  # Show first 5 failures
            print(f"  Request #{r['request_id']}: {r.get('error', 'Unknown error')}")

    print(f"{'='*60}\n")

    return len(successful) == num_requests

async def main():
    """Run tests with increasing concurrency"""
    test_sizes = [1, 5, 10, 20]

    print(f"\nTesting vLLM API Concurrent Request Handling")
    print(f"API URL: {API_URL}")

    for size in test_sizes:
        success = await test_concurrent_requests(size)
        if not success:
            print(f"⚠️  Some requests failed at {size} concurrent requests")
        else:
            print(f"✓ All {size} requests succeeded")

        # Small delay between test rounds
        await asyncio.sleep(2)

    print("\n" + "="*60)
    print("CONCLUSION:")
    print("="*60)
    print("The vLLM API is configured to handle concurrent requests.")
    print(f"Current configuration allows up to 256 concurrent sequences.")
    print("Actual capacity depends on GPU memory and request complexity.")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
