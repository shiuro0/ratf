# Contoh integrasi Node.js

Contoh ini tidak mengimpor modul Python. `server.mjs` bertindak sebagai Policy
Enforcement Point dan meminta keputusan ke layanan evaluasi R-ATF dengan format
AuthZEN.

`server.mjs` mengirim `context.policy_id=important-api` secara bawaan. Nilainya
dapat diganti melalui environment variable `RATF_POLICY_ID`, sehingga service
Node.js dapat memilih policy endpoint tanpa menduplikasi formula R-ATF.

Token `node-app-token` hanya mewakili validasi Identity Provider milik aplikasi
pada contoh lokal. Pada aplikasi nyata, validasi token harus dilakukan sebelum
subject dan konteks dikirim ke evaluation service.

1. Jalankan `examples/flask_app/app.py` agar layanan evaluasi aktif.
2. Jalankan `server.mjs`.
3. Jalankan `run_client.mjs` untuk melihat request normal dan perubahan konteks.

Tidak ada package npm tambahan yang dibutuhkan karena contoh memakai `fetch` dan
server HTTP bawaan Node.js.
