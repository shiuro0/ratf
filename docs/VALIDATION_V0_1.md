# Validasi R-ATF 0.1

Tanggal eksekusi: 9 Agustus 2026.

Tabel berikut adalah snapshot validasi sebelum showcase terpaket ditambahkan.

| Kategori | Lulus | Isi utama |
|---|---:|---|
| Regression | 2/2 | request normal dan exact replay pada server penelitian lama |
| Integration | 3/3 | Flask extension, bobot kustom, shadow mode, step-up hook |
| Interoperability | 2/2 | kontrak AuthZEN dan request nyata dari proses Node.js |
| Security | 4/4 | token hilang/palsu, scope, replay saat shadow, audit hash chain |
| Performance smoke | 1/1 | eksekusi microbenchmark core berhasil |
| **Total** | **12/12** | tidak ada failure, error, atau skip |

Wheel awal `ratf_framework-0.1.1-py3-none-any.whl` berhasil dibangun dan memuat
modul core, Flask extension, template dashboard, serta spesifikasi OpenAPI.
Validation integration juga memeriksa policy per-endpoint, pemilihan policy
melalui AuthZEN, dan pencatatan nama policy pada response.

Source distribution awal `ratf_framework-0.1.1.tar.gz` diekstrak pada direktori
sementara dan `run_all_checks.py` dijalankan dari hasil ekstraksi tersebut.
Seluruh 12 pemeriksaan kembali lulus, sehingga validasi tidak bergantung pada
folder kerja asal.

## Pemeriksaan tambahan showcase (10 Agustus 2026)

Suite integration sekarang berisi enam test dan seluruhnya lulus. Pemeriksaan
memastikan UHAMKA Mart serta Control Room termuat dari package, status kesiapan
tidak salah mengklaim produksi, policy endpoint dapat dikembalikan ke bobot dan
ambang penelitian, token demonstrasi lokal tampil lengkap, serta alur HTTP
menghasilkan `allow`, `verify`, `block`, dan `nonce_reused` sesuai kondisi client.

Wheel final `ratf_framework-0.1.3-py3-none-any.whl` dipasang pada virtual
environment terpisah dengan working directory di luar repository. UHAMKA Mart,
Control Room, ringkasan hasil penelitian, token demonstrasi, template terpaket,
dan entry point `ratf-showcase = ratf.showcase:main` berhasil dimuat dari
`site-packages`. Seluruh 15 validation test lulus. S1–S15 dan eksperimen k6 tidak
dijalankan ulang karena perubahan ini berada pada packaging, aplikasi showcase,
dan tampilan; bukti eksperimen lama tetap dipertahankan.

Microbenchmark pengembangan menjalankan 5.000 evaluasi core pada memory storage.
Nilai hasil eksekusi tersimpan pada
`results/v0_1_validation/validation_summary.json`. Angka tersebut hanya menjadi
smoke benchmark untuk mendeteksi regresi besar pada core. Ia tidak mengukur
Gunicorn, jaringan, Redis, CPU container, memori container, atau konkurensi k6,
sehingga tidak menggantikan hasil performa utama BAB IV.

## Pemeriksaan paket 0.1.4 (11 Agustus 2026)

Revisi UHAMKA Mart dan Control Room diperiksa kembali tanpa mengubah core
keputusan. Seluruh 15 test tetap lulus: 2 regresi, 6 integrasi, 2
interoperabilitas, 4 keamanan, dan 1 performance smoke. Kedua template lolos
pemeriksaan struktur HTML, tidak memiliki ID ganda, dan seluruh JavaScript
inline lolos pemeriksaan sintaks Node.js.

Wheel `ratf_framework-0.1.4-py3-none-any.whl` dan source distribution
`ratf_framework-0.1.4.tar.gz` dibangun dari salinan sumber yang bersih. Isi
template di dalam wheel dibandingkan byte per byte dengan file revisi dan
hasilnya sama. Wheel kemudian dipasang pada virtual environment baru di luar
repository; versi distribusi, import `ratf`, UHAMKA Mart, Control Room, API
bootstrap, konteks demonstrasi, ringkasan penelitian, dan konfigurasi policy
berhasil dimuat. `pip check` tidak menemukan dependency rusak dan `twine check`
lulus untuk kedua artefak distribusi.

## Hubungan dengan hasil penelitian lama

Validasi v0.1 menjawab pertanyaan apakah hasil penelitian dapat dikemas,
dimodifikasi, dan dipakai dari aplikasi lain. Data S1–S15 dan 40 measured run k6
tetap menjadi dasar klaim efektivitas keamanan dan overhead pada penelitian.
Kedua kelompok bukti tidak dicampurkan:

- `results/research_final`: eksperimen Standard API vs R-ATF;
- `results/v0_1_validation`: validasi rekayasa framework 0.1;
- `results/scenario_logs`: keluaran demonstrasi per skenario.

Setelah diimpor, raw security data dianalisis ulang pada salinan sementara.
Standard dan R-ATF masing-masing kembali menghasilkan 15.000 baris evaluatif,
metric summary identik, dan quality gate lulus. Empat puluh measured run k6 juga
menghasilkan comparison identik dengan arsip dan seluruh kriteria tetap lulus.
