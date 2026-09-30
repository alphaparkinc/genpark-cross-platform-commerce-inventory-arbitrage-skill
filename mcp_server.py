"""MCP Server for Cross-Platform Commerce Inventory Arbitrage Engine."""
import sys
import json
from client import CommerceInventoryArbitrageEngine

engine = CommerceInventoryArbitrageEngine()

def handle_call_tool(params):
    name = params.get("name")
    args = params.get("arguments", {})
    if name != "arbitrage_commerce_inventory":
        raise ValueError(f"Unknown tool: {name}")

    action = args.get("action", "compare_merchants")
    if action == "compare_merchants":
        return engine.compare_merchants(
            product_query=args.get("product_query", "item"),
            merchant_offers=args.get("merchant_offers", [])
        )
    elif action == "optimize_purchase_route":
        return engine.optimize_purchase_route(
            cart_items=args.get("cart_items", []),
            merchant_catalog=args.get("merchant_offers", []),
            objective=args.get("optimization_objective", "cheapest")
        )
    elif action == "stack_promotions":
        return engine.stack_promotions(
            subtotal=float(args.get("subtotal", 0.0)),
            coupons=args.get("coupons", [])
        )
    elif action == "detect_price_anomalies":
        return engine.detect_price_anomalies(
            historical_prices=args.get("historical_prices", []),
            current_quote=float(args.get("subtotal", 0.0))
        )
    else:
        raise ValueError(f"Invalid action: {action}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Running self-test...")
        quotes = [
            {"merchant": "Shopify Store A", "unit_price": 49.99, "shipping_fee": 5.0, "free_shipping_min": 60.0, "estimated_delivery_hours": 48},
            {"merchant": "Walmart", "unit_price": 52.00, "shipping_fee": 0.0, "estimated_delivery_hours": 24},
            {"merchant": "Instacart Express", "unit_price": 54.00, "shipping_fee": 3.99, "estimated_delivery_hours": 2}
        ]
        res = engine.compare_merchants("Sony Headphones", quotes)
        assert res["total_quotes"] == 3
        promos = engine.stack_promotions(100.0, [{"code": "SAVE10", "type": "fixed", "value": 10.0}])
        assert promos["discounted_subtotal"] == 90.0
        print("Self-test PASSED!")
        sys.exit(0)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            msg_id = req.get("id")
            method = req.get("method")
            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "CommerceInventoryArbitrageEngine", "version": "1.0.0"},
                        "capabilities": {"tools": {}}
                    }
                }
            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": [{
                            "name": "arbitrage_commerce_inventory",
                            "description": "Multi-merchant inventory arbitrage: compare real-time pricing and delivery across merchants, calculate stacked coupons, detect price surges, and optimize purchase routing.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "action": {"type": "string", "enum": ["compare_merchants", "optimize_purchase_route", "stack_promotions", "detect_price_anomalies"]},
                                    "product_query": {"type": "string"},
                                    "merchant_offers": {"type": "array"},
                                    "optimization_objective": {"type": "string"},
                                    "cart_items": {"type": "array"},
                                    "coupons": {"type": "array"},
                                    "subtotal": {"type": "number"},
                                    "historical_prices": {"type": "array"}
                                },
                                "required": ["action"]
                            }
                        }]
                    }
                }
            elif method == "tools/call":
                res = handle_call_tool(req.get("params", {}))
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
                }
            else:
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            print(json.dumps(resp), flush=True)
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}
            print(json.dumps(err_resp), flush=True)

if __name__ == "__main__":
    main()
