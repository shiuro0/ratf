# Protokol Eksperimen v6.0

## Objek pembanding

1. **Standard API**, port 5000 dan Redis database 0.
2. **R-ATF API**, port 5001 dan Redis database 1.

Keduanya memakai registry token, status active/revoked, replacement policy,
scope, device proof HMAC, timestamp, nonce, idempotency, rate limit, validasi
payload, dan audit hash chain. Mode R-ATF menambahkan trust score, context
history, dan adaptive policy engine. Fingerprint konfigurasi bersama harus sama.

## Urutan eksperimen

1. Buat `.env` satu kali dan jalankan container sampai sehat.
2. Jalankan 26 regression test dengan `python -m pytest -q`.
3. Jalankan preflight individual dan preflight pasangan.
4. Jalankan pilot lima sampel primer per skenario pada kedua sistem.
5. Pastikan quality gate S1–S15 dan validasi S7 lulus.
6. Bekukan kode, `.env`, bobot, threshold, alokasi Docker, dan protokol.
7. Jalankan k6 pada 1, 10, 25, dan 50 VUs; lima pengulangan; 15 detik warm-up;
   60 detik measured run; urutan sistem diselang-seling.
8. Jalankan pengujian keamanan sebanyak 200 request primer per skenario dan
   lima pengulangan per sistem. Urutan Standard/R-ATF juga diselang-seling.
9. Agregasikan hanya run dengan fingerprint protokol identik.
10. Ekspor tabel BAB IV hanya setelah final validation report lulus.

## Aturan sampel dan fase

Skenario non-burst dibagi ke token-family batch kecil supaya rate limit tidak
menjadi variabel pengganggu. Semua skenario mempunyai jumlah baris primer yang
sama. Baris setup tidak dihitung sebagai TP/FN/FP/TN/CHALLENGE.

S7 selalu dibentuk sebagai:

```text
fase setup  : 1 .. BURST_HARD_LIMIT       -> allow
fase attack : BURST_HARD_LIMIT+1 .. +N    -> block, HTTP 429,
                                               rate_limit_exceeded
```

Setiap request S7 memakai proof GET atas SHA-256 body kosong, nonce baru,
request ID baru, token family yang sama, endpoint yang sama, dan window yang
sama. Analyzer memeriksa `request_count_window` secara berurutan.

## Metrik keamanan

- exact replay prevention khusus S4;
- contextual detection/challenge pada S6, S12, dan S14;
- overall attack prevention/challenge;
- hard rejection dan attack challenge rate;
- strict false positive rate;
- legitimate challenge dan friction rate;
- confusion matrix;
- exact scenario-contract match;
- audit integrity dan kelengkapan bukti.

## Metrik kinerja

- p95, rata-rata, median, dan p99 latency k6;
- throughput business request;
- business failure rate;
- mean/p95 CPU serta mean/max memori API dan Redis;
- added p95 = mean p95 R-ATF − mean p95 Standard pada VU yang sama.

Latensi pada CSV skenario keamanan hanya informasi pendukung. Klaim kinerja
utama harus berasal dari k6 karena endpoint, payload, durasi, VU, think time,
dan urutan pengujiannya dikendalikan.

## Kriteria pra-registrasi

| Metrik | Target |
|---|---:|
| Exact replay prevention S4 | >= 95% |
| Strict FPR | <= 5% |
| S7 setelah hard limit | 100% block/429/`rate_limit_exceeded` |
| S8, S9, S10, dan S13 | 100% sesuai kontrak |
| Scenario-contract match | 100% |
| Audit hash chain | Valid |
| Kenaikan p95 R-ATF dari baseline | <= 20% pada setiap tingkat VU |
| Penurunan throughput R-ATF | <= 15% pada setiap tingkat VU |
| Business failure rate | < 1% pada kedua sistem |

Kriteria tidak boleh diubah setelah eksperimen utama dimulai. Hasil yang tidak
memenuhi target tetap merupakan hasil penelitian yang sah apabila
`data_quality_passed` bernilai true.

## Ancaman validitas yang dikendalikan

- stale result dicegah dengan mewajibkan folder keluaran kosong;
- missing run dicegah melalui `--expected-runs`/`--expected-repetitions`;
- perbedaan konfigurasi dicegah melalui shared fingerprint;
- perubahan protokol dicegah melalui scenario-contract dan protocol fingerprint;
- bias urutan dikurangi melalui counterbalancing;
- residual Redis state pada k6 dibersihkan pada kedua sistem sebelum setiap run;
- profile poisoning dicegah karena context history hanya diperbarui setelah allow;
- data pilot dipisahkan dari hasil final.
