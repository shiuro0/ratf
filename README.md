# R-ATF Framework 0.1.3

R-ATF adalah framework keamanan adaptif berbasis aturan untuk mengevaluasi
setiap request API setelah autentikasi dasar berhasil. Framework menghitung
trust score dari konsistensi IP, perangkat, waktu, frekuensi, dan riwayat
penggunaan token, lalu menghasilkan `allow`, `verify`, atau `block`.

Versi 0.1 menyatukan produk framework dan artefak penelitian dalam satu proyek.
Algoritma eksperimen lama tetap digunakan sebagai sumber keputusan; lapisan baru
menambahkan API publik, integrasi Identity Provider, Flask extension, AuthZEN,
shadow mode, step-up hook, contoh Node.js, dan dashboard.

## Penggunaan pada aplikasi sebenarnya

Dashboard bersifat opsional. Integrasi utama dilakukan melalui Flask extension
atau evaluation service HTTP. Contoh endpoint penting dengan policy tersendiri:

```python
from flask import Flask, jsonify
from ratf import RATF

app = Flask(__name__)
ratf = RATF(identity_provider=idp_aplikasi, storage=redis_storage)

api_penting = ratf.policy(
    "api-penting",
    weights={
        "ip": 0.30,
        "device": 0.25,
        "time": 0.10,
        "frequency": 0.20,
        "token_history": 0.15,
    },
    thresholds={"verify": 0.70, "allow": 0.88},
)

ratf.init_app(app)

@app.post("/api/payments")
@ratf.protect("payments:write", transactional=True, policy=api_penting)
def create_payment():
    return jsonify({"status": "accepted"}), 201
```

Bobot menentukan kontribusi komponen trust score, sedangkan threshold menentukan
batas keputusan. Policy per-endpoint tidak mengubah konfigurasi global dan nama
policy dicatat pada response serta audit.

Untuk sekelompok endpoint, `ratf.protect_blueprint(...)` dapat memasang policy
yang sama satu kali pada seluruh Flask Blueprint.

Dokumentasi integrasi lengkap terdapat di
`docs/DEVELOPER_INTEGRATION.md`. Contoh tanpa dashboard terdapat di
`examples/production_flask/app.py`.

## Distribusi internet

Source code sudah memiliki metadata paket, CI, workflow rilis, lisensi, security
policy, artefak wheel, serta aplikasi showcase yang ikut masuk ke paket. Setelah
project PyPI diaktifkan oleh pemilik, komputer lain cukup menjalankan:

```bash
pip install ratf-framework
```

Pengguna yang sudah memasang versi sebelumnya dapat memperbarui package tanpa
memindahkan folder proyek:

```bash
pip install --upgrade --no-cache-dir ratf-framework==0.1.3
```

Flask dan Waitress sudah menjadi dependency paket. Pengembang tidak perlu
mengunduh atau memindahkan folder repository untuk menjalankan showcase.

Perintah tersebut belum akan mengambil versi ini dari internet sebelum paket
benar-benar dipublikasikan. Panduan pemilik paket berada di
`docs/PUBLIC_DISTRIBUTION.md`.

### Menjalankan showcase dari paket terpasang

Pada PyCharm, buat **Python Run Configuration**, pilih **Module name**, lalu isi:

```text
ratf.showcase
```

Klik **Run**. Browser akan terbuka pada `http://127.0.0.1:5100/`. Cara yang sama
dapat dipakai melalui konfigurasi module pada VS Code. Alternatif terminalnya:

```bash
ratf-showcase
```

Halaman utama adalah aplikasi dagang fiktif **UHAMKA Mart**, bukan halaman admin
framework. Halaman tersebut sengaja hanya menampilkan pengalaman belanja agar
terlihat seperti aplikasi milik pengembang. Request checkout dapat diperiksa
melalui **Chrome DevTools → Network**, termasuk token demonstrasi yang dikirim
lengkap pada header `Authorization`.

Seluruh penjelasan R-ATF dipusatkan pada **Control Room** di
`http://127.0.0.1:5100/ratf/dashboard/`. Penguji dapat mencoba penggunaan normal,
perpindahan token ke perangkat lain, exact replay, dan konteks berisiko tinggi;
mengubah bobot serta batas keputusan; mengembalikan nilai penelitian; lalu
melihat keputusan, komponen skor, riwayat konteks, audit, dan ringkasan hasil
penelitian.

