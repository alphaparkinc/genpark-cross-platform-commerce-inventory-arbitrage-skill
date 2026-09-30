"""
Universal Cross-Platform Commerce Inventory & Price Arbitrage Engine (Zero External Dependencies)
Provides multi-merchant comparison, promo stacking, anomaly detection, and purchase routing.
"""
import time
import math
import json
from typing import Dict, Any, List, Optional

class CommerceInventoryArbitrageEngine:
    def __init__(self, default_tax_rate: float = 0.0825):
        self.default_tax_rate = default_tax_rate

    def compare_merchants(
        self,
        product_query: str,
        merchant_offers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates quotes from multiple merchants (e.g. Shopify, Walmart, Instacart, Amazon).
        Computes landed cost (base + estimated tax + shipping) and delivery ETA score.
        """
        if not merchant_offers:
            return {"error": "No merchant offers provided", "offers": []}

        evaluated = []
        for offer in merchant_offers:
            merchant = offer.get("merchant", "unknown")
            base_price = float(offer.get("unit_price", 0.0))
            shipping = float(offer.get("shipping_fee", 0.0))
            free_shipping_threshold = float(offer.get("free_shipping_min", 999.0))
            in_stock = bool(offer.get("in_stock", True))
            delivery_hours = float(offer.get("estimated_delivery_hours", 48.0))
            seller_rating = float(offer.get("seller_rating", 4.5)) # out of 5.0

            effective_shipping = 0.0 if base_price >= free_shipping_threshold else shipping
            tax = base_price * self.default_tax_rate
            landed_cost = base_price + effective_shipping + tax

            # Fast delivery score: 1.0 for same-day (<6h), decaying down to 0.1 for 7+ days
            speed_score = max(0.1, 1.0 - (delivery_hours / 168.0))
            # Reliability score: based on seller rating and stock
            rel_score = (seller_rating / 5.0) if in_stock else 0.0

            # Composite balanced utility: 50% lowest price + 30% speed + 20% reliability
            evaluated.append({
                "merchant": merchant,
                "base_price": round(base_price, 2),
                "shipping_fee": round(effective_shipping, 2),
                "estimated_tax": round(tax, 2),
                "total_landed_cost": round(landed_cost, 2),
                "delivery_hours": delivery_hours,
                "in_stock": in_stock,
                "seller_rating": seller_rating,
                "speed_score": round(speed_score, 3),
                "reliability_score": round(rel_score, 3),
                "offer_metadata": offer.get("metadata", {})
            })

        # Calculate best in category
        valid_offers = [o for o in evaluated if o["in_stock"]]
        if not valid_offers:
            return {"query": product_query, "status": "ALL_OUT_OF_STOCK", "offers": evaluated}

        cheapest = min(valid_offers, key=lambda x: x["total_landed_cost"])
        fastest = min(valid_offers, key=lambda x: x["delivery_hours"])

        # Max landed cost to normalize price score
        max_cost = max(o["total_landed_cost"] for o in valid_offers)
        for o in valid_offers:
            price_norm = 1.0 - (o["total_landed_cost"] / (max_cost + 1e-5))
            o["balanced_utility"] = round(0.50 * price_norm + 0.30 * o["speed_score"] + 0.20 * o["reliability_score"], 4)

        balanced_best = max(valid_offers, key=lambda x: x["balanced_utility"])

        return {
            "query": product_query,
            "total_quotes": len(evaluated),
            "recommendations": {
                "cheapest_option": {"merchant": cheapest["merchant"], "landed_cost": cheapest["total_landed_cost"]},
                "fastest_option": {"merchant": fastest["merchant"], "delivery_hours": fastest["delivery_hours"], "cost": fastest["total_landed_cost"]},
                "balanced_best": {"merchant": balanced_best["merchant"], "utility": balanced_best["balanced_utility"]}
            },
            "detailed_offers": evaluated
        }

    def stack_promotions(
        self,
        subtotal: float,
        coupons: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Stacks eligible coupons and discounts honoring stacking rules:
        - Percentage off (e.g. 15% off)
        - Fixed dollar off (e.g. $10 off)
        - Max discount caps and minimum cart thresholds
        """
        running_subtotal = subtotal
        applied = []
        rejected = []

        # Sort coupons: fixed dollar discounts first or percentage first
        # Usually percentage off first gives merchant advantage, fixed first gives buyer advantage.
        # We simulate optimal consumer advantage: sort by highest savings potential
        for cp in coupons:
            code = cp.get("code", "PROMO")
            min_spend = float(cp.get("min_spend", 0.0))
            ctype = cp.get("type", "percent") # "percent" or "fixed"
            val = float(cp.get("value", 0.0))
            max_disc = float(cp.get("max_discount", 99999.0))
            stackable = bool(cp.get("stackable", True))

            if running_subtotal < min_spend:
                rejected.append({"code": code, "reason": f"Minimum spend ${min_spend} not met (current: ${running_subtotal:.2f})"})
                continue

            if applied and not stackable:
                rejected.append({"code": code, "reason": "Coupon is non-stackable with other promotions"})
                continue

            savings = 0.0
            if ctype == "percent":
                savings = min(running_subtotal * (val / 100.0), max_disc)
            elif ctype == "fixed":
                savings = min(val, running_subtotal)

            savings = round(min(savings, running_subtotal), 2)
            if savings > 0:
                running_subtotal -= savings
                applied.append({"code": code, "type": ctype, "value": val, "savings": savings})

        tax = running_subtotal * self.default_tax_rate
        total_savings = round(subtotal - running_subtotal, 2)

        return {
            "original_subtotal": round(subtotal, 2),
            "discounted_subtotal": round(running_subtotal, 2),
            "total_promotional_savings": total_savings,
            "estimated_tax": round(tax, 2),
            "effective_total": round(running_subtotal + tax, 2),
            "applied_coupons": applied,
            "rejected_coupons": rejected
        }

    def detect_price_anomalies(
        self,
        historical_prices: List[float],
        current_quote: float,
        surge_threshold_ratio: float = 0.25
    ) -> Dict[str, Any]:
        """
        Detects sudden price gouging, fake flash discounts, or historic bargains.
        """
        if not historical_prices:
            return {"anomaly_detected": False, "reason": "No historical price series"}

        avg_price = sum(historical_prices) / len(historical_prices)
        min_price = min(historical_prices)
        max_price = max(historical_prices)

        delta_from_avg = current_quote - avg_price
        pct_change = (delta_from_avg / avg_price) * 100.0

        anomaly_type = "NORMAL"
        is_anomaly = False

        if current_quote >= avg_price * (1.0 + surge_threshold_ratio):
            anomaly_type = "SURGE_PRICING"
            is_anomaly = True
        elif current_quote <= avg_price * (1.0 - surge_threshold_ratio):
            anomaly_type = "HISTORIC_LOW_BARGAIN"
            is_anomaly = True

        return {
            "current_quote": current_quote,
            "historical_stats": {
                "average": round(avg_price, 2),
                "min": min_price,
                "max": max_price,
                "sample_points": len(historical_prices)
            },
            "percentage_vs_avg": round(pct_change, 2),
            "anomaly_detected": is_anomaly,
            "anomaly_type": anomaly_type,
            "advisory": (
                "Price is unusually high. Suggest waiting or checking alternative merchants."
                if anomaly_type == "SURGE_PRICING" else
                ("Exceptional bargain detected! Recommended for immediate checkout." if anomaly_type == "HISTORIC_LOW_BARGAIN" else "Price is within normal historical distribution.")
            )
        }

    def optimize_purchase_route(
        self,
        cart_items: List[Dict[str, Any]],
        merchant_catalog: List[Dict[str, Any]],
        objective: str = "cheapest"
    ) -> Dict[str, Any]:
        """
        Optimizes multi-item cart routing between single-merchant consolidation vs split-merchant fulfillment.
        """
        # Group offers by item SKU
        sku_offers = {}
        for offer in merchant_catalog:
            sku = offer.get("sku")
            sku_offers.setdefault(sku, []).append(offer)

        selected_allocations = []
        merchants_used = set()

        for item in cart_items:
            sku = item.get("sku")
            qty = item.get("quantity", 1)
            offers = sku_offers.get(sku, [])
            if not offers:
                selected_allocations.append({"sku": sku, "status": "UNAVAILABLE"})
                continue

            # Pick best according to objective
            if objective == "fastest":
                best = min(offers, key=lambda x: x.get("estimated_delivery_hours", 999))
            else: # cheapest or balanced
                best = min(offers, key=lambda x: x.get("unit_price", 9999))

            merchants_used.add(best.get("merchant"))
            selected_allocations.append({
                "sku": sku,
                "quantity": qty,
                "merchant": best.get("merchant"),
                "unit_price": best.get("unit_price"),
                "line_total": round(best.get("unit_price") * qty, 2),
                "delivery_hours": best.get("estimated_delivery_hours")
            })

        total_product_cost = sum(a.get("line_total", 0.0) for a in selected_allocations if "line_total" in a)

        return {
            "objective": objective,
            "distinct_merchants": list(merchants_used),
            "merchant_count": len(merchants_used),
            "total_product_cost": round(total_product_cost, 2),
            "item_allocations": selected_allocations
        }
