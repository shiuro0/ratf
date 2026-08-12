# Model keputusan dan contoh trust score

RATF menghitung trust score sebagai jumlah lima komponen yang telah diberi
bobot:

```text
TS = wIP(Cip) + wDevice(Cdevice) + wTime(Ctime)
     + wFrequency(Freq) + wHistory(Htoken)
```

Nilai penelitian menggunakan bobot berikut:

| Komponen | Bobot |
|---|---:|
| Jaringan/IP | 0,25 |
| Perangkat | 0,20 |
| Waktu | 0,10 |
| Frekuensi | 0,20 |
| Riwayat token | 0,25 |

Ambang keputusannya adalah:

| Rentang skor | Keputusan |
|---|---|
| `TS < 0,62` | `block` |
| `0,62 <= TS < 0,82` | `verify` |
| `TS >= 0,82` | `allow` |

## Mengapa hasil penelitian 0,7075?

Pada skenario S6, S12, dan S14, penyerang diasumsikan memperoleh token beserta
identitas perangkat yang terkait. Request kemudian berasal dari jaringan dan
aplikasi klien yang berbeda, sementara jam akses dan frekuensinya masih wajar.

| Komponen | Nilai |
|---|---:|
| `Cip` | 0,60 |
| `Cdevice` | 0,60 |
| `Ctime` | 1,00 |
| `Freq` | 1,00 |
| `Htoken` | 0,55 |

Perhitungannya:

```text
TS = (0,25 × 0,60)
   + (0,20 × 0,60)
   + (0,10 × 1,00)
   + (0,20 × 1,00)
   + (0,25 × 0,55)
   = 0,7075
```

Nilai tersebut berada di antara 0,62 dan 0,82 sehingga menghasilkan `verify`.

## Mengapa contoh lama pernah menghasilkan 0,6275?

Contoh lama memakai `device_id` yang benar-benar baru. Akibatnya nilai
`Cdevice` turun dari 0,60 menjadi 0,20, sedangkan komponen lain tetap sama:

```text
TS = (0,25 × 0,60)
   + (0,20 × 0,20)
   + (0,10 × 1,00)
   + (0,20 × 1,00)
   + (0,25 × 0,55)
   = 0,6275
```

Skor `0,6275` juga masih termasuk `verify` karena tidak lebih kecil dari 0,62.
Jadi, perbedaannya bukan kesalahan rumus; kedua request menggambarkan asumsi
serangan yang berbeda. Showcase repository ini memakai skenario utama yang
selaras dengan penelitian dan menampilkan `0,7075`.

## Catatan penggunaan

Nilai bobot dan ambang tidak boleh dianggap berlaku untuk semua aplikasi.
Endpoint pembayaran, pencarian, profil, dan administrasi dapat memiliki tingkat
risiko yang berbeda. Pengembang sebaiknya memulai dari shadow mode, mengamati
distribusi skor request sah, lalu menetapkan ambang dengan memperhatikan risiko
serta kemungkinan gangguan bagi pengguna.
