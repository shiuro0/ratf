# Checklist Sebelum Eksperimen Final

## Konfigurasi

- [ ] `.env` dibuat dengan `python scripts/init_env.py`.
- [ ] `STRICT_STARTUP=true`.
- [ ] `STORAGE_BACKEND=redis` dan `ALLOW_MEMORY_FALLBACK=false`.
- [ ] Kedua API memakai file `.env` yang sama.
- [ ] Hanya `API_MODE`, port, Redis database, dan log path yang berbeda.
- [ ] Bobot dan threshold sudah dibekukan setelah pilot.
- [ ] Batch non-burst tidak melebihi soft rate-limit agar S1, S2, S6, S11, S12, S14, dan S15 tidak terkontaminasi S7.
- [ ] Config fingerprint dicatat.
- [ ] Scenario-contract dan security-protocol fingerprint dicatat.

## Lingkungan

- [ ] Docker Desktop aktif.
- [ ] Container berstatus sehat.
- [ ] Aplikasi berat dan proses latar belakang ditutup.
- [ ] Jam sistem benar.
- [ ] Standard dan R-ATF tidak diuji secara bersamaan untuk pengukuran performa.
- [ ] k6 dijalankan pada VUS 1, 10, 25, dan 50, masing-masing lima pengulangan selama 60 detik.
- [ ] Urutan Standard/R-ATF diselang-seling pada pengulangan ganjil dan genap.
- [ ] Think time 0,6 detik dipertahankan agar rate limit per token family tidak menjadi variabel pengganggu.

## Integritas data

- [ ] `preflight.py` menghasilkan `passed: true`.
- [ ] `preflight_pair.py` menghasilkan `passed: true`.
- [ ] 26 test lulus di dalam container.
- [ ] Tidak ada `request_error`.
- [ ] Tidak ada nonce/idempotency duplikat di luar S4.
- [ ] `experiment_quality.json` menghasilkan `passed: true`.
- [ ] S7 setup seluruhnya allow dan fase attack seluruhnya block/429/`rate_limit_exceeded`.
- [ ] `scenario_contract_validation.passed` bernilai true untuk S1–S15.
- [ ] Audit hash chain valid.
- [ ] Token mentah dan device secret tidak muncul dalam audit log.
- [ ] Manifest tersedia untuk setiap CSV.
- [ ] Setiap run k6 memiliki summary JSON, log, API stats CSV, dan Redis stats CSV.
- [ ] `performance_comparison.json` menghasilkan `data_quality_passed: true`.
- [ ] `final_validation_report.json` menghasilkan `passed: true`.

## Penulisan hasil

- [ ] Pilot tidak ditulis sebagai hasil final.
- [ ] Exact RPR hanya dihitung dari S4.
- [ ] Verify dilaporkan sebagai challenge, bukan disamakan sepenuhnya dengan block.
- [ ] Kontrol standar dan kontribusi R-ATF dibedakan.
- [ ] Hasil negatif atau skenario yang lolos tetap dilaporkan.
- [ ] Overhead p95 dihitung sebagai selisih milidetik R-ATF dikurangi Standard, bukan total response time dan bukan hanya persentase.
- [ ] CPU, memori, dan throughput dilaporkan secara deskriptif tanpa membuat ambang baru setelah data diketahui.
