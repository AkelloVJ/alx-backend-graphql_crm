import requests
from datetime import datetime
from pathlib import Path
from celery import shared_task

# GraphQL endpoint
GRAPHQL_URL = "http://localhost:8000/graphql"

# Report log file
REPORT_LOG = Path("/tmp/crm_report_log.txt")

@shared_task
def generate_crm_report():
    """
    Generate a weekly CRM report with total customers, orders, and revenue.
    """
    try:
        # GraphQL query to fetch CRM statistics
        query = """
        query {
            allCustomers {
                totalCount
            }
            allOrders {
                totalCount
                edges {
                    node {
                        totalAmount
                    }
                }
            }
        }
        """
        
        # Make GraphQL request
        response = requests.post(
            GRAPHQL_URL,
            json={"query": query},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract data from GraphQL response
            customers_data = data.get("data", {}).get("allCustomers", {})
            orders_data = data.get("data", {}).get("allOrders", {})
            
            total_customers = customers_data.get("totalCount", 0)
            total_orders = orders_data.get("totalCount", 0)
            
            # Calculate total revenue
            total_revenue = 0
            orders_edges = orders_data.get("edges", [])
            for edge in orders_edges:
                order = edge.get("node", {})
                total_amount = order.get("totalAmount", 0)
                if total_amount:
                    total_revenue += float(total_amount)
            
            # Format timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create report message
            report_message = f"{timestamp} - Report: {total_customers} customers, {total_orders} orders, ${total_revenue:.2f} revenue\n"
            
            # Log the report
            try:
                REPORT_LOG.parent.mkdir(parents=True, exist_ok=True)
                with REPORT_LOG.open("a", encoding="utf-8") as f:
                    f.write(report_message)
            except Exception as e:
                print(f"Error writing to log file: {e}")
            
            return {
                "status": "success",
                "customers": total_customers,
                "orders": total_orders,
                "revenue": total_revenue
            }
            
        else:
            error_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error: GraphQL request failed with status {response.status_code}\n"
            try:
                REPORT_LOG.parent.mkdir(parents=True, exist_ok=True)
                with REPORT_LOG.open("a", encoding="utf-8") as f:
                    f.write(error_message)
            except Exception:
                pass
            
            return {
                "status": "error",
                "message": f"GraphQL request failed with status {response.status_code}"
            }
            
    except Exception as e:
        error_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error: {str(e)}\n"
        try:
            REPORT_LOG.parent.mkdir(parents=True, exist_ok=True)
            with REPORT_LOG.open("a", encoding="utf-8") as f:
                f.write(error_message)
        except Exception:
            pass
        
        return {
            "status": "error",
            "message": str(e)
        }
