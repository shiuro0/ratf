# Contoh Pemakaian API

## 1. Mendaftarkan perangkat sintetis

Header:

```text
X-Enrollment-Key: <DEVICE_ENROLLMENT_KEY>
```

Payload:

```json
{
  "user_id": "user_001",
  "client_id": "small-shop-client",
  "device_name": "Office Windows Device",
  "role": "customer",
  "allowed_scopes": "catalog:read orders:read orders:write payments:write"
}
```

Role dan allowed scope disimpan di registry. Token endpoint tidak menerima peningkatan role secara langsung.

## 2. Menerbitkan JWT atau opaque token

```json
{
  "user_id": "user_001",
  "client_id": "small-shop-client",
  "device_id": "dev_...",
  "device_secret": "<secret hasil enrollment>",
  "token_format": "jwt",
  "scope": "catalog:read orders:read orders:write",
  "ttl_seconds": 900
}
```

Ganti `token_format` menjadi `opaque` untuk reference token. Requested scope harus merupakan subset policy perangkat.

## 3. Membuat order

```json
{
  "customer_id": "cust_1001",
  "items": [{"sku": "SKU-RED-01", "quantity": 2}],
  "shipping_method": "regular"
}
```

Protected request harus memiliki access token, client/device ID, timestamp, nonce, HMAC device signature, dan idempotency key.

## 4. Pembayaran

```json
{
  "order_id": "ord_...",
  "amount": 350000,
  "currency": "IDR",
  "payment_method": "virtual_account"
}
```

Order harus tersedia dan token harus memiliki `payments:write`.
