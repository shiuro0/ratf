# Laporan Validasi Paket v6.0 Final Fix

## Pemeriksaan yang telah dilakukan pada paket

- seluruh modul Python berhasil dikompilasi;
- 26 unit, integration, regression, dan analyzer test lulus;
- S7 diuji pada mode Standard dan R-ATF dengan hard limit kecil;
- tiga request awal S7 `allow` dan dua request berikutnya `block` HTTP 429;
- request counter S7 bertambah 1–5 dan reason code akhir
  `rate_limit_exceeded`, bukan `device_signature_invalid`;
- hash body GET runner sama dengan SHA-256 body kosong middleware;
- mutasi JWT mempertahankan struktur token dan mengubah signature secara pasti;
- dataset sintetis dengan 15 kontrak lengkap lulus pada kedua mode;
- reason/status S7 yang salah membuat quality gate gagal;
- satu skenario yang hilang membuat quality gate gagal;
- import `scripts` dapat dijalankan melalui `python -m pytest` di layout Docker;
- analyzer kinerja tetap melewati regression test added-p95.

## Pemeriksaan yang tetap wajib dilakukan oleh peneliti

Lingkungan validasi ini tidak menggantikan uji pada Docker Desktop dan perangkat
yang akan dicatat di BAB IV. Sebelum hasil disebut final, peneliti wajib
menjalankan:

1. build container dari paket v6.0;
2. 26 test di dalam container;
3. preflight kedua sistem dan preflight pasangan;
4. pilot S1–S15 pada Redis;
5. k6 beserta CPU/memori;
6. lima pengulangan keamanan final;
7. pemeriksaan `final_validation_report.json`.

Jumlah test adalah bukti cakupan regresi, bukan bukti bahwa prototipe bebas
seluruh kerentanan. Klaim skripsi harus dibatasi pada konfigurasi, skenario,
data sintetis, dan perangkat eksperimen yang benar-benar digunakan.
