# RATF V0.2.0

RATF adalah modul keamanan adaptif berbasis aturan untuk membantu aplikasi
menilai penggunaan access token pada setiap request API. Modul ini bekerja
setelah token dinyatakan valid oleh sistem identitas aplikasi, kemudian
membandingkan jaringan, perangkat, waktu akses, frekuensi request, dan riwayat
penggunaan token.

Hasil penilaiannya terdiri dari tiga keputusan:

- `allow`: request dapat diteruskan;
- `verify`: aplikasi perlu meminta konfirmasi identitas tambahan;
- `block`: request ditolak.

RATF tidak menggantikan login, OAuth/OIDC, atau Identity Provider. Fungsinya
adalah menambahkan penilaian kontekstual pada endpoint yang dianggap penting.

## Quick Start

Persyaratan minimum:

- Python 3.11 atau lebih baru;
- aplikasi Flask untuk integrasi;
- Redis untuk deployment dengan beberapa proses atau server;
- Identity Provider yang dapat memvalidasi access token pada aplikasi nyata.

Showcase lokal dapat langsung berjalan dengan penyimpanan memori dan token
simulasi, sehingga Redis dan Identity Provider belum diperlukan pada langkah
pertama.

Pasang paket:

```bash
pip install ratf
```

Untuk melihat cara kerja modul sebelum mengintegrasikannya, jalankan showcase:

```bash
python -m ratf.showcase
```

Buka alamat berikut:

- UHAMKA Mart: `http://127.0.0.1:5100/`
- Control Room: `http://127.0.0.1:5100/ratf/dashboard/`

Pengguna PyCharm dapat membuat **Run Configuration**, memilih **Module name**,
lalu mengisi `ratf.showcase`. Panduan langkah demi langkah tersedia di
[docs/QUICKSTART.md](docs/QUICKSTART.md).

> Nama `ratf` pada PyPI harus sudah diterbitkan oleh pemilik proyek sebelum
> perintah instalasi di atas dapat digunakan pada komputer lain. Selama masa
> migrasi, paket juga dapat dipasang langsung dari repository GitHub.

## Contoh integrasi Flask

Sistem token tetap menjadi milik aplikasi. RATF hanya menerima hasil validasi
melalui adapter Identity Provider:

```python
from flask import Flask, jsonify

from ratf import RATF
from ratf.identity import CallbackIdentityProvider
from ratf.storage import RedisStorage

app = Flask(__name__)


def validate_access_token(access_token, context):
    # Ganti pemanggilan ini dengan introspection atau verifikasi JWT/JWKS
    # yang sudah digunakan oleh aplikasi Anda.
    claims = application_identity_provider.introspect(access_token)
    if not claims.get("active"):
        return None

    return {
        "active": True,
        "subject": claims["sub"],
        "client_id": claims["client_id"],
        "scope": claims["scope"],
        "token_id": claims["jti"],
        "family_id": claims.get("sid", claims["sub"]),
        "exp": claims["exp"],
        "metadata": claims,
    }


ratf = RATF(
    storage=RedisStorage("redis://127.0.0.1:6379/0"),
    identity_provider=CallbackIdentityProvider(validate_access_token),
)

checkout_policy = ratf.policy(
    "checkout",
    weights={
        "ip": 0.25,
        "device": 0.20,
        "time": 0.10,
        "frequency": 0.20,
        "token_history": 0.25,
    },
    thresholds={"verify": 0.62, "allow": 0.82},
)

ratf.init_app(app)


@app.post("/api/orders")
@ratf.protect(
    required_scope="orders:write",
    transactional=True,
    policy=checkout_policy,
)
def create_order():
    return jsonify({"status": "created"}), 201
```

Endpoint bisnis tidak perlu menghitung trust score sendiri. Decorator memeriksa
request terlebih dahulu dan hanya menjalankan fungsi endpoint jika keputusan
efektifnya `allow`.

## Mengatur tingkat keamanan

Bobot menentukan seberapa besar pengaruh setiap komponen. Ambang menentukan
batas keputusan:

```text
score < 0.62            → block
0.62 <= score < 0.82    → verify
score >= 0.82           → allow
```

Karena itu, skor `0.6275` dan `0.7075` sama-sama berada pada wilayah `verify`.
Perbedaannya berasal dari konteks yang disimulasikan, bukan dari perubahan
rumus. Showcase utama menggunakan konteks yang selaras dengan skenario
penelitian dan menghasilkan `0.7075`. Penjelasan perhitungannya tersedia di
[docs/DECISION_MODEL.md](docs/DECISION_MODEL.md).

