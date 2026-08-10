# R-ATF Framework v0.1.3

Rilis ini memperjelas demonstrasi untuk penguji tanpa mengubah algoritma,
skenario, atau angka eksperimen penelitian.

## Perubahan tampilan

- Aplikasi contoh menggunakan nama **UHAMKA Mart** dan tampil sebagai toko milik
  pengembang, bukan sebagai halaman pengujian framework.
- UHAMKA Mart memiliki pencarian, kategori, favorit, keranjang multi-produk,
  pilihan pengiriman, kode promo, serta dialog hasil checkout.
- Informasi keputusan, nilai kepercayaan, bobot, ambang, riwayat, audit, dan
  hasil penelitian hanya ditampilkan pada **R-ATF Control Room**.
- Bahasa Control Room disederhanakan menjadi Diizinkan, Perlu konfirmasi, dan
  Ditolak, dengan istilah teknis tetap tersedia sebagai keterangan pendamping.

## Perubahan demonstrasi

- Tombol **Gunakan nilai penelitian** mengembalikan bobot IP 0,25; perangkat
  0,20; waktu 0,10; frekuensi 0,20; riwayat token 0,25; serta ambang 0,62 dan
  0,82.
- Policy endpoint aktif dapat diperbarui dari Control Room tanpa mengubah kode
  endpoint.
- Token demonstrasi lokal ditampilkan lengkap pada Control Room dan dikirim
  lengkap pada header `Authorization` sehingga dapat dilihat melalui Chrome
  DevTools. Token tersebut bukan kredensial produksi.
- Ringkasan hasil penelitian tersimpan ikut dibawa oleh paket dan dipisahkan
  dari hasil permintaan interaktif.

## Instalasi

```bash
pip install --upgrade --no-cache-dir ratf-framework==0.1.3
python -m ratf.showcase
```

Public API Flask extension tetap kompatibel. Status paket tetap alpha dan belum
diklaim siap untuk operasi skala besar tanpa sistem login produksi, Redis yang
tahan gagal, HTTPS, pengelolaan kunci, MFA nyata, pemantauan, serta pengujian
beberapa server.
