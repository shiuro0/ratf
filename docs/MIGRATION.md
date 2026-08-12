# Migrasi dari `ratf-framework` ke `ratf`

Repository ini melanjutkan source `ratf-framework` 0.1.4. Nama publik diubah
menjadi `ratf`, tetapi namespace Python tetap sama:

```python
from ratf import RATF
```

## Versi

Versi baru dimulai dari `0.2.0`, bukan kembali ke `0.1.0`. Ini menjaga urutan
riwayat karena kode merupakan kelanjutan langsung dari 0.1.4.

## Memindahkan instalasi

Jangan memasang `ratf-framework` dan `ratf` bersamaan karena keduanya menyediakan
package Python bernama `ratf`.

```bash
python -m pip uninstall ratf-framework
python -m pip install ratf
```

Impor dan decorator aplikasi tidak perlu diganti. Periksa hanya konfigurasi
deployment, lock file, dokumentasi internal, dan otomasi yang masih menyebut
nama distribusi lama.

## Repository GitHub

Pilihan yang paling aman adalah mengganti nama repository lama melalui
**Settings → General → Repository name → ratf**. GitHub biasanya mempertahankan
redirect untuk URL clone, issue, star, dan riwayat commit.

Membuat repository baru juga dapat dilakukan, tetapi issue, star, release, dan
riwayat kolaborasi tidak berpindah otomatis. Jika memilih repository baru,
gunakan folder ini sebagai root dan pertahankan repository lama dalam keadaan
arsip agar sumber versi sebelumnya tetap dapat dilacak.

## PyPI

Nama repository GitHub tidak menjamin nama `ratf` tersedia di PyPI. Sebelum
rilis pertama:

1. periksa `https://pypi.org/project/ratf/`;
2. siapkan Trusted Publisher untuk repository `shiuro0/ratf`;
3. bangun dan periksa wheel;
4. terbitkan `ratf` 0.2.0;
5. uji instalasi pada virtual environment bersih.

Jika nama `ratf` ternyata sudah dimiliki pihak lain, gunakan nama distribusi
yang unik seperti `ratf-security`. Nama import tetap dapat dipertahankan sebagai
`ratf`.

Paket lama tidak perlu dihapus dari PyPI. Biarkan sebagai riwayat dan tambahkan
catatan bahwa pengembangan berlanjut pada distribusi baru.
