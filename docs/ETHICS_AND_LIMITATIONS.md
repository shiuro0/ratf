# Etika dan Keterbatasan

Seluruh identitas, IP, perangkat, token, order, dan pembayaran bersifat sintetis. Eksperimen tidak dijalankan terhadap akun, API, token, atau jaringan pihak lain.

Keterbatasan:

- TLS tidak diukur pada lapisan aplikasi;
- device proof HMAC adalah simulasi, bukan DPoP atau mTLS;
- IP dan user-agent hanya sinyal risiko;
- full compromise dapat meniru token, proof secret, dan konteks;
- token issuer bukan OAuth authorization server produksi;
- access-token replacement adalah kebijakan prototipe, bukan refresh-token rotation;
- idempotency duplicate pada prototipe ditolak, belum mengembalikan respons tersimpan;
- Redis tidak memakai persistence karena eksperimen membutuhkan reset terkontrol;
- hasil lokal tidak langsung mewakili beban produksi;
- hasil smoke test tidak boleh ditulis sebagai hasil Bab 4.
