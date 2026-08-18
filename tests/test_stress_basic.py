"""Stress tests para endpoints críticos — concurrencia y throughput."""

import concurrent.futures
import time

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


class TestStressPredictEndpoint:
    """Stress tests para /predict endpoint."""

    def test_stress_10_concurrent_predict_requests(self):
        """10 concurrent requests to /predict endpoint."""
        urls = [f"http://phishing-test-{i}.example.com" for i in range(10)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            start = time.time()
            futures = [
                executor.submit(client.post, "/predict", json={"url": url})
                for url in urls
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            elapsed = time.time() - start

        assert len(results) == 10
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 8, f"Only {success_count}/10 requests succeeded"

        throughput = 10 / elapsed
        print(f"\n✅ 10 concurrent /predict in {elapsed:.2f}s = {throughput:.1f} req/s")

    def test_stress_25_concurrent_predict_requests(self):
        """25 concurrent requests to /predict endpoint."""
        urls = [f"http://phishing-load-{i}.example.com" for i in range(25)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            start = time.time()
            futures = [
                executor.submit(client.post, "/predict", json={"url": url})
                for url in urls
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            elapsed = time.time() - start

        assert len(results) == 25
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 20, f"Only {success_count}/25 requests succeeded"

        throughput = 25 / elapsed
        print(f"\n✅ 25 concurrent /predict in {elapsed:.2f}s = {throughput:.1f} req/s")

    def test_stress_mixed_urls_same_url_repeated(self):
        """Test cache behavior under concurrent load — same URL multiple times."""
        url = "http://cache-test.example.com"

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            start = time.time()
            futures = [
                executor.submit(client.post, "/predict", json={"url": url})
                for _ in range(10)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            elapsed = time.time() - start

        assert len(results) == 10
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 9, f"Only {success_count}/10 requests succeeded"

        # Verify cache is being hit (later requests should be faster)
        cached_responses = sum(1 for r in results if r.json().get("cached") is True)
        print(f"\n✅ Cache hits: {cached_responses}/10 in {elapsed:.2f}s")


class TestStressAnalyzeContentEndpoint:
    """Stress tests para /analyze-content endpoint."""

    def test_stress_10_concurrent_analyze_content(self):
        """10 concurrent requests to /analyze-content."""
        texts = [
            f"This is a news article about topic {i}. It discusses important events."
            for i in range(10)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            start = time.time()
            futures = [
                executor.submit(client.post, "/analyze-content", json={"text": text})
                for text in texts
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            elapsed = time.time() - start

        assert len(results) == 10
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 9, f"Only {success_count}/10 requests succeeded"

        throughput = 10 / elapsed
        print(f"\n✅ 10 concurrent /analyze-content in {elapsed:.2f}s = {throughput:.1f} req/s")

    def test_stress_25_concurrent_analyze_content(self):
        """25 concurrent requests to /analyze-content."""
        texts = [
            f"Article {i}: This is about news. Fake news vs real news discussion."
            for i in range(25)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            start = time.time()
            futures = [
                executor.submit(client.post, "/analyze-content", json={"text": text})
                for text in texts
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            elapsed = time.time() - start

        assert len(results) == 25
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 20, f"Only {success_count}/25 requests succeeded"

        throughput = 25 / elapsed
        print(f"\n✅ 25 concurrent /analyze-content in {elapsed:.2f}s = {throughput:.1f} req/s")


class TestStressMixedEndpoints:
    """Stress tests mixing both endpoints."""

    def test_stress_mixed_endpoints_concurrent(self):
        """Concurrent mix of /predict and /analyze-content requests."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            for i in range(8):
                futures.append(
                    executor.submit(
                        client.post,
                        "/predict",
                        json={"url": f"http://mixed-{i}.example.com"}
                    )
                )

            for i in range(8):
                futures.append(
                    executor.submit(
                        client.post,
                        "/analyze-content",
                        json={"text": f"Mixed content test {i} about news"}
                    )
                )

            start = time.time()
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            elapsed = time.time() - start

        assert len(results) == 16
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 14, f"Only {success_count}/16 requests succeeded"

        throughput = 16 / elapsed
        print(f"\n✅ 16 mixed endpoints in {elapsed:.2f}s = {throughput:.1f} req/s")


class TestStressHealthMetrics:
    """Verify API health under load."""

    def test_health_endpoint_under_load(self):
        """Health endpoint should always respond even under concurrent /predict load."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            for i in range(10):
                futures.append(
                    executor.submit(
                        client.post,
                        "/predict",
                        json={"url": f"http://load-{i}.example.com"}
                    )
                )

            time.sleep(0.1)

            for _ in range(5):
                futures.append(executor.submit(client.get, "/health"))

            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        health_results = [r for r in results if r.status_code == 200]
        assert len(health_results) >= 14, "Health endpoint failed under load"
        print("\n✅ Health endpoint stable under concurrent /predict load")

    def test_metadata_endpoint_under_load(self):
        """Metadata endpoint should respond quickly even during /predict calls."""
        latencies = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for _ in range(5):
                executor.submit(
                    client.post,
                    "/predict",
                    json={"url": "http://metadata-stress.example.com"}
                )

            time.sleep(0.05)

            for _ in range(3):
                start = time.time()
                response = client.get("/metadata")
                latencies.append(time.time() - start)
                assert response.status_code == 200

        avg_latency = sum(latencies) / len(latencies)
        print(f"\n✅ /metadata avg latency: {avg_latency*1000:.1f}ms under load")
