# Catatan Penyesuaian BAB IV untuk Framework v6.0

Dokumen ini menjadi jembatan antara perbaikan implementasi dan revisi narasi
BAB IV sebelum hasil final tersedia.

## Perubahan yang dapat ditulis sebagai hasil tahap Act

Pilot terdahulu menunjukkan S7 terblokir sebelum mencapai rate limiter. Audit
alur request menemukan perbedaan representasi body GET: runner menandatangani
serialisasi objek kosong, sedangkan middleware menerima byte body kosong.
Perbaikan menyamakan canonical body hash dengan data yang benar-benar dikirim.
Setelah itu, S7 dipisahkan menjadi fase setup sampai hard limit dan fase serangan
setelah hard limit. Setiap request tetap memakai nonce dan request ID baru agar
block dapat diatribusikan pada rate limit.

Perbaikan juga memperluas quality gate ke seluruh S1–S15. Keberhasilan sekarang
tidak dinilai hanya dari allow/verify/block, tetapi juga dari HTTP status, reason
code, jumlah sampel, mode, urutan fase, fingerprint, dan integritas audit.

## Penyesuaian tabel pra-uji

| Tabel | Penyesuaian v6.0 |
|---|---|
| Ringkasan unit/integration test | Isi hasil aktual; paket memiliki 26 test, tetapi tetap salin output container |
| Lingkungan pengujian | Isi versi aktual setelah final run |
| Kualitas data | `evaluated_rows` menjadi 15.000 per sistem; total tetap 15.610 |
| Hasil per skenario | Ganti seluruh angka dengan ekspor otomatis final |
| Confusion matrix | S3 current-token control tidak lagi menambah TN karena berlabel setup |
| Metrik keamanan | Gunakan denominator baru yang setara antarskenario |
| Latensi keamanan | Tetap diberi status informasi pendukung |

## Pemeriksaan jumlah untuk N=200 dan R=5

Nilai berikut hanya pemeriksaan struktur, bukan hasil efektivitas:

- 15.000 baris evaluatif per sistem;
- 15.610 total baris per sistem;
- 1.000 baris primer per skenario;
- 300 setup S7 per sistem;
- 1.000 serangan S7 per sistem.

## Narasi siap disesuaikan setelah hasil final

> Pengujian keamanan dilakukan terhadap lima belas skenario dengan ukuran
> sampel primer yang sama. Request yang hanya membentuk profil atau kondisi
> awal diberi label setup dan dikeluarkan dari confusion matrix. Pemisahan ini
> mencegah kontrol pendahuluan menambah jumlah true negative dan menjaga agar
> kontribusi setiap skenario terhadap evaluasi dapat dibandingkan secara
> proporsional.

> Pada S7, request pertama sampai batas hard limit digunakan untuk membentuk
> kondisi counter dan harus tetap diizinkan. Request setelah batas tersebut
> menjadi unit evaluasi. Nonce dan request ID selalu diperbarui, sedangkan
> metode, endpoint, token family, dan window dipertahankan. Oleh sebab itu,
> respons HTTP 429 dengan reason code rate_limit_exceeded dapat ditafsirkan
> sebagai bukti kerja rate limiter, bukan efek replay detector atau kegagalan
> device proof.

Setelah eksperimen selesai, gantikan frasa bersyarat “diharapkan” atau “harus”
dengan deskripsi hasil aktual hanya apabila quality report mendukungnya.
