# Panduan Integrasi Hasil ke BAB IV

Dokumen ini memisahkan bukti implementasi, keamanan, dan kinerja supaya BAB IV
menjawab rumusan masalah tanpa melebihkan temuan.

## 1. Bukti implementasi yang tidak memerlukan eksperimen final

Bagian implementasi dapat ditulis dari inspeksi kode dan konfigurasi:

- arsitektur Standard API dan R-ATF;
- urutan kontrol middleware;
- formula, bobot, aturan diskret, dan threshold trust score;
- token registry, replacement/revocation, scope, nonce, idempotency, device proof;
- context history yang hanya belajar setelah allow;
- adaptive policy engine dan audit hash chain;
- pemetaan endpoint serta fungsi komponen.

Nyatakan sebagai “hasil implementasi/inspeksi kode”, bukan “hasil pengujian”.

## 2. Bukti yang wajib berasal dari pengujian

Tabel unit test, lingkungan, kualitas data, keputusan per skenario, confusion
matrix, metrik keamanan, latency, throughput, failure rate, CPU, dan memori harus
diisi dari output aktual. Jangan mempertahankan angka contoh apabila run final
memberikan nilai berbeda.

## 3. Empat tabel keamanan

Setelah final validation lulus, gunakan berkas pada
`results/final/bab4_exports`:

| Tabel | Berkas sumber otomatis | Fungsi pembahasan |
|---|---|---|
| 4.15 Hasil Final per Skenario | `Tabel_4.15_Hasil_Final_per_Skenario.csv` | Keputusan dan reason code S1–S15 |
| 4.16 Confusion Matrix Final | `Tabel_4.16_Confusion_Matrix_Final.csv` | TP, FN, FP, TN, challenge |
| 4.17 Ringkasan Metrik Keamanan | `Tabel_4.17_Ringkasan_Metrik_Keamanan_Final.csv` | RPR, contextual detection, FPR, friction, audit |
| 4.18 Latensi Skrip Keamanan | `Tabel_4.18_Latensi_Skrip_Keamanan_Pendukung.csv` | Informasi pendukung, bukan klaim performa utama |

Sumber tabel yang disarankan:

> Sumber: Hasil pengujian keamanan final, diolah penulis (2026).

## 4. Angka pemeriksaan jumlah

Dengan N = 200 dan lima pengulangan, setiap sistem harus mempunyai:

- 15.000 baris primer = 15 × 200 × 5;
- 610 baris setup terkendali;
- 15.610 total baris;
- 1.000 baris primer untuk setiap skenario;
- S7: 300 setup allow dan 1.000 attack block/429 per sistem.

S3 current-token acceptance sekarang berlabel setup. Oleh karena itu jumlah
baris evaluatif yang benar adalah 15.000, bukan 15.005. Perubahan ini membuat
setiap skenario menyumbang ukuran sampel primer yang sama.

## 5. Arah pembahasan per kelompok skenario

- **Kontrol sah:** S1, S2, S11, dan S15 menunjukkan acceptance dan false
  positive. Bahas block dan verify pada request sah secara terpisah.
- **Kontrol deterministik:** S3, S4, S5, S7, S8, S9, S10, dan S13 harus
  diatribusikan pada registry, replay control, proof, rate limit, signature,
  expiration, revocation, atau scope yang ada pada kedua sistem.
- **Nilai tambah R-ATF:** S6, S12, dan S14 membandingkan Standard yang lolos
  dengan R-ATF yang melakukan verify akibat perubahan konteks.

Untuk S7, jelaskan bahwa perbaikan bukan menaikkan keberhasilan secara artifisial.
Perbaikan menyelaraskan body hash GET sehingga request dapat mencapai komponen
yang memang sedang diuji. Nonce dan request ID tetap baru; karena itu block 429
dapat diatribusikan pada rate limiter.

## 6. Kinerja dan resource

Gunakan `results/performance/final/performance_summary.csv` dan
`performance_comparison.json`. Added p95 dihitung dalam milidetik untuk setiap
VU. Failure rate, throughput, CPU, dan memori tidak boleh diambil dari CSV
skenario keamanan.

Jika `criteria_passed` false tetapi `data_quality_passed` true, laporkan hasil
tersebut apa adanya dan bahas penyebabnya. Jika `data_quality_passed` false,
data belum layak digunakan.

## 7. Batas klaim ilmiah

Gunakan ungkapan “pada prototipe dan skenario terkontrol yang diuji”. Hindari
“100% aman”, “tanpa celah”, atau “lebih baik daripada seluruh machine learning”.
Perbandingan dengan pembelajaran mesin pada penelitian ini bersifat
karakteristik desain: R-ATF unggul dalam keterjelasan aturan, reproduksibilitas,
auditabilitas, dan kebutuhan data pelatihan nol pada ruang lingkup prototipe;
bukan bukti empiris mengalahkan semua model ML tanpa baseline ML yang diuji.
