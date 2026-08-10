# Integrasi R-ATF pada aplikasi pengembang

R-ATF dipasang pada aplikasi sebagai lapisan evaluasi setelah access token
divalidasi oleh Identity Provider dan sebelum fungsi bisnis dijalankan.
Dashboard tidak diperlukan pada aplikasi yang memakai framework.

## Instalasi

Setelah paket dipublikasikan ke PyPI:

```bash
pip install "ratf-framework[flask]==0.1.1"
```

Sebelum publikasi, pengembang dapat memasang wheel atau repository:

```bash
pip install "ratf-framework[flask] @ git+https://github.com/OWNER/REPOSITORY.git@v0.1.1"
```

Ganti `OWNER/REPOSITORY` setelah repository publik dibuat.

## Bobot dan threshold

Bobot menentukan besarnya kontribusi setiap komponen trust score. Threshold
menentukan batas keputusan. Keduanya tidak boleh diberi nama yang sama.

```python
payment_policy = ratf.policy(
    "important-payment",
    weights={
        "ip": 0.30,
        "device": 0.25,
        "time": 0.10,
        "frequency": 0.20,
        "token_history": 0.15,
    },
    thresholds={
        "verify": 0.70,
        "allow": 0.88,
    },
    burst_soft_limit=15,
    burst_hard_limit=40,
)
```

Bobot dinormalisasi menjadi total satu. Konfigurasi ditolak bila terdapat bobot
negatif, nama komponen tidak dikenal, atau threshold tidak memenuhi:

```text
0 <= verify < allow <= 1
```

## Melindungi endpoint

```python
from flask import Flask, jsonify
from ratf import RATF

app = Flask(__name__)
ratf = RATF(identity_provider=idp, storage=redis_storage)

payment_policy = ratf.policy(
    "important-payment",
    weights={"ip": .30, "device": .25, "time": .10,
             "frequency": .20, "token_history": .15},
    thresholds={"verify": .70, "allow": .88},
)
ratf.init_app(app)

@app.post("/api/payments")
@ratf.protect(
    required_scope="payments:write",
    transactional=True,
    policy=payment_policy,
)
def create_payment():
    return jsonify({"status": "accepted"}), 201
```

Policy dapat disebut menggunakan objek atau nama yang sudah terdaftar:

```python
@ratf.protect("payments:write", policy="important-payment")
```

Jika seluruh route dalam satu Flask Blueprint memiliki tingkat perlindungan
yang sama, policy dapat dipasang satu kali:

```python
payments_api = Blueprint("payments", __name__, url_prefix="/api/payments")

ratf.protect_blueprint(
    payments_api,
    required_scope="payments:write",
    transactional=True,
    policy="important-payment",
)
app.register_blueprint(payments_api)
```

Jangan menggabungkan `protect_blueprint()` dan `@ratf.protect()` pada route yang
sama karena request akan dievaluasi dua kali. Request `OPTIONS` dilewati secara
bawaan agar CORS preflight tidak dianggap sebagai akses bisnis; gunakan
`include_options=True` hanya bila aplikasi memang mengevaluasinya sendiri.

Response memuat `X-RATF-Policy`, `X-RATF-Decision`,
`X-RATF-Effective-Decision`, `X-RATF-Reason`, dan `X-RATF-Score` agar keputusan
dapat diamati tanpa membuka access token.

## Konfigurasi melalui aplikasi

Policy juga dapat diletakkan pada konfigurasi Flask sehingga tidak tersebar di
setiap endpoint:

```python
app.config["RATF_POLICIES"] = {
    "important-payment": {
        "weights": {
            "ip": .30,
            "device": .25,
            "time": .10,
            "frequency": .20,
            "token_history": .15,
        },
        "thresholds": {"verify": .70, "allow": .88},
        "burst_soft_limit": 15,
        "burst_hard_limit": 40,
    }
}
```

## Identity Provider dan step-up

Gunakan `CallbackIdentityProvider` jika aplikasi sudah memiliki fungsi validasi
token, atau `OIDCIntrospectionIdentityProvider` untuk endpoint introspection.
R-ATF tidak mengambil alih proses login dan tidak menerbitkan token produksi.

Keputusan `verify` memanggil `StepUpHandler`. Hook hanya membuat atau memulai
challenge; keberhasilan MFA harus divalidasi oleh Identity Provider, bukan
dipercaya dari nilai `verified=true` yang dikirim client.

Contoh integrasi yang tidak mengaktifkan dashboard terdapat di
`examples/production_flask/app.py`.

## Bahasa selain Python

Aplikasi Node.js, Java, Go, PHP, atau bahasa lain menggunakan R-ATF sebagai
Policy Decision Point melalui:

```text
POST /access/v1/evaluation
```

Kirim `context.policy_id` untuk memilih policy terdaftar. Aplikasi tetap menjadi
Policy Enforcement Point yang meneruskan atau menahan request berdasarkan
boolean `decision`. Detail tiga keputusan R-ATF berada pada
`context.ratf.decision`.

Kontrak lengkap tersedia pada `src/ratf/openapi/ratf-evaluation.openapi.yaml`.

## Syarat penerapan

- Redis yang persisten dan tersedia bagi seluruh instance aplikasi;
- HTTPS serta reverse proxy yang dikonfigurasi sebagai trusted proxy;
- sinkronisasi waktu server;
- secret manager untuk audit dan token hashing;
- access token serta scope dari Identity Provider;
- proses MFA nyata untuk keputusan `verify`;
- penalaan bobot dan threshold berdasarkan risiko aplikasi;
- observability, backup, failover, serta security review sebelum produksi.

Memory storage dan dashboard lokal hanya digunakan untuk pengembangan.
