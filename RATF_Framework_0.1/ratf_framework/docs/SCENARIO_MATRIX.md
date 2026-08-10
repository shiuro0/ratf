# Matriks Kontrak 15 Skenario v6.0

Kontrak ini membedakan **hasil yang diharapkan berdasarkan rancangan** dari
**hasil aktual yang baru boleh ditulis setelah pengujian**. Quality gate
memeriksa keputusan, HTTP status, dan reason code secara tepat.

| Kode | Kondisi primer | Label | Standard | R-ATF | Reason code utama |
|---|---|---|---|---|---|
| S1 | JWT normal, proof baru | Sah | Allow/201 | Allow/201 | `standard_controls_passed` / `trust_score_allow` |
| S2 | Perubahan subnet /24 dan versi aplikasi kecil | Sah | Allow/201 | Allow/201 | `standard_controls_passed` / `trust_score_allow` |
| S3 | Token lama setelah access-token replacement | Serangan | Block/401 | Block/401 | `token_revoked` |
| S4 | Nonce, request ID, timestamp, payload, dan idempotency diulang | Serangan | Block/409 | Block/409 | `nonce_reused` |
| S5 | Token dicuri tanpa secret perangkat terikat | Serangan | Block/401 | Block/401 | `token_device_binding_mismatch` |
| S6 | Token dan secret perangkat disalin setelah pemakaian sah | Serangan | Allow/201 | Verify/401 | `standard_controls_passed` / `trust_score_verify` |
| S7 | Burst GET dengan nonce dan request ID baru | Serangan | Block/429 | Block/429 | `rate_limit_exceeded` |
| S8 | Signature JWT dimutasi | Serangan | Block/401 | Block/401 | `jwt_InvalidSignatureError` |
| S9 | JWT kedaluwarsa | Serangan | Block/401 | Block/401 | `jwt_ExpiredSignatureError` |
| S10 | Token dicabut melalui registry | Serangan | Block/401 | Block/401 | `token_revoked` |
| S11 | Opaque token normal, proof baru | Sah | Allow/201 | Allow/201 | `standard_controls_passed` / `trust_score_allow` |
| S12 | Opaque token dan secret perangkat disalin | Serangan | Allow/201 | Verify/401 | `standard_controls_passed` / `trust_score_verify` |
| S13 | Token tanpa scope `payments:write` | Serangan | Block/403 | Block/403 | `insufficient_scope` |
| S14 | Token dan secret dicuri sebelum protected request pertama | Serangan | Allow/201 | Verify/401 | `standard_controls_passed` / `trust_score_verify` |
| S15 | Roaming sah, device dan user-agent tetap | Sah | Allow/201 | Allow/201 | `standard_controls_passed` / `trust_score_allow` |

## Kesetaraan jumlah sampel

Pada setiap run, seluruh S1–S15 memiliki tepat `--requests` baris primer.
Request pembentuk kondisi diberi label `setup` dan dikeluarkan dari confusion
matrix:

- S2, S6, dan S12: satu setup per batch token;
- S3: satu current-token acceptance control;
- S4: satu request sah sebelum exact replay;
- S7: tepat `BURST_HARD_LIMIT` request setup yang harus allow.

S7 kemudian menghasilkan tepat `--requests` baris serangan setelah hard limit.
Untuk konfigurasi hard limit 60 dan `--requests 200`, satu run memuat 60 setup
S7 dan 200 serangan S7. Seluruh request S7 menggunakan GET, body kosong, signature
yang sesuai, serta nonce dan request ID baru. Dengan demikian, replay detector
dan device proof tidak boleh menjadi penyebab block pada S7.

## Aturan atribusi hasil

S3, S4, S5, S7, S8, S9, S10, dan S13 menguji kontrol deterministik yang sama
pada kedua sistem. Keberhasilan skenario ini tidak boleh diklaim sebagai nilai
tambah khusus trust scoring.

S6, S12, dan S14 menguji nilai tambah R-ATF setelah request melewati kontrol
deterministik. S2 dan S15 menjadi kontrol false positive saat konteks pengguna
sah berubah. Keputusan `verify` dilaporkan terpisah dari `block` karena
konsekuensi operasionalnya berbeda.
