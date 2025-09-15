#!/usr/bin/env python3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport


GRAPHQL_URL = "http://localhost:8000/graphql"
LOG_FILE = Path("/tmp/order_reminders_log.txt")


def timestamp() -> str:
    return datetime.now().strftime("%d/%m/%Y-%H:%M:%S")


def main() -> int:
    try:
        transport = RequestsHTTPTransport(url=GRAPHQL_URL, retries=2, verify=True)
        client = Client(transport=transport, fetch_schema_from_transport=False)

        since_dt = datetime.utcnow() - timedelta(days=7)
        since_iso = since_dt.isoformat() + "Z"

        query = gql(
            """
            query PendingOrders($since: DateTime!){
              allOrders(orderDateGte: $since){
                edges{ node{ id customer{ email } } }
              }
            }
            """
        )
        result = client.execute(query, variable_values={"since": since_iso})
        edges = result.get("allOrders", {}).get("edges", [])
        lines = [
            f"{timestamp()} Reminder for order {n['node']['id']} -> {n['node']['customer']['email']}\n"
            for n in edges
            if n and n.get("node") and n["node"].get("customer")
        ]
    except Exception as e:
        lines = [f"{timestamp()} Error querying GraphQL: {e}\n"]

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            for line in lines:
                f.write(line)
    except Exception:
        pass

    print("Order reminders processed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


