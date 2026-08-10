# Spesifikasi Token v6.0

## JWT access token

Klaim yang digunakan:

| Klaim | Fungsi |
|---|---|
| `iss`, `aud` | penerbit dan resource server |
| `sub`, `role`, `client_id` | identitas dan aplikasi |
| `scope` | hak akses |
| `iat`, `nbf`, `exp` | waktu penerbitan dan masa berlaku |
| `jti` | identitas unik token |
| `sid` | session/token family |
| `cnf.device_hash` | binding ke perangkat simulasi |

Decode JWT hanya membaca header dan payload. Validasi tetap memerlukan signature, algorithm allowlist, issuer, audience, expiration, registry, revocation, scope, dan device binding.

## Opaque access token

Opaque token berbentuk nilai acak seperti:

```text
ratf_at_<random value>
```

Token tidak memiliki klaim yang dapat di-decode oleh client. Metadata diperoleh melalui registry atau `/oauth/introspect`, meliputi `active`, scope, client, subject, issuer, audience, waktu, session ID, dan confirmation/device hash.

## Lifecycle pada prototipe

- Token dapat dipakai berkali-kali sampai expired, revoked, atau digantikan.
- Penerbitan token baru pada family yang sama menggantikan token lama secara default.
- Kebijakan tersebut membatasi token lama yang terkumpul dari satu perangkat.
- Token terbaru tetap membutuhkan device proof, nonce, scope, rate limit, dan evaluasi R-ATF.
- Mekanisme penggantian access token ini tidak disebut OAuth refresh-token rotation.