## Mencoba contoh yang tersedia

Struktur contoh lama tetap digunakan. Untuk Python, Run
`examples/flask_app/app.py`, kemudian Run `examples/flask_app/run_client.py`.
Hasilnya memperlihatkan request normal, perubahan konteks, exact replay, dan
snapshot debug histori konteks.

Untuk Node.js, biarkan contoh Flask aktif sebagai evaluation service, lalu
jalankan `examples/nodejs/server.mjs` dan `run_client.mjs`. Contoh Node.js tidak
memiliki dependency npm tambahan.

Nama `v6` pada skrip lama adalah nomor iterasi paket eksperimen, sedangkan
`0.1.0` adalah versi semantik pertama untuk produk library. Perubahan nomor ini
bukan penurunan fitur dan tidak mengubah data eksperimen v6.

## Demonstrasi melalui PyCharm

Cara paling mudah untuk demonstrasi:

1. buka proyek ini di PyCharm;
2. pasang dependency dengan `pip install -e ".[demo]"`;
3. Run `run_dashboard.py`;
4. gunakan aplikasi UHAMKA Mart pada `http://127.0.0.1:5100/`;
5. buka **R-ATF Control Room** untuk mengubah bobot atau threshold.

Bagian **Hasil penelitian** membaca ringkasan data pengujian akhir yang disimpan
di dalam paket: 31.220 baris keamanan, 40 measured run k6, perubahan 3.000
request kontekstual, 4.000 request sah, serta overhead utama. Nilai tersimpan
tersebut ditampilkan terpisah dari hasil request interaktif di Control Room.

Urutan presentasi singkat tersedia pada
`docs/PANDUAN_DEMONSTRASI_PENGUJI.md`.

Showcase memakai memory storage agar dapat langsung dijalankan dengan satu
perintah. Ini sengaja diberi label demonstrasi satu proses. Untuk memakai Redis,
set `RATF_SHOWCASE_STORAGE=redis` dan `RATF_SHOWCASE_REDIS_URL` ke database Redis
khusus karena tombol reset membersihkan state showcase.

## Memasang sebagai Flask extension

Paket dapat dibangun menjadi wheel atau dipasang langsung dari folder proyek:

```powershell
pip install -e ".[flask]"
```

Penggunaan minimal:

```python
from flask import Flask, jsonify
from ratf import RATF

app = Flask(__name__)
ratf = RATF(app)

@app.post("/orders")
@ratf.protect("orders:write", transactional=True)
def create_order():
    return jsonify({"status": "created"}), 201
```

Secara default adapter lokal memeriksa JWT atau opaque token pada registry
R-ATF. Aplikasi yang sudah memiliki Identity Provider dapat menggantinya:

```python
from ratf import RATF
from ratf.identity import CallbackIdentityProvider

def validate_with_application(access_token, context):
    claims = application_idp.introspect(access_token)
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

ratf = RATF(identity_provider=CallbackIdentityProvider(validate_with_application))
ratf.init_app(app)
```

Tersedia pula `OIDCIntrospectionIdentityProvider` untuk endpoint introspection
OAuth/OIDC milik aplikasi.

## Mengubah bobot dan threshold

Kebijakan tidak ditanam langsung pada endpoint. Pengembang dapat mengubahnya
melalui konfigurasi:

```python
from ratf.core import CoreConfig

policy = CoreConfig(
    weight_ip=0.20,
    weight_device=0.30,
    weight_time=0.10,
    weight_frequency=0.15,
    weight_token_history=0.25,
    verify_threshold=0.60,
    allow_threshold=0.85,
)
app.config["RATF_CORE_CONFIG"] = policy
```

Bobot dinormalisasi menjadi total satu dan konfigurasi ditolak bila threshold
tidak memenuhi `0 <= verify < allow <= 1`. Dashboard mengubah objek kebijakan
yang sama, bukan algoritma salinan.

## Shadow mode dan step-up hook

Shadow mode mengamati keputusan kontekstual tanpa langsung menghentikan request:

```python
app.config["RATF_SHADOW_MODE"] = True
```

Respons tetap memuat `X-RATF-Decision` sebagai keputusan yang seharusnya terjadi
dan `X-RATF-Effective-Decision` sebagai tindakan aktual. Autentikasi gagal,
scope salah, exact replay, dan hard rate limit tetap diblokir; shadow mode tidak
dipakai untuk melewati kontrol dasar.

