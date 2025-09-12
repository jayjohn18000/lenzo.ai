# pocketflow/nodes/plan_ticket.py
import os, yaml
from pocketflow.store import SharedStore


class PlanTicket:
    name = "plan"

    def __init__(self, ticket_path: str):
        self.ticket_path = ticket_path

    def run(self, store: SharedStore) -> None:
        with open(self.ticket_path, "r") as f:
            ticket = yaml.safe_load(f)
        store.context["ticket"] = ticket

        # quick validations + inferred paths
        repo = store.repo_root
        paths = {
            "main": os.path.join(repo, "backend", "main.py"),
            "routes_v1": os.path.join(repo, "backend", "api", "v1", "routes.py"),
            "auth_api_key": os.path.join(repo, "backend", "auth", "api_key.py"),
        }
        store.context["paths"] = paths
        store.save()
