# Changelog

Perubahan penting pada RATF dicatat pada berkas ini.

## 0.2.0

- Mengubah identitas repository dan distribusi dari `ratf-framework` menjadi
  `ratf` tanpa mengubah namespace Python `ratf`.
- Mempertahankan API publik untuk core, Flask extension, Identity Provider,
  policy profile, shadow mode, step-up hook, AuthZEN, Redis, dan audit log.
- Menyelaraskan skenario verify pada showcase dengan konteks penelitian sehingga
  contoh utama menghasilkan trust score `0.7075`.
- Menambahkan header simulasi `X-Test-User-Agent` yang hanya diterima ketika
  experiment mode dan experiment key aktif.
- Menambahkan README, Quick Start, model keputusan, panduan migrasi, dan panduan
  publikasi yang berorientasi pada pengembang aplikasi.
- Mengubah `validation_tests/` menjadi struktur standar `tests/`.
- Mengubah `run_all_checks.py` menjadi `run_checks.py` dan menghentikan penulisan
  laporan hasil ke repository.
- Menghapus laporan validasi, panduan BAB IV, dan release note lama dari source
  distribution publik. Test otomatis tetap dipertahankan.

## Riwayat sebelum perubahan nama

Versi 0.1.0 sampai 0.1.4 diterbitkan dengan nama distribusi
`ratf-framework`. Versi tersebut menjadi dasar 0.2.0 dan tetap dipertahankan
pada riwayat repository/rilis lama.
