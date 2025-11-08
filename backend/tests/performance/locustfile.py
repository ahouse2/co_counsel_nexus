from locust import HttpUser, task, between

class BackendUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def get_graph_neighbor(self):
        self.client.get("/graph/neighbor?id=some-initial-node")
