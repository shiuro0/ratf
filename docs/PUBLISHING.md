# Membuat repository dan menerbitkan RATF

## 1. Menentukan cara pemindahan

Disarankan mengganti nama repository `ratf-framework` menjadi `ratf` agar
commit, issue, release, dan star tetap tersimpan. Jika repository baru benar-
benar diperlukan, buat repository kosong bernama `ratf`, lalu unggah isi folder
ini sebagai root.

Pastikan root repository langsung memuat:

```text
pyproject.toml
README.md
LICENSE
src/
tests/
examples/
docs/
.github/
```

Jangan mengunggah virtual environment, `.env`, secret, `dist/`, `build/`, log,
atau folder hasil pengujian.

## 2. Memeriksa source

```bash
python -m pip install -e ".[demo,test,release]"
python run_checks.py
python -m build
python -m twine check dist/*
```

Uji wheel pada virtual environment baru sebelum membuat release.

## 3. Menyiapkan Trusted Publishing PyPI

Karena `ratf` merupakan nama distribusi baru, konfigurasi Trusted Publisher
lama tidak otomatis berpindah. Pada PyPI, isi pengaturan publisher dengan:

```text
Owner       : shiuro0
Repository  : ratf
Workflow    : release.yml
Environment : pypi
```

Workflow `.github/workflows/release.yml` membangun distribusi dan menerbitkannya
saat GitHub Release dibuat.

Publisher yang masih menunjuk repository lama tidak akan cocok dengan identitas
OIDC repository baru. Hapus atau ubah konfigurasi lama, lalu pastikan empat nilai
di atas sama persis, termasuk nama environment `pypi`.

## 4. Membuat rilis

1. Pastikan `src/ratf/__init__.py` berisi versi yang sama dengan tag.
2. Pastikan CHANGELOG sudah diperbarui.
3. Commit perubahan dan dorong ke branch utama.
4. Buat tag `v0.2.0`.
5. Buat GitHub Release dari tag tersebut.
6. Periksa job build dan publish sampai selesai.
7. Uji dari komputer atau virtual environment lain:

```bash
python -m pip install --no-cache-dir ratf==0.2.0
python -m ratf.showcase
```

## 5. Bila publikasi gagal

- `File already exists`: nomor versi tersebut pernah diterbitkan dan tidak
  dapat ditimpa; naikkan versi.
- `Project not found` atau kegagalan OIDC: periksa Owner, Repository, Workflow,
  dan Environment pada Trusted Publisher.
- Gagal pada tahap pembuatan attestation: pastikan publikasi memakai Trusted
  Publisher yang cocok dengan repository dan workflow saat ini. Attestation
  aktif secara bawaan dan tidak memerlukan token PyPI manual.
- `No matching distribution`: release belum sampai ke PyPI atau nama/versi
  yang diminta berbeda.
- Konflik nama `ratf`: pilih nama distribusi unik, lalu ubah hanya
  `project.name` dan petunjuk instalasi. Folder source dan import `ratf` tidak
  harus berubah.

Rilis lama sebaiknya tidak diedit atau ditimpa. Setiap perubahan diterbitkan
sebagai versi baru agar pengguna dapat menelusuri riwayat paket dengan jelas.
