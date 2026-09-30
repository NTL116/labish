"""AI-visible tool wrappers over the SAP integration client."""

from app.integrations.sap.service_layer import SAPServiceLayerClient


def sap_order_tool(order_data: dict) -> str:
    """Agent interface wrapper for creating SAP sales orders."""
    client = SAPServiceLayerClient()
    result = client.create_sales_order(order_data)
    if result.success:
        return f"Order successfully pushed to SAP. DocEntry: {result.doc_entry}"
    return f"SAP order failed: {result.error}"
