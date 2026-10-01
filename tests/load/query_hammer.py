from locust import HttpUser, task, between


class QueryHammerUser(HttpUser):
    wait_time = between(0.01, 0.05)  # High throughput simulation

    @task
    def hammer_query(self):
        payload = {
            "query": "What is total revenue for FY2025 in Note 17?",
            "conversation_id": "load_test_conv_001"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": "tenant_load_test",
            "X-Tenant-Tier": "enterprise"
        }
        with self.client.post("/api/query", json=payload, headers=headers, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Expected 200 status code, got {resp.status_code}")
