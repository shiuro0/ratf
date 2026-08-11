# Panduan Demonstrasi untuk Penguji

Panduan ini menunjukkan hasil akhir R-ATF melalui dua tampilan yang mempunyai
fungsi berbeda. **UHAMKA Mart** berperan sebagai aplikasi milik pengembang,
sedangkan **R-ATF Control Room** dipakai untuk menjelaskan keputusan keamanan,
mengubah aturan, dan membaca ringkasan hasil penelitian.

## Menjalankan aplikasi

Pada PyCharm, buat **Python Run Configuration**, pilih **Module name**, lalu isi:

```text
ratf.showcase
```

Setelah menekan **Run**, browser membuka alamat berikut:

- UHAMKA Mart: `http://127.0.0.1:5100/`
- Control Room: `http://127.0.0.1:5100/ratf/dashboard/`

Jika paket belum dipasang, gunakan terminal pada virtual environment yang sama:

```powershell
pip install --upgrade --no-cache-dir ratf-framework==0.1.4
```

## Urutan demonstrasi yang disarankan

### 1. Tunjukkan integrasi pada aplikasi pengembang

Buka UHAMKA Mart, cari produk, tambahkan beberapa barang ke keranjang, pilih
pengiriman, masukkan promo `KAMPUS10`, lalu buat pesanan. Halaman toko hanya
menampilkan pengalaman pengguna dan tidak memperlihatkan perhitungan R-ATF.

Sebelum menekan **Buat pesanan**, buka **Chrome DevTools → Network**. Pilih
request `orders` setelah checkout untuk memperlihatkan:

- token lengkap pada header `Authorization`;
- identitas client, perangkat, waktu, dan nonce pada request header;
- isi pesanan pada tab Payload;
- status HTTP dan header keputusan `X-RATF-*` pada response.

Token sengaja ditampilkan lengkap karena nilainya hanya data demonstrasi lokal.
Token aplikasi nyata tidak boleh dicetak ke console, dibagikan, atau disimpan
di source code.

### 2. Jelaskan tiga keputusan utama

Buka Control Room, lalu jalankan skenario dari menu **Coba akses**:

1. **Penggunaan normal** memperlihatkan request yang diizinkan.
2. **Token berpindah perangkat** memperlihatkan perubahan konteks yang perlu
   dikonfirmasi atau ditolak sesuai nilai kepercayaan.
3. **Request yang sama dikirim ulang** memperlihatkan pencegahan exact replay.
4. **Konteks berisiko tinggi** memperlihatkan keputusan terhadap beberapa
   perubahan konteks sekaligus.

Untuk setiap percobaan, tunjukkan status keputusan, alasan sederhana, nilai
kepercayaan, tindakan efektif, serta rincian request dan response bila penguji
ingin memeriksa bukti teknisnya.

### 3. Tunjukkan bahwa aturan dapat disesuaikan

Buka menu **Atur penilaian**. Ubah salah satu bobot atau batas keputusan, lalu
tekan **Terapkan pengaturan**. Jalankan kembali penggunaan normal atau konteks
berisiko untuk membuktikan bahwa endpoint memakai pengaturan tersebut.

Tekan **Gunakan nilai penelitian** untuk mengembalikan konfigurasi utama:

| Komponen | Bobot |
|---|---:|
| Alamat jaringan | 0,25 |
| Perangkat | 0,20 |
| Waktu akses | 0,10 |
| Frekuensi | 0,20 |
| Riwayat token | 0,25 |

Batas **perlu konfirmasi** adalah `0,62` dan batas **diizinkan** adalah `0,82`.
Jumlah bobot harus tetap `1,00`.

### 4. Tunjukkan bukti pencatatan

Buka menu **Riwayat** untuk memperlihatkan konteks yang telah diterima dan
catatan audit. Gunakan tombol reset hanya ketika ingin mengulang demonstrasi
dari keadaan awal. Reset tidak mengubah bobot atau batas keputusan.

### 5. Bedakan demo langsung dan hasil penelitian

Buka menu **Hasil penelitian**. Jelaskan bahwa angka pada bagian ini merupakan
ringkasan data pengujian akhir yang tersimpan, bukan angka yang dibuat ulang
oleh tombol skenario. Sementara itu, kartu hasil pada menu **Coba akses** adalah
hasil request yang baru saja dijalankan secara langsung.

## Kalimat penutup yang dapat digunakan

> UHAMKA Mart menunjukkan bagaimana paket R-ATF dipasang pada aplikasi Flask
> milik pengembang. Request checkout tetap terlihat seperti proses belanja
> biasa bagi pengguna, sedangkan R-ATF memeriksa token dan konteks pada sisi
> server. Control Room dipakai untuk melihat alasan keputusan, menyesuaikan
> kebijakan, dan memeriksa audit tanpa mencampurkan informasi teknis ke halaman
> utama aplikasi.

Demonstrasi ini membuktikan kesiapan instalasi dan integrasi awal. Showcase
lokal belum dimaksudkan sebagai bukti kesiapan operasi produksi berskala besar.
