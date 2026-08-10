# R-ATF Framework v0.1.2

Versi ini merupakan pembaruan kompatibel dari v0.1.1. Nomor versi dinaikkan
karena package yang telah diterbitkan ke PyPI tidak dapat diganti isinya dengan
nomor versi yang sama.

## Perubahan utama

- Showcase web NusaMart ikut terpasang di dalam wheel.
- Showcase dapat dijalankan melalui `python -m ratf.showcase` atau
  `ratf-showcase`.
- R-ATF Control Room tetap tersedia di `/ratf/dashboard/` dengan tampilan yang
  diperbarui.
- Client dapat mencoba request normal, perpindahan konteks, exact replay, dan
  konteks berisiko tinggi.
- Request, response, header `X-RATF-*`, trust score, histori konteks, event,
  audit integrity, dan penilaian kesiapan dapat diperiksa melalui GUI.
- Flask dan Waitress menjadi dependency standar agar instalasi satu perintah
  langsung dapat menjalankan showcase.
- Metadata PyPI menampilkan tautan homepage, repository, dokumentasi, issue
  tracker, dan changelog pada `shiuro0/ratf-framework`.

## Kompatibilitas

Public API Flask extension, policy profile, Identity Provider adapter, step-up
hook, AuthZEN endpoint, Redis storage, dan engine v0.1.1 tetap dipertahankan.
Perubahan ini tidak mengubah dataset atau angka eksperimen keamanan dan kinerja
yang digunakan pada penelitian.

## Instalasi dan pembaruan

Instalasi baru:

```bash
pip install ratf-framework==0.1.2
```

Pembaruan dari v0.1.1:

```bash
pip install --upgrade --no-cache-dir ratf-framework==0.1.2
```

Verifikasi:

```bash
python -c "import ratf; print(ratf.__version__, ratf.__file__)"
python -c "import ratf.showcase; print(ratf.showcase.__file__)"
python -m ratf.showcase
```

## Batas kesiapan

v0.1.2 siap didistribusikan, didemonstrasikan, dan diintegrasikan pada aplikasi
Flask. Statusnya tetap alpha dan belum diklaim siap produksi skala besar tanpa
IdP produksi, Redis persistence/failover, HTTPS, secret manager, MFA nyata,
observability, dan pengujian multi-node.
