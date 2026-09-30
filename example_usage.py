"""Example usage for CommerceInventoryArbitrageEngine."""
import json
from client import CommerceInventoryArbitrageEngine

def main():
    print("=== Cross-Platform Commerce Inventory Arbitrage Engine Demo ===")
    engine = CommerceInventoryArbitrageEngine()

    # 1. Multi-Merchant Price & Delivery Evaluation
    offers = [
        {"merchant": "Shopify Direct D2C", "unit_price": 79.0, "shipping_fee": 7.50, "free_shipping_min": 100.0, "estimated_delivery_hours": 72, "seller_rating": 4.9},
        {"merchant": "Walmart Supercenter", "unit_price": 82.50, "shipping_fee": 0.0, "free_shipping_min": 35.0, "estimated_delivery_hours": 36, "seller_rating": 4.6},
        {"merchant": "Instacart 2-Hour", "unit_price": 86.0, "shipping_fee": 5.99, "free_shipping_min": 999.0, "estimated_delivery_hours": 2, "seller_rating": 4.8}
    ]

    print("\n--- Multi-Merchant Comparison (Meta Muse Consumer Agent) ---")
    comp = engine.compare_merchants("AirPods Pro USB-C", offers)
    print("Recommendations:")
    print(json.dumps(comp["recommendations"], indent=2))

    # 2. Coupon Stacking Simulation
    print("\n--- Promotional Stacking Engine ---")
    coupons = [
        {"code": "WELCOME15", "type": "percent", "value": 15.0, "min_spend": 50.0, "stackable": True},
        {"code": "LOYALTY5", "type": "fixed", "value": 5.0, "min_spend": 20.0, "stackable": True}
    ]
    stacked = engine.stack_promotions(82.50, coupons)
    print(f"Original: ${stacked['original_subtotal']} -> After Discounts: ${stacked['discounted_subtotal']} (Saved: ${stacked['total_promotional_savings']})")

    # 3. Surge Pricing Anomaly Detection
    print("\n--- Surge Price Anomaly Check ---")
    history = [75.0, 78.0, 74.5, 76.0, 79.0]
    surge_check = engine.detect_price_anomalies(history, 115.0)
    print(f"Current Quote: $115.0 -> Anomaly: {surge_check['anomaly_type']} ({surge_check['advisory']})")

if __name__ == "__main__":
    main()