Metode autentikasi tambahan tetap menjadi milik aplikasi. Framework menyediakan
hook untuk menghasilkan challenge:

```python
from ratf.core import StepUpChallenge
from ratf.core.ports import CallbackStepUpHandler

def start_step_up(context, identity, evaluation):
    return StepUpChallenge(
        challenge_type="totp",
        challenge_url=f"/mfa/{identity.subject}",
        expires_in=180,
    )

ratf = RATF(step_up_handler=CallbackStepUpHandler(start_step_up))
```

Hook tidak menerima nilai `verified=true` dari client sebagai bukti. Aplikasi
atau IdP tetap harus memvalidasi MFA dan menerbitkan sesi/token yang sesuai.

## Integrasi bahasa lain melalui AuthZEN

R-ATF menyediakan endpoint evaluasi:

```text
POST /access/v1/evaluation
```

Format request memakai entitas `subject`, `resource`, `action`, dan `context`.
Boolean AuthZEN berada pada `decision`; hasil tiga-arah R-ATF, trust score,
reason code, shadow status, dan challenge step-up berada pada
`context.ratf`. Spesifikasi OpenAPI tersedia di
`src/ratf/openapi/ratf-evaluation.openapi.yaml`.

Contoh lengkap:

- `examples/flask_app/app.py`: extension langsung dan IdP callback;
- `examples/flask_app/run_client.py`: normal, exact replay, dan konteks berbeda;
- `examples/nodejs/server.mjs`: Node.js sebagai policy-enforcement point;
- `examples/nodejs/run_client.mjs`: client untuk contoh Node.js.

Node.js tidak menjalankan kode Python di dalam aplikasinya. Ia meminta keputusan
ke evaluation service melalui HTTP, sehingga core dan policy tetap satu sumber.

## Struktur proyek

```text
src/ratf/core/           core tanpa ketergantungan Flask
src/ratf/flask_extension.py
src/ratf/identity.py     kontrak IdP dan adapter
src/ratf/authzen.py      evaluation service
src/ratf/dashboard.py    dashboard demonstrasi
examples/                integrasi Flask dan Node.js
examples/production_flask/ contoh aplikasi tanpa dashboard
validation_tests/        pemeriksaan v0.1 berbasis unittest
demo_scenarios/          demonstrasi S1-S15 penelitian lama
scripts/, k6/, postman/  eksperimen Standard API vs R-ATF
results/                 hasil dan bukti, dipisahkan per jenis pengujian
```

Folder lama tidak menjadi framework kedua. `src/ratf/core` adalah sumber logika
utama; skrip S1-S15 dan k6 dipertahankan sebagai regression evidence dan
reproduksi penelitian. `SecurityMiddleware` lama dipertahankan sebagai adapter
kompatibilitas agar hasil v6 dapat direproduksi; integrasi baru menggunakan
`RATF` Flask extension.

## Pemeriksaan v0.1

Run `run_all_checks.py` dari PyCharm. Skrip ini tidak membutuhkan pytest dan
menjalankan kategori berikut secara berurutan:

- regression terhadap server penelitian lama;
- integration Flask extension, bobot, shadow mode, dan step-up;
- interoperability AuthZEN dan proses Node.js nyata;
- security untuk token hilang/palsu, scope, replay, serta audit;
- performance smoke test pada core.

Hasil terakhir ditulis ke
`results/v0_1_validation/validation_summary.json`. Microbenchmark core hanya
memeriksa regresi performa pengembangan. Angkanya tidak boleh menggantikan hasil
Docker, Gunicorn, Redis, dan k6 pada BAB IV.

## Artefak penelitian lama

Perbandingan Standard API dan R-ATF tetap dijalankan dengan Docker pada kondisi
yang sama. Panduan lengkap berada di `docs/PANDUAN_PENGUJIAN_FINAL.md`. Hasil
utama BAB IV berada di `results/research_final`, bukan
dari dashboard dan bukan dari Flask development server.

## Batas penggunaan

Versi 0.1 sudah dapat dipasang, dikonfigurasi, dan diintegrasikan, tetapi belum
diklaim siap produksi. Penerapan nyata masih memerlukan HTTPS/reverse proxy,
secret manager, IdP produksi, MFA end-to-end, Redis persistence/failover,
observability, pengujian multi-node, penalaan bobot berbasis risiko aplikasi,
dan security review tersendiri.
