# Protokol dan Panduan Pengujian Final v6.0

**Rancang Bangun Framework Keamanan Adaptif Berbasis Aturan Logika Trust
Scoring untuk Mencegah Penyalahgunaan Token pada API Microservices**

Zahrul Fuadi — 2203015088  
Program Studi Teknik Informatika, FTII UHAMKA — 2026

Panduan ini dipakai untuk memperoleh data BAB IV yang dapat ditelusuri ulang.
Angka hasil tidak ditentukan oleh dokumen; seluruh tabel diisi dari keluaran
aktual yang lolos quality gate.

## A. Apa yang sudah tersedia

| Komponen | Status pada paket | Tindakan peneliti |
|---|---|---|
| Implementasi Standard dan R-ATF | Tersedia | Build dari paket v6.0 |
| Kontrak S1–S15 | Tersedia | Jangan diubah setelah pilot |
| Koreksi S7 GET proof | Tersedia | Konfirmasi melalui pilot Redis |
| Unit/regression/integration test | 26 test | Jalankan ulang di container |
| Preflight individual dan pasangan | Tersedia | Wajib lulus |
| Analyzer dan quality gate | Tersedia | Wajib `passed: true` |
| Eksperimen keamanan berulang | Tersedia | Jalankan 200 × 5 per sistem |
| k6 dan resource collector | Tersedia | Jalankan 4 VU × 5 × 2 sistem |
| Ekspor empat tabel BAB IV | Otomatis | Gunakan setelah final validation |

Paket final tidak menyertakan data lama sebagai hasil resmi. Hal ini mencegah
hasil pra-perbaikan S7 tercampur dengan data final.

## B. Persiapan lingkungan

Gunakan satu komputer, satu versi Docker Desktop, satu alokasi CPU/RAM, dan mode
daya yang sama. Catat prosesor, core/thread, RAM, sistem operasi, Python, Docker,
Docker Compose, dan k6.

```powershell
python --version
docker --version
docker compose version
k6 version
```

Tutup aplikasi berat dan sinkronisasi besar. Pastikan jam Windows benar dan
laptop tersambung ke daya.

## C. Inisialisasi dan build bersih

Masuk ke folder yang berisi `docker-compose.yml`, lalu:

```powershell
python .\scripts\init_env.py
docker compose down --remove-orphans
docker compose build --no-cache
docker compose up -d
docker compose ps
```

`.env` harus dibuat sekali dan dipertahankan selama satu rangkaian eksperimen.
Jangan mengunggah atau menyalinnya ke skripsi.

Jika muncul `.env not found`, jalankan kembali `python .\scripts\init_env.py`
dari folder proyek yang benar. Jika container restart:

```powershell
docker compose logs --tail=200 --no-color standard-api ratf-api redis
```

Periksa health dari host:

```powershell
$standard = Invoke-RestMethod http://localhost:5000/health
$ratf = Invoke-RestMethod http://localhost:5001/health
$standard
$ratf
$standard.shared_experiment_fingerprint -eq $ratf.shared_experiment_fingerprint
```

Nilai terakhir harus `True`; kedua status harus `ok`; backend harus `redis`;
mode harus `standard` dan `ratf`.

## D. Regression test dan preflight

Gunakan `python -m pytest`, bukan executable `pytest` langsung:

```powershell
docker compose exec -T ratf-api python -m pytest -q
```

Hasil paket yang telah divalidasi adalah `26 passed`. Jika impor `scripts`
gagal, berarti container masih memakai image lama. Ulangi build bersih pada
Bagian C.

Lanjutkan dengan:

```powershell
docker compose exec -T standard-api python scripts/preflight.py `
  --base-url http://localhost:5000 --expected-mode standard

docker compose exec -T ratf-api python scripts/preflight.py `
  --base-url http://localhost:5001 --expected-mode ratf

docker compose exec -T ratf-api python scripts/preflight_pair.py `
  --standard-url http://standard-api:5000 `
  --ratf-url http://ratf-api:5001
```

Ketiganya harus `passed: true`.

## E. Pilot seluruh 15 skenario

### E.1 Standard API

```powershell
docker compose exec -T standard-api python scripts/run_scenarios.py `
  --base-url http://localhost:5000 `
  --expected-mode standard `
  --requests 5 `
  --batch-size 10 `
  --reset `
  --output results/standard_pilot_v6.csv

docker compose exec -T standard-api python scripts/analyze_results.py `
  --input results/standard_pilot_v6.csv `
  --output-dir results/standard_pilot_v6_analysis
```

### E.2 R-ATF

```powershell
docker compose exec -T ratf-api python scripts/run_scenarios.py `
  --base-url http://localhost:5001 `
  --expected-mode ratf `
  --requests 5 `
  --batch-size 10 `
  --reset `
  --output results/ratf_pilot_v6.csv

docker compose exec -T ratf-api python scripts/analyze_results.py `
  --input results/ratf_pilot_v6.csv `
  --output-dir results/ratf_pilot_v6_analysis
```

Opsi `--burst-requests` tidak diperlukan lagi. Runner membaca hard limit dari
API dan otomatis membuat 60 setup + N serangan S7.

### E.3 Pemeriksaan manual S7

```powershell
$stdS7 = Import-Csv .\results\standard_pilot_v6.csv |
  Where-Object scenario -eq 'S7_RAPID_BURST'

$ratfS7 = Import-Csv .\results\ratf_pilot_v6.csv |
  Where-Object scenario -eq 'S7_RAPID_BURST'

