# Distribusi publik R-ATF

## Status

Kode sudah dapat dibangun menjadi wheel dan source distribution, tetapi belum
otomatis tersedia melalui `pip install ratf-framework` sampai pemilik membuat
repository publik dan menerbitkan paket ke PyPI. Nama distribusi juga harus
diperiksa kembali karena nama PyPI bersifat global.

Wheel saat ini sudah membawa Flask, Waitress, template NusaMart, template
Control Room, dan console entry point. Artinya, setelah rilis PyPI berhasil,
pengembang pada komputer lain tidak perlu menerima folder dari pembuat:

```bash
pip install ratf-framework
ratf-showcase
```

Pada IDE, `ratf-showcase` dapat digantikan dengan Run Configuration yang
menjalankan module `ratf.showcase`.

## Alur publikasi yang disarankan

1. Gunakan repository GitHub yang sudah ada dan commit hanya file yang berubah.
2. Jangan memasukkan `.env`, token, secret, audit mentah, atau dataset besar ke
   repository. Hasil penelitian lengkap dapat ditempatkan sebagai release asset.
3. Jalankan workflow CI sampai seluruh pemeriksaan lulus.
4. Uji paket pertama melalui TestPyPI.
5. Buat project/pending publisher di PyPI.
6. Hubungkan `.github/workflows/release.yml` sebagai Trusted Publisher dengan
   environment bernama `pypi`.
7. Buat GitHub Release dari tag versi `v0.1.2`.

Workflow release membangun wheel dan source distribution, memeriksanya, lalu
mengunggah melalui identitas OIDC berumur pendek. Tidak perlu menyimpan API token
PyPI jangka panjang dalam repository.

## Memperbarui repository dan release yang sudah ada

Tidak perlu membuat repository atau folder proyek baru. Ganti file pada path
yang sama, commit ke branch `main`, lalu tunggu CI selesai.

- Pertahankan `v0.1.1` sebagai riwayat rilis dan buat `v0.1.2` pada repository
  yang sama. PyPI tidak mengizinkan isi versi yang sudah terbit untuk ditimpa.
- Jangan menghapus release atau tag lama hanya karena pengguna akan diarahkan
  ke versi terbaru.
- Release notes dan asset GitHub dapat diperbarui, tetapi paket PyPI yang sudah
  terbit tetap bersifat immutable.

## Pemeriksaan lokal sebelum rilis

```bash
python run_all_checks.py
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

Uji instalasi pada virtual environment baru:

```bash
pip install dist/ratf_framework-0.1.2-py3-none-any.whl
python -c "from ratf import RATF, PolicyProfile; print('R-ATF siap')"
python -m ratf.showcase
```

Pemeriksaan rilis belum selesai bila showcase hanya berhasil dari folder source.
Pengujian harus dilakukan pada virtual environment kosong dengan wheel terpasang,
working directory di luar repository, dan memastikan file template dimuat dari
`site-packages`.

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

Test keamanan S1–S15 dan eksperimen k6 merupakan tanggung jawab maintainer pada
proses validasi framework. Pengembang pengguna cukup menguji integrasi token,
Redis, policy endpoint, dan step-up milik aplikasinya.

Wheel hanya berisi package `ratf`, template showcase/dashboard, dan OpenAPI. Naskah
skripsi, dataset penelitian, Postman, serta script eksperimen tidak menjadi
dependency aplikasi pengguna. Showcase NusaMart ikut berada dalam package
`ratf` sebagai bukti integrasi yang dapat dijalankan tanpa repository.
