# R-ATF Framework v0.1.4

Rilis ini membawa revisi tampilan terbaru ke paket Python tanpa mengubah
algoritma, endpoint, bobot, threshold, atau hasil eksperimen penelitian.

## Perubahan UHAMKA Mart

- Mengganti nama tautan `Panel pengelola` menjadi `Control Room`.
- Menyederhanakan bagian produk unggulan dengan menghapus badge dekoratif yang
  dapat mengganggu tata letak pada ukuran layar tertentu.
- Menyederhanakan elemen dekoratif pada informasi layanan dan teks footer.
- Mempertahankan pencarian, kategori, favorit, keranjang, pilihan pengiriman,
  promo, checkout, serta pemeriksaan request melalui Chrome DevTools.

## Perubahan Control Room

- Meringkas beberapa kalimat agar informasi lebih cepat dipahami penguji.
- Menegaskan bahwa access token showcase adalah opaque token dari Identity
  Provider contoh.
- Mempertahankan skenario normal, perpindahan token, exact replay, konteks
  berisiko, evaluasi manual, pengaturan policy, preset penelitian, riwayat,
  audit, dan ringkasan hasil penelitian.

## Distribusi dan kompatibilitas

- Template terbaru disertakan di dalam wheel dan source distribution.
- Public API Python dan Flask extension tetap kompatibel dengan rilis
  sebelumnya.
- GitHub Actions build/publish diperbarui ke action yang menggunakan Node.js 24.
- PyPI Trusted Publishing dan digital attestations tetap diaktifkan.

## Instalasi

Setelah rilis tersedia di PyPI:

```bash
pip install --upgrade --no-cache-dir ratf-framework==0.1.4
python -m ratf.showcase
```

Showcase tetap ditujukan untuk demonstrasi dan integrasi awal, bukan sebagai
konfigurasi produksi berskala besar.