$stdS7 | Group-Object expected_label,decision,status_code,reason_code |
  Select-Object Count,Name

$ratfS7 | Group-Object expected_label,decision,status_code,reason_code |
  Select-Object Count,Name

$stdS7 | Select-Object row_sequence,expected_label,request_count_window,status_code,decision,reason_code
```

Untuk N = 5, setiap sistem harus mempunyai:

- 60 setup: allow, HTTP 200;
- 5 attack: block, HTTP 429, `rate_limit_exceeded`;
- counter berurutan 1–65;
- nol `device_signature_invalid`.

Kemudian baca:

```powershell
Get-Content .\results\standard_pilot_v6_analysis\experiment_quality.json
Get-Content .\results\ratf_pilot_v6_analysis\experiment_quality.json
```

Pastikan `passed`, `scenario_contract_validation.passed`, dan
`s7_rate_limit_validation_passed` semuanya true. Jika tidak, jangan lanjut ke
final dan jangan mengedit CSV secara manual.

## F. Code freeze

Setelah pilot lulus:

1. jangan ubah source code, threshold, bobot, batch size, atau `.env`;
2. simpan hash/fingerprint dan tanggal;
3. arsipkan folder proyek sebagai code freeze;
4. pindahkan pilot ke folder terpisah;
5. pastikan `results/performance/final` dan `results/final` belum berisi run lama.

Skrip final sengaja berhenti jika menemukan bukti lama. Pindahkan seluruh
folder lama ke nama bertanggal, misalnya `final_2026-07-19_pre_fix`; jangan
menggabungkan isinya.

## G. Pengujian kinerja

Kinerja dijalankan sebelum keamanan final karena reset state pada load test.

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\run_performance_experiment.ps1 `
  -VusLevels 1,10,25,50 `
  -Repetitions 5 `
  -Duration 60s `
  -WarmupDuration 15s `
  -SleepSeconds 0.6
```

Skrip menghasilkan 40 measured run, mengganti urutan sistem, dan mengambil
statistik API/Redis tiap detik. Kedua state sistem di-reset sebelum setiap run
agar Redis memory tidak membawa residu sistem sebelumnya.

Periksa:

```powershell
Get-Content .\results\performance\final\performance_comparison.json
```

`data_quality_passed` harus true. `criteria_passed` boleh false dan harus
dilaporkan apa adanya apabila data tetap valid.

## H. Pengujian keamanan final

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\run_experiment.ps1 `
  -Requests 200 `
  -Repetitions 5 `
  -LegitimateDelay 0.05 `
  -BatchSize 10
```

Skrip menjalankan preflight ulang, melakukan counterbalancing, menganalisis
setiap run, mengagregasikan tepat lima run, membandingkan sistem, mengekspor
empat tabel, dan membuat final validation report. Native command yang gagal
langsung menghentikan eksperimen.

## I. Pemeriksaan jumlah dan integritas

Dengan N = 200 dan R = 5, **per sistem**:

| Pemeriksaan | Nilai yang harus ada |
|---|---:|
| Skenario primer | 15 |
| Baris primer per skenario | 1.000 |
| Total baris primer | 15.000 |
| Total setup | 610 |
| Total baris termasuk setup | 15.610 |
| S7 setup allow | 300 |
| S7 attack block/429 | 1.000 |

S3 current-token acceptance berlabel setup sehingga confusion matrix tidak lagi
memiliki tambahan lima TN. Ini adalah koreksi kesetaraan sampel; total baris
tetap 15.610.

Periksa bukti akhir:

```powershell
Get-Content .\results\final\standard_all_runs_analysis\experiment_quality.json
Get-Content .\results\final\ratf_all_runs_analysis\experiment_quality.json
Get-Content .\results\final\system_comparison.json
Get-Content .\results\final\final_validation_report.json
```

Semua quality report dan `valid_comparison` harus true. Audit chain harus valid;
request error dan unclassified row harus nol; duplicate di luar S4 harus nol;
fingerprint protokol harus sama.

## J. Memindahkan hasil ke empat tabel BAB IV

Gunakan keluaran otomatis berikut, bukan angka pendahuluan:

```text
results/final/bab4_exports/Tabel_4.15_Hasil_Final_per_Skenario.csv
results/final/bab4_exports/Tabel_4.16_Confusion_Matrix_Final.csv
results/final/bab4_exports/Tabel_4.17_Ringkasan_Metrik_Keamanan_Final.csv
results/final/bab4_exports/Tabel_4.18_Latensi_Skrip_Keamanan_Pendukung.csv
results/final/bab4_exports/TABEL_BAB4_FINAL.md
```

Tabel 4.18 harus diberi keterangan “informasi pendukung”. Tabel/grafik performa
utama diambil dari k6. Sumber tabel:

> Sumber: Hasil pengujian keamanan final, diolah penulis (2026).

## K. Prinsip penulisan hasil

- Bedakan hasil implementasi dari hasil eksperimen.
- Bedakan `verify` dari `block`.
- Beri atribusi S3/S4/S5/S7/S8/S9/S10/S13 pada kontrol deterministik bersama.
- Gunakan S6/S12/S14 untuk nilai tambah kontekstual R-ATF.
- Gunakan S2/S15 untuk false-positive control.
- Jangan mengubah angka, menghapus outlier tanpa alasan, atau memilih run yang
  paling mendukung hipotesis.
- Batasi klaim pada prototipe lokal, data sintetis, dan skenario terkontrol.
- Jangan menulis “bebas celah” atau “100% aman”.
