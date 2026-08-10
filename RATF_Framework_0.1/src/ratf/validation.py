from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]


def validate_order(payload: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    customer_id = payload.get("customer_id")
    if not isinstance(customer_id, str) or not customer_id.strip() or len(customer_id) > 64:
        errors.append("customer_id must be a non-empty string of at most 64 characters")
    items = payload.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        errors.append("items must contain between 1 and 20 entries")
    else:
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"items[{index}] must be an object")
                continue
            sku = item.get("sku")
            quantity = item.get("quantity")
            if not isinstance(sku, str) or not sku.strip() or len(sku) > 64:
                errors.append(f"items[{index}].sku is invalid")
            if not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 100:
                errors.append(f"items[{index}].quantity must be an integer between 1 and 100")
    if payload.get("shipping_method", "regular") not in {"regular", "express", "pickup"}:
        errors.append("shipping_method is not supported")
    return ValidationResult(not errors, errors)


def validate_payment(payload: dict[str, Any], max_amount: int) -> ValidationResult:
    errors: list[str] = []
    order_id = payload.get("order_id")
    amount = payload.get("amount")
    if not isinstance(order_id, str) or not order_id.strip() or len(order_id) > 80:
        errors.append("order_id is invalid")
    if not isinstance(amount, int) or isinstance(amount, bool) or not 1 <= amount <= max_amount:
        errors.append(f"amount must be an integer between 1 and {max_amount}")
    if payload.get("currency", "IDR") != "IDR":
        errors.append("only IDR is supported in this prototype")
    if payload.get("payment_method", "virtual_account") not in {
        "virtual_account",
        "bank_transfer",
        "cash_on_delivery",
    }:
        errors.append("payment_method is not supported")
    return ValidationResult(not errors, errors)
