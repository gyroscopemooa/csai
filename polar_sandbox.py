"""Operator-only Polar sandbox checkout probe. Never provisions CS AI access."""
import os
from uuid import UUID

import httpx
from fastapi import Request

from app import app, require, require_operator
from billing import quote


def checkout_payload(product_id, amount):
    product_id = str(UUID(product_id))
    return {
        'products': [product_id],
        'prices': {product_id: [{'amount_type': 'fixed', 'price_amount': amount, 'price_currency': 'krw'}]},
        'allow_discount_codes': False,
        'allow_trial': False,
    }


@app.post('/api/operator/polar/sandbox-checkout')
def sandbox_checkout(body: dict, request: Request):
    require_operator(request)
    require(os.getenv('POLAR_SANDBOX_CHECKOUT_ENABLED') == '1', 'Polar 샌드박스가 비활성화되어 있습니다.', 503)
    kind, items, amount = quote(body)
    token = os.getenv('POLAR_SANDBOX_TOKEN', '')
    product = os.getenv('POLAR_SANDBOX_MONTHLY_PRODUCT_ID' if kind == 'subscription' else 'POLAR_SANDBOX_ONE_TIME_PRODUCT_ID', '')
    try:
        payload = checkout_payload(product, amount)
    except ValueError:
        require(False, 'Polar 샌드박스 상품 ID 설정이 필요합니다.', 503)
    require(token, 'Polar 샌드박스 토큰 설정이 필요합니다.', 503)
    try:
        response = httpx.post('https://sandbox-api.polar.sh/v1/checkouts/', json=payload,
                              headers={'Authorization': f'Bearer {token}'}, timeout=15)
        response.raise_for_status()
        checkout = response.json()
    except (httpx.HTTPError, ValueError):
        require(False, 'Polar 샌드박스 Checkout 생성에 실패했습니다.', 502)
    require(checkout.get('amount') == amount and str(checkout.get('currency', '')).lower() == 'krw' and checkout.get('url'),
            'Polar Checkout 금액 또는 통화가 서버 견적과 다릅니다.', 502)
    return {'id': checkout['id'], 'url': checkout['url'], 'amount': amount, 'items': items, 'sandbox': True}
