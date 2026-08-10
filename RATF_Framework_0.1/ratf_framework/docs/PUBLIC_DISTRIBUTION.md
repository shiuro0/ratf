# Distribusi publik R-ATF

## Status

Kode sudah dapat dibangun menjadi wheel dan source distribution, tetapi belum
otomatis tersedia melalui `pip install ratf-framework` sampai pemilik membuat
repository publik dan menerbitkan paket ke PyPI. Nama distribusi juga harus
diperiksa kembali karena nama PyPI bersifat global.

## Alur publikasi yang disarankan

1. Buat repository GitHub publik dan unggah source code, README, LICENSE,
   dokumentasi, contoh, serta test.
2. Jangan memasukkan `.env`, token, secret, audit mentah, atau dataset besar ke
   repository. Hasil penelitian lengkap dapat ditempatkan sebagai release asset.
3. Jalankan workflow CI sampai seluruh pemeriksaan lulus.
4. Uji paket pertama melalui TestPyPI.
5. Buat project/pending publisher di PyPI.
6. Hubungkan `.github/workflows/release.yml` sebagai Trusted Publisher dengan
   environment bernama `pypi`.
7. Buat GitHub Release dari tag versi, misalnya `v0.1.1`.

Workflow release membangun wheel dan source distribution, memeriksanya, lalu
mengunggah melalui identitas OIDC berumur pendek. Tidak perlu menyimpan API token
PyPI jangka panjang dalam repository.

## Pemeriksaan lokal sebelum rilis

```bash
python run_all_checks.py
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

Uji instalasi pada virtual environment baru:

```bash
pip install Flask
pip install dist/ratf_framework-0.1.1-py3-none-any.whl
python -c "from ratf import RATF, PolicyProfile; print('R-ATF siap')"
```

## Hal yang harus tersedia agar pengembang mandiri

- README dengan quick start;
- dokumentasi public API dan seluruh konfigurasi;
- contoh integrasi nyata, bukan hanya dashboard;
- OpenAPI untuk interoperabilitas bahasa lain;
- changelog dan semantic versioning;
- lisensi penggunaan;
- security policy dan kanal pelaporan kerentanan;
- issue template untuk bug yang dapat direproduksi;
- test otomatis untuk setiap rilis.

Wheel hanya berisi package `ratf`, template dashboard, dan OpenAPI. Naskah
skripsi, dataset penelitian, Postman, serta script eksperimen tidak menjadi
dependency aplikasi pengguna.