Pengembang dapat membuat policy berbeda untuk setiap tingkat risiko:

```python
payment_policy = ratf.policy(
    "high-value-payment",
    weights={
        "ip": 0.30,
        "device": 0.25,
        "time": 0.10,
        "frequency": 0.20,
        "token_history": 0.15,
    },
    thresholds={"verify": 0.72, "allow": 0.90},
    burst_soft_limit=12,
    burst_hard_limit=35,
)
```

Policy bernama dapat diperbarui dari backend tanpa mengubah fungsi endpoint:

```python
ratf.update_policy_profile(
    "high-value-payment",
    verify_threshold=0.75,
    allow_threshold=0.92,
)
```

Endpoint administrasi yang memanggil fungsi tersebut wajib dilindungi oleh
autentikasi dan otorisasi milik aplikasi.

## Shadow mode

Shadow mode membantu pengembang mengamati dampak policy sebelum menahannya pada
pengguna. Keputusan asli tetap dicatat, tetapi keputusan kontekstual
`verify`/`block` dapat diteruskan sementara sebagai `allow`.

```python
ratf.update_policy_profile("checkout", shadow_mode=True)
```

Kontrol dasar seperti token tidak valid, scope tidak sesuai, exact replay, dan
hard rate limit tetap ditolak. Shadow mode bukan cara untuk melewati
autentikasi.

## Step-up authentication

RATF menentukan kapan verifikasi tambahan diperlukan. OTP, passkey, atau MFA
tetap dijalankan oleh aplikasi atau Identity Provider:

```python
from ratf.core import StepUpChallenge
from ratf.core.ports import CallbackStepUpHandler


def create_step_up(context, identity, evaluation):
    return StepUpChallenge(
        challenge_type="totp",
        challenge_url="/account/verification",
        expires_in=180,
    )


ratf = RATF(
    identity_provider=idp,
    storage=storage,
    step_up_handler=CallbackStepUpHandler(create_step_up),
)
```

## Struktur repository

```text
src/ratf/core/             mesin evaluasi tanpa ketergantungan Flask
src/ratf/flask_extension.py
src/ratf/identity.py       adapter Identity Provider
src/ratf/authzen.py        layanan evaluasi HTTP
src/ratf/dashboard.py      Control Room opsional
src/ratf/showcase.py       aplikasi demonstrasi paket
examples/flask_app/        contoh integrasi Flask
examples/production_flask/ contoh integrasi tanpa dashboard
examples/nodejs/           policy-enforcement point melalui HTTP
tests/                     pemeriksaan otomatis
docs/                      dokumentasi penggunaan dan desain
```

## Pemeriksaan repository

Pemeriksaan dapat dijalankan dari PyCharm dengan membuka `run_checks.py` lalu
menekan **Run**. Melalui terminal:

```bash
python run_checks.py
```

Skrip menampilkan hasil pada konsol dan tidak menulis laporan validasi ke dalam
repository. Berkas hasil eksperimen atau log runtime sengaja tidak disertakan
dalam source distribution.

## Dokumentasi

- [Quick Start](docs/QUICKSTART.md)
- [Model keputusan dan contoh skor](docs/DECISION_MODEL.md)
- [Integrasi aplikasi](docs/DEVELOPER_INTEGRATION.md)
- [Referensi konfigurasi](docs/CONFIGURATION_REFERENCE.md)
- [Spesifikasi token](docs/TOKEN_SPECIFICATION.md)
- [Reason codes](docs/REASON_CODES.md)
- [Migrasi dari `ratf-framework`](docs/MIGRATION.md)
- [Membuat repository dan rilis](docs/PUBLISHING.md)
- [Batasan keamanan](docs/ETHICS_AND_LIMITATIONS.md)

## Status penggunaan

RATF dapat dipasang, dihubungkan ke Identity Provider, menggunakan Redis, dan
diterapkan pada endpoint Flask. Namun, kesiapan integrasi tidak otomatis berarti
siap produksi untuk seluruh skala aplikasi. Penerapan nyata tetap memerlukan
HTTPS, pengelolaan secret, Redis persistence/failover, MFA end-to-end,
observability, penalaan policy, pengujian multi-node, dan security review pada
lingkungan tujuan.

## Lisensi

MIT License. Lihat [LICENSE](LICENSE).
