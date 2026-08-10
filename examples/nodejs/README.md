# Contoh integrasi Node.js

Folder Node.js lama tetap digunakan. `server.mjs` menjadi Policy Enforcement
Point dan meminta keputusan ke evaluation service R-ATF melalui HTTP.

1. Run `examples/flask_app/app.py` agar evaluation service aktif.
2. Jalankan `server.mjs` dengan Node.js 18 atau lebih baru.
3. Jalankan `run_client.mjs`.

Tidak ada dependency npm tambahan. Nilai body dan header dapat diubah langsung
pada `run_client.mjs`. Aplikasi Node.js tidak menyalin formula trust score,
sehingga bobot dan threshold tetap dikelola oleh R-ATF.

Contoh ini hanya smoke test integrasi. Pengembang yang memakai paket tidak perlu
mengulang S1–S15 atau eksperimen k6. Pada aplikasi nyata, Identity Provider
harus memvalidasi token sebelum identitas dan konteks dikirim ke R-ATF.
