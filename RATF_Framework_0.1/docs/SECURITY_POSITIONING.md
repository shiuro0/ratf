# Posisi Keamanan Penelitian

Judul proposal tetap digunakan. Framework diposisikan sebagai implementasi rule-based trust scoring untuk mencegah request berisiko diteruskan pada skenario eksperimen yang ditetapkan.

## Kontrol deterministik

Validasi token, registry, expiration, revocation, scope, device proof, timestamp, nonce, idempotency, rate limit, dan validasi payload menangani kondisi yang dapat diputuskan secara langsung.

## Ruang kontribusi R-ATF

R-ATF diuji ketika token dan request lolos kontrol deterministik, tetapi konteks berbeda dari konteks penerbitan atau histori yang telah diizinkan. S6, S12, dan S14 merupakan skenario utama untuk mengukur nilai tambah tersebut.

## Hubungan dengan RBA

R-ATF memakai prinsip yang mirip dengan Risk-Based Authentication, yaitu konteks, histori, skor, dan threshold. Perbedaannya adalah titik evaluasi: R-ATF bekerja pada protected API request setelah token diterbitkan. Penelitian tidak mengklaim menemukan konsep RBA baru.

## DPoP dan mTLS

DPoP dan mTLS dibahas sebagai pembanding sender-constrained token. Keduanya tidak wajib diimplementasikan pada prototipe ini. Device proof HMAC bukan DPoP dan tidak boleh diklaim setara.

## Batas

- TLS diasumsikan tersedia dan tidak diuji.
- IP dan user-agent dapat berubah atau dipalsukan.
- Full device compromise dapat meniru konteks pengguna.
- HS256 digunakan untuk prototipe lokal; asymmetric signing lebih tepat untuk pemisahan issuer dan resource server produksi.
- Endpoint token adalah simulasi penelitian, bukan authorization server lengkap.
