# Skema Audit Log v6.0

| Field | Keterangan |
|---|---|
| `schema_version` | versi skema log |
| `config_fingerprint` | hash konfigurasi nonrahasia |
| `system_mode`, `storage_backend` | lingkungan keputusan |
| `request_id`, `run_id`, `scenario_label` | identitas eksperimen |
| `token_id_hash`, `token_format` | identitas token tanpa token mentah |
| `token_family_id_hash`, `subject_hash` | identitas yang di-HMAC/hash |
| `device_id_hash`, `source_ip_hash`, `user_agent_hash` | konteks yang dilindungi |
| `endpoint`, `method`, `body_hash` | metadata request |
| `nonce_hash`, `idempotency_key_hash` | bukti replay tanpa nilai mentah |
| `trust_score`, `score_components` | hasil R-ATF |
| `request_count_window` | frekuensi request |
| `decision`, `reason_code`, `reason_codes` | keputusan dan alasan |
| `latency_ms`, `replay_flag` | performa dan replay |
| `sequence`, `previous_hash`, `entry_hash` | hash chain integritas log |

Audit log tidak memuat access token, payload JWT lengkap, device secret, signing secret, admin token, atau payload pembayaran lengkap.

Pada mode eksperimen, response juga memuat header keputusan, reason code,
fingerprint, dan `X-RATF-Request-Count`. Header counter digunakan analyzer untuk
menunjukkan bahwa S7 benar-benar mencapai rate limiter; header tersebut bukan
kontrol keamanan tambahan dan tidak diaktifkan sebagai kontrak produksi.
