# Acuan Standar

- RFC 6750, *The OAuth 2.0 Authorization Framework: Bearer Token Usage*. Menjelaskan sifat bearer token dan kewajiban penggunaan TLS.
- RFC 7662, *OAuth 2.0 Token Introspection*. Menjelaskan pemeriksaan status aktif dan metadata token, termasuk opaque token.
- RFC 8705, *OAuth 2.0 Mutual-TLS Client Authentication and Certificate-Bound Access Tokens*. Acuan sender-constrained token berbasis sertifikat.
- RFC 9449, *OAuth 2.0 Demonstrating Proof of Possession (DPoP)*. Acuan proof-of-possession pada lapisan aplikasi.

Implementasi device proof pada paket ini memakai HMAC untuk simulasi yang mudah direproduksi. Implementasi tersebut tidak disebut sebagai DPoP dan tidak mengklaim kesetaraan keamanan dengan RFC 9449.
