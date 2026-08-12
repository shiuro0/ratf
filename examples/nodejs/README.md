# Contoh integrasi Node.js

`server.mjs` menjadi Policy Enforcement Point dan meminta keputusan ke layanan
evaluasi RATF melalui HTTP.

1. Run `examples/flask_app/app.py` agar evaluation service aktif.
2. Jalankan `server.mjs` dengan Node.js 18 atau lebih baru.
3. Jalankan `run_client.mjs`.

Tidak ada dependency npm tambahan. Nilai body dan header dapat diubah langsung
pada `run_client.mjs`. Aplikasi Node.js tidak menyalin formula trust score,
sehingga bobot dan threshold tetap dikelola oleh R-ATF.

Contoh ini hanya pemeriksaan awal integrasi. Pada aplikasi nyata, Identity
Provider harus memvalidasi token sebelum identitas dan konteks dikirim ke RATF.
