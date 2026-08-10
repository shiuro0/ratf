# Contoh integrasi aplikasi Flask

Contoh ini menunjukkan integrasi langsung pada aplikasi, bukan dashboard.
Access token divalidasi oleh OAuth/OIDC introspection milik aplikasi, state
adaptif disimpan pada Redis, dan endpoint pembayaran memakai policy tersendiri.

Environment minimum:

```text
REDIS_URL=redis://127.0.0.1:6379/0
OIDC_INTROSPECTION_URL=https://idp.example.com/oauth2/introspect
OIDC_CLIENT_ID=resource-server
OIDC_CLIENT_SECRET=isi-dari-secret-manager
TOKEN_HASH_SECRET=secret-acak-minimal-32-byte
AUDIT_LOG_SECRET=secret-acak-minimal-32-byte
LOG_PATH=results/production_audit.jsonl
```

Gunakan secret manager dan HTTPS pada penerapan sebenarnya. Endpoint
`/auth/step-up` masih placeholder karena proses MFA harus dihubungkan ke
Identity Provider yang digunakan aplikasi.
