# Quick Start

Panduan ini ditujukan untuk pengembang yang ingin mencoba RATF tanpa menyalin
source code modul ke aplikasi mereka.

## 1. Menjalankan showcase dari paket

Buat virtual environment Python 3.11 atau lebih baru, kemudian pasang RATF:

```bash
python -m pip install ratf
```

### PyCharm

1. Buka **Run → Edit Configurations**.
2. Tekan **+** dan pilih **Python**.
3. Pilih **Module name**.
4. Isi module dengan `ratf.showcase`.
5. Pastikan interpreter yang dipilih sudah memiliki paket `ratf`.
6. Tekan **Run**.

Showcase akan membuka UHAMKA Mart pada `http://127.0.0.1:5100/`. Control Room
tersedia pada `http://127.0.0.1:5100/ratf/dashboard/`.

Jika versi `ratf` belum tersedia di PyPI, pasang langsung dari repository:

```bash
python -m pip install "ratf[demo] @ git+https://github.com/shiuro0/ratf.git@v0.2.0"
```

## 2. Menjalankan contoh dari repository

Pasang source dalam mode editable:

```bash
python -m pip install -e ".[demo,test]"
```

Kemudian:

1. Run `examples/flask_app/app.py` sebagai server.
2. Run `examples/flask_app/run_client.py` sebagai client.

Konsol client memperlihatkan HTTP status, keputusan, trust score, reason code,
context history, dan integritas audit.

## 3. Memasang pada aplikasi Flask

Integrasi minimum memiliki empat bagian:

1. storage untuk nonce, rate limit, dan histori konteks;
2. adapter untuk memvalidasi token aplikasi;
3. policy berisi bobot dan ambang;
4. decorator pada endpoint yang ingin dilindungi.

Gunakan Redis pada aplikasi yang menjalankan lebih dari satu proses:

```python
from ratf import RATF
from ratf.identity import CallbackIdentityProvider
from ratf.storage import RedisStorage


def validate_token(access_token, context):
    # idp_aplikasi adalah client Identity Provider milik aplikasi Anda.
    claims = idp_aplikasi.introspect(access_token)
    if not claims.get("active"):
        return None
    return {
        "active": True,
        "subject": claims["sub"],
        "client_id": claims["client_id"],
        "scope": claims["scope"],
        "family_id": claims.get("sid", claims["sub"]),
        "metadata": claims,
    }


ratf = RATF(
    storage=RedisStorage("redis://127.0.0.1:6379/0"),
    identity_provider=CallbackIdentityProvider(validate_token),
)
```

Daftarkan policy dan inisialisasi extension:

```python
checkout = ratf.policy(
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
```

Lindungi endpoint:

```python
@app.post("/api/orders")
@ratf.protect("orders:write", transactional=True, policy=checkout)
def create_order():
    return {"status": "created"}, 201
```

## 4. Memeriksa hasil

Respons endpoint yang dilindungi memuat header berikut:

```text
X-RATF-Decision
X-RATF-Effective-Decision
X-RATF-Reason
X-RATF-Score
X-RATF-Policy
```

Keputusan `verify` tidak otomatis menyelesaikan MFA. Hubungkan step-up hook ke
OTP, passkey, atau layanan MFA aplikasi. Lihat
[DEVELOPER_INTEGRATION.md](DEVELOPER_INTEGRATION.md).

## 5. Sebelum produksi

Matikan experiment mode, lindungi dashboard, gunakan HTTPS dan secret manager,
aktifkan Redis persistence/failover, hubungkan Identity Provider nyata, serta
uji policy dengan pola penggunaan aplikasi sendiri. Nilai penelitian merupakan
titik awal, bukan nilai universal untuk semua endpoint.
