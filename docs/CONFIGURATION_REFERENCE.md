# Referensi Konfigurasi

## Konfigurasi aplikasi/library

| Konfigurasi | Fungsi |
|---|---|
| `RATF_CORE_CONFIG` | Objek `CoreConfig` sebagai policy global |
| `RATF_POLICIES` | Mapping named policy per-endpoint |
| `RATF_IDENTITY_PROVIDER` | Adapter validasi token milik aplikasi |
| `RATF_STORAGE` | Implementasi penyimpanan state, umumnya Redis |
| `RATF_STEP_UP_HANDLER` | Hook challenge untuk keputusan `verify` |
| `RATF_AUDIT_LOGGER` | Sink audit framework |
| `RATF_SHADOW_MODE` | Observasi keputusan kontekstual tanpa enforcement |
| `RATF_AUTHZEN_ENABLED` | Membuka evaluation service lintas bahasa |
| `RATF_AUTHZEN_API_KEY` | Kredensial service-to-service untuk evaluation client |
| `RATF_DASHBOARD_ENABLED` | Mengaktifkan dashboard opsional |

Parameter `ratf.policy()`:

| Parameter | Arti |
|---|---|
| `name` | Nama stabil yang masuk ke response dan audit |
| `weights` | Bobot `ip`, `device`, `time`, `frequency`, `token_history` |
| `thresholds.verify` | Skor minimum untuk meminta verifikasi tambahan |
| `thresholds.allow` | Skor minimum untuk langsung mengizinkan request |
| `shadow_mode` | Override shadow mode hanya untuk policy tersebut |
| `burst_soft_limit` | Titik penalti frekuensi pada window |
| `burst_hard_limit` | Batas keras request pada window |
| `hard_burst_block` | Menjadikan frekuensi tinggi sebagai pelanggaran kritis |

Nilai yang tidak diberikan mewarisi `CoreConfig` global. Profile tidak mengubah
global config dan akan divalidasi saat aplikasi dimulai.

## Konfigurasi server penelitian lama

| Variabel | Fungsi |
|---|---|
| `STRICT_STARTUP` | Menghentikan startup bila secret/threshold tidak valid |
| `STORAGE_BACKEND` | Redis untuk eksperimen, memory hanya untuk test |
| `ALLOW_MEMORY_FALLBACK` | Harus false pada eksperimen final |
| `REDIS_STARTUP_TIMEOUT_SECONDS` | Batas waktu entrypoint menunggu Redis sebelum Gunicorn dijalankan |
| `REDIS_STARTUP_INTERVAL_SECONDS` | Jeda antarpercobaan koneksi Redis saat startup |
| `REPLACE_PREVIOUS_ACCESS_TOKEN` | Mengganti token lama pada family yang sama |
| `MAX_ACTIVE_TOKENS_PER_FAMILY` | Batas token aktif |
| `NONCE_REQUIRED` | Mewajibkan nonce |
| `DEVICE_PROOF_REQUIRED` | Mewajibkan HMAC proof |
| `IDEMPOTENCY_REQUIRED` | Mewajibkan idempotency pada transaksi |
| `TIMESTAMP_SKEW_SECONDS` | Toleransi waktu request |
| `REPLAY_WINDOW_SECONDS` | TTL nonce/idempotency |
| `BURST_*` | Fixed-window rate limit |
| `ALLOW_THRESHOLD`, `VERIFY_THRESHOLD` | Batas policy |
| `WEIGHT_*` | Bobot formula trust score |
| `EXPERIMENT_MODE` | Mengaktifkan header simulasi dengan experiment key |
| `TRUST_PROXY_HEADERS` | Jangan aktif kecuali API berada di belakang proxy tepercaya |
| `LOG_CONTEXT_MODE` | Raw, masked, atau hash |

Jangan mengubah konfigurasi setelah eksperimen utama dimulai. Config fingerprint digunakan untuk mendeteksi perubahan. Aturan pembekuan ini berlaku untuk reproduksi eksperimen, bukan untuk aplikasi pengguna yang memang menggunakan policy per-endpoint.
