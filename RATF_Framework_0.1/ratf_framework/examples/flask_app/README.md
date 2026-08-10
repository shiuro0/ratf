# Contoh integrasi Flask

Jalankan `app.py` langsung melalui **Run** di PyCharm, lalu buka:

- `http://127.0.0.1:5100/ratf/dashboard/` untuk dashboard;
- jalankan `run_client.py` untuk request normal, exact replay, dan perubahan konteks.

Endpoint `/api/payments` menunjukkan penggunaan policy `important-api` dengan
bobot, threshold, dan batas burst tersendiri. Dashboard juga dapat memilih
policy tersebut dari kolom **Policy endpoint**.

Contoh memakai memory storage agar demonstrasi lokal langsung berjalan. Untuk
memakai Redis, tambahkan environment variable `RATF_EXAMPLE_STORAGE=redis` dan
pastikan `REDIS_URL` mengarah ke Redis aplikasi.

`application_idp()` mewakili validasi token milik aplikasi. Dalam penerapan
sebenarnya, ganti callback tersebut dengan SDK Identity Provider atau gunakan
`OIDCIntrospectionIdentityProvider`.
