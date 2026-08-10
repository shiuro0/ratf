# Penyelarasan Proposal Tanpa Mengubah Judul

Judul awal tetap digunakan. Penyesuaian dilakukan pada definisi operasional, batasan, baseline, dan metode uji agar Bab 4 konsisten dengan implementasi.

## Posisi R-ATF

R-ATF diposisikan sebagai framework rule-based yang mengevaluasi penggunaan token pada setiap protected API request. Framework tidak menggantikan TLS, validasi token, registry, revocation, nonce, idempotency, scope, atau rate limit. Trust score dijalankan setelah kontrol deterministik tersebut berhasil.

Sifat adaptif berarti skor dan keputusan berubah mengikuti konteks serta histori request. Bobot tidak belajar sendiri dan tidak menggunakan machine learning.

## Penyesuaian Bab 1

- Pertahankan judul yang disetujui.
- Jelaskan bahwa “mencegah” dioperasionalkan sebagai mencegah request diteruskan pada skenario uji yang terdefinisi, bukan menjamin pencegahan absolut.
- Hapus klaim bahwa OAuth2 access-token rotation menghasilkan access token sekali pakai dan tidak cocok untuk high traffic.
- Gunakan istilah kebijakan penggantian access token pada session family untuk mekanisme prototipe ini.
- Nyatakan bahwa TLS menjadi asumsi dasar deployment, sedangkan penelitian membahas penyalahgunaan setelah token telah diperoleh pihak lain.

## Penyesuaian Bab 2

Tambahkan penjelasan ringkas mengenai:

1. Risk-Based Authentication sebagai pendekatan terkait;
2. perbedaan RBA pada saat login dan evaluasi R-ATF pada protected request;
3. DPoP dan mTLS sebagai pembanding sender-constrained token, bukan komponen yang wajib diimplementasikan;
4. JWT sebagai self-contained token dan opaque token sebagai reference token;
5. token registry, revocation, nonce, idempotency, dan scope sebagai kontrol deterministik.

## Penyesuaian Bab 3

Baseline diganti dari “API yang hanya memvalidasi JWT” menjadi `standard controls`. Kedua sistem memakai endpoint, payload, token policy, Redis, dan alat uji yang sama. Perbedaan utamanya adalah penggunaan trust score pada mode R-ATF.

Metrik dipisahkan menjadi:

- exact replay prevention untuk S4;
- contextual stolen-token detection untuk S6, S12, dan S14;
- strict FPR untuk request sah yang diblokir;
- challenge rate untuk request sah yang mendapat verify;
- friction rate untuk gabungan block dan verify;
- p95 latency dan throughput;
- audit completeness dan audit integrity.

Request `setup` tidak dimasukkan ke confusion matrix. Threshold hanya disesuaikan pada pilot, lalu dibekukan sebelum eksperimen utama.
