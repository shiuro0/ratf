# Arsitektur R-ATF 0.1

## Tujuan desain

R-ATF 0.1 diposisikan sebagai kerangka kerja yang menyediakan struktur dan
alur evaluasi baku, tetapi memberi titik perubahan yang jelas kepada aplikasi.
Pengembang tidak perlu mengubah algoritma internal untuk mengganti Identity
Provider, bobot, threshold, penyimpanan, respons step-up, atau mode penerapan.

## Lapisan

| Lapisan | Tanggung jawab | Bergantung Flask |
|---|---|---|
| `ratf.core` | model konteks, konfigurasi, evaluasi, hasil keputusan, shadow mode | Tidak |
| modul kontrol | trust score, policy, replay, device proof, storage | Tidak |
| `ratf.identity` | local registry, callback aplikasi, introspection OIDC | Tidak |
| `ratf.flask_extension` | ekstraksi request Flask dan dekorasi response | Ya |
| `ratf.authzen` | kontrak layanan evaluasi untuk PEP non-Python | Ya pada adapter HTTP contoh |
| dashboard | konfigurasi dan visualisasi demonstrasi | Ya |

Flask dan AuthZEN adalah adapter menuju `RATFEngine`; keduanya tidak memiliki
formula trust score sendiri.

`PolicyProfile` menyediakan override per-endpoint untuk bobot, threshold,
shadow mode, dan batas burst. Profile diselesaikan dari konfigurasi global pada
setiap evaluasi tanpa mengubah objek kebijakan global. Nama profile ikut masuk
ke response dan audit sehingga konfigurasi yang menghasilkan keputusan tetap
dapat ditelusuri.

`ratf.middleware.SecurityMiddleware` dipertahankan sebagai compatibility
adapter untuk mereproduksi eksperimen v6. Ia tidak menjadi API publik baru dan
tidak boleh dihapus karena akan memutus keterlacakan data lama. Compatibility
adapter dan `RATFEngine` tetap mengimpor fungsi trust score serta policy yang
sama; orkestrasi lama dibekukan agar bukti eksperimen tidak diubah secara
retrospektif.

## Alur keputusan

1. Adapter aplikasi memvalidasi access token melalui Identity Provider.
2. Kontrol autentikasi, client, scope, device proof, replay, dan hard rate limit
   dijalankan sebelum skor.
3. Core menghitung lima komponen dan trust score berbobot.
4. Policy menghasilkan `allow`, `verify`, atau `block`.
5. Shadow mode dapat mengubah tindakan efektif dari keputusan kontekstual
   menjadi `allow`, tetapi tidak mengabaikan autentikasi, replay, atau hard rate
   limit.
6. Step-up hook dipanggil ketika keputusan kebijakan adalah `verify`.
7. Histori tepercaya diperbarui hanya setelah `allow`, kecuali pengembang secara
   eksplisit mengaktifkan pembelajaran shadow.
8. Hasil dan alasan keputusan dikirim ke audit sink.

## Kontrak Identity Provider

Metode `authenticate(access_token, context)` mengembalikan identitas normal:

- subject;
- client ID;
- scope;
- token ID dan family/session ID;
- waktu kedaluwarsa jika tersedia;
- metadata penerbitan yang dibutuhkan untuk baseline konteks.

R-ATF tidak mengambil alih proses login. Token tetap diterbitkan dan dikelola
oleh aplikasi atau Identity Provider yang dipilih pengembang.

## Shadow mode

Shadow mode adalah mekanisme observasi kebijakan. Framework tetap menghitung
dan mencatat keputusan yang seharusnya berlaku, tetapi request yang hanya gagal
pada evaluasi kontekstual dapat diteruskan. Dua nilai selalu dibedakan:

- `decision`: hasil kebijakan asli;
- `effective_decision`: tindakan yang benar-benar diberlakukan.

Pemisahan tersebut membantu aplikasi menilai false positive dan threshold
sebelum enforcement. Shadow mode bukan bypass autentikasi.

## Step-up hook

Step-up hook adalah interface untuk menyerahkan keputusan `verify` ke mekanisme
autentikasi tambahan milik aplikasi. Hook dapat mengembalikan jenis challenge,
URL, masa berlaku, dan metadata. Keberhasilan MFA tetap harus diverifikasi oleh
server atau Identity Provider; framework tidak mempercayai klaim boolean dari
client.

## AuthZEN

Endpoint `/access/v1/evaluation` memakai entitas `subject`, `resource`,
`action`, dan `context`. Karena respons AuthZEN menggunakan keputusan boolean,
R-ATF memetakannya sebagai berikut:

| R-ATF | AuthZEN `decision` | Detail |
|---|---:|---|
| allow | `true` | `context.ratf.decision=allow` |
| verify | `false` | detail dan step-up pada `context.ratf` |
| block | `false` | alasan block pada `context.ratf` |
| verify/block dalam shadow mode | `true` | keputusan asli tetap berada pada `context.ratf.decision` |

Spesifikasi yang digunakan: [OpenID AuthZEN Authorization API
1.0](https://openid.net/specs/authorization-api-1_0.html), khusus endpoint
single access evaluation.

Aplikasi non-Python dapat mengirim `context.policy_id` untuk memilih profile
yang sudah didaftarkan oleh host evaluation service.

## Batas kesiapan

Versi ini membuktikan instalasi, extension point, dan interoperabilitas pada
lingkungan pengembangan. Produksi masih memerlukan hardening deployment,
pengelolaan secret, IdP dan MFA nyata, Redis high availability, observability,
penalaan kebijakan, serta pengujian multi-node.
