# Contoh integrasi Flask

Folder ini adalah contoh Python utama dan tetap memakai struktur proyek lama.
Run `app.py` melalui PyCharm, lalu Run `run_client.py` pada proses terpisah.

Client memperlihatkan empat hal:

- request normal yang diteruskan;
- perubahan konteks yang meminta verifikasi ulang;
- exact replay yang diblokir;
- state histori konteks dan integritas audit untuk membantu debugging.

Body dan header berada langsung di bagian atas `run_client.py`, sehingga dapat
diubah tanpa memahami test runner. Bobot dan threshold berada di `app.py` pada
policy `important-api`.

Contoh memakai memory storage agar langsung berjalan. Jika ingin melihat state
yang sama di Redis, set `RATF_EXAMPLE_STORAGE=redis` dan arahkan `REDIS_URL` ke
Redis aplikasi. Redis menyimpan profile, history, nonce, idempotency, dan rate
counter; keputusan audit tetap disimpan dalam log JSONL dengan hash chain.

Endpoint `/app/debug/ratf` hanya untuk pengembangan lokal dan membutuhkan header
`X-Debug-Key`. Jangan membukanya ke internet. Pengembang aplikasi tidak perlu
mengulang eksperimen keamanan S1–S15 atau pengujian k6 hanya untuk mencoba
integrasi ini.
