# Reason Code

## Validasi token dan otorisasi

| Reason code | Makna |
|---|---|
| `missing_bearer_token` | Authorization Bearer tidak tersedia |
| `jwt_*` | JWT gagal validasi teknis |
| `jwt_not_registered` | JWT valid kriptografis tetapi tidak ada pada registry |
| `opaque_token_unknown` | Opaque token tidak ditemukan |
| `token_expired` | Token telah kedaluwarsa |
| `token_revoked` | Token tidak aktif atau telah diganti/dicabut |
| `registry_claim_mismatch` | Klaim JWT berbeda dari registry |
| `client_id_mismatch` | Client request berbeda dari client token |
| `insufficient_scope` | Scope tidak cukup |

## Device proof dan replay

| Reason code | Makna |
|---|---|
| `device_id_missing` | Device ID tidak tersedia |
| `token_device_binding_mismatch` | Token terikat pada perangkat lain |
| `request_timestamp_missing` | Timestamp tidak dikirim |
| `request_timestamp_outside_window` | Timestamp melewati toleransi |
| `device_signature_invalid` | HMAC proof tidak valid |
| `nonce_missing` | Nonce wajib tetapi tidak tersedia |
| `nonce_reused` | Nonce sudah diklaim |
| `idempotency_key_missing` | Endpoint transaksi tidak memiliki key |
| `idempotency_key_reused` | Transaksi menggunakan key lama |
| `rate_limit_exceeded` | Hard rate limit terlampaui |

## R-ATF

| Reason code | Makna |
|---|---|
| `trust_score_allow` | Skor berada pada rentang allow |
| `trust_score_verify` | Skor memerlukan step-up verification |
| `trust_score_block` | Skor berada pada rentang block |
| `ip_changed_same_network` | Perubahan IP masih satu subnet |
| `ip_changed_new_network` | IP baru belum pernah diizinkan |
| `user_agent_minor_change` | Perubahan versi/family kecil |
| `user_agent_changed_same_bound_device` | User-agent berubah pada device yang sama |
| `token_context_multiple_novelty` | Beberapa konteks baru muncul bersama |
| `request_frequency_elevated` | Frekuensi melewati soft limit |
| `request_frequency_high` | Frekuensi sangat tinggi |
