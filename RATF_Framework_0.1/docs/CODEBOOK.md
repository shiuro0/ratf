# Codebook v6.0

## Klasifikasi

| Istilah | Definisi operasional |
|---|---|
| TP | Request berlabel serangan menghasilkan `block` atau `verify` |
| FN | Request berlabel serangan menghasilkan `allow` |
| FP | Request sah menghasilkan `block` |
| TN | Request sah menghasilkan `allow` |
| CHALLENGE | Request sah menghasilkan `verify` |
| SETUP | Request pembentuk kondisi; tidak masuk confusion matrix |
| Strict FPR | FP / seluruh request sah × 100% |
| Challenge rate | CHALLENGE / seluruh request sah × 100% |
| Friction rate | (FP + CHALLENGE) / seluruh request sah × 100% |
| Exact replay prevention | TP khusus serangan S4 |
| Contextual detection | Block/verify pada S6, S12, dan S14 |
| Contract match | Keputusan, status HTTP, dan reason code sesuai kontrak skenario/mode |

## Kolom CSV skenario

| Kolom | Makna |
|---|---|
| `run_id` | Identitas unik satu run |
| `row_sequence` | Urutan global baris dalam run, dimulai dari 1 |
| `scenario_phase_index` | Urutan baris di dalam pasangan skenario–fase |
| `scenario` | Nama stabil S1–S15 |
| `expected_label` | `setup`, `legit`, atau `attack` |
| `expected_outcome` | Ekspektasi rancangan yang dicatat runner |
| `expected_control` | Kontrol yang menjadi fokus skenario |
| `status_code` | HTTP status aktual |
| `decision` | `allow`, `verify`, `block`, atau `request_error` |
| `reason_code` | Alasan utama keputusan |
| `trust_score` | Skor 0–1 bila dihitung |
| `request_count_window` | Nilai counter rate limit setelah request |
| `client_latency_ms` | Waktu sisi runner; hanya informasi pendukung |
| `http_method`, `endpoint` | Bentuk request aktual |
| `request_id` | ID request; nilai harus unik di luar exact replay S4 |
| `nonce_sha256`, `idempotency_sha256` | Hash bukti replay tanpa nilai mentah |
| `config_fingerprint` | SHA-256 konfigurasi nonrahasia sistem |
| `shared_experiment_fingerprint` | SHA-256 konfigurasi bersama pembanding |
| `system_mode` | `standard` atau `ratf` |

## Fingerprint protokol

Manifest menyimpan `protocol_version`, `scenario_contract_fingerprint`,
`security_protocol`, dan `security_protocol_fingerprint`. Fingerprint protokol
mencakup jumlah sampel, batch size, hard limit S7, delay, versi kontrak, dan 15
ekspektasi skenario. Run dengan fingerprint berbeda tidak boleh digabung.
