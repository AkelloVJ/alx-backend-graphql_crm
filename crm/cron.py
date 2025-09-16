import json
from datetime import datetime
from pathlib import Path

import requests
from gql.transport.requests import RequestsHTTPTransport
from gql import gql, Client


GRAPHQL_URL = "http://localhost:8000/graphql"
HEARTBEAT_LOG = Path("/tmp/crm_heartbeat_log.txt")
LOW_STOCK_LOG = Path("/tmp/low_stock_updates_log.txt")


def _timestamp() -> str:
    return datetime.now().strftime("%d/%m/%Y-%H:%M:%S")


def log_crm_heartbeat() -> None:
    message = f"{_timestamp()} CRM is alive\n"
    try:
        HEARTBEAT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with HEARTBEAT_LOG.open("a", encoding="utf-8") as f:
            f.write(message)
    except Exception:
        pass

    # Optional GraphQL health check (query hello)
    try:
        query = "query { hello }"
        resp = requests.post(
            GRAPHQL_URL,
            json={"query": query},
            timeout=5,
        )
        _ = resp.json()
    except Exception:
        # keep heartbeat log even if GraphQL check fails
        return


def updatelowstock() -> None:
    mutation = """
    mutation UpdateLowStock($inc: Int){
      updateLowStockProducts(incrementBy: $inc){
        ok
        message
        updatedProducts { id name stock }
      }
    }
    """
    try:
        resp = requests.post(
            GRAPHQL_URL,
            json={"query": mutation, "variables": {"inc": 10}},
            timeout=15,
        )
        data = resp.json()
        updates = data.get("data", {}).get("updateLowStockProducts", {})
        products = updates.get("updatedProducts", [])
        lines = [
            f"{_timestamp()} Updated: {p.get('name')} -> stock {p.get('stock')}\n"
            for p in products
        ]
    except Exception as e:
        lines = [f"{_timestamp()} Error updating low stock: {e}\n"]

    try:
        LOW_STOCK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOW_STOCK_LOG.open("a", encoding="utf-8") as f:
            for line in lines:
                f.write(line)
    except Exception:
        pass


