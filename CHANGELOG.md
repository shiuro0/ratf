# Changelog

## v0.1.2 packaged showcase and control room

- Menambahkan showcase web NusaMart yang ikut terpasang dalam wheel dan dapat
  dijalankan melalui module `ratf.showcase` atau entry point `ratf-showcase`.
- Menambahkan alur visual allow, verify, exact replay, block konteks, shadow
  mode, inspeksi request/response, snapshot backend, dan kesiapan produksi.
- Memperbarui Control Room tanpa menghapus fungsi pengaturan policy dan
  menjadikan Flask serta Waitress dependency instalasi standar.
- Menambahkan pemeriksaan integrasi showcase dan instalasi wheel dari working
  directory di luar repository.
- Mempertahankan core, eksperimen keamanan, data k6, dan public API v0.1.1 agar
  pembaruan antarmuka tidak mengubah hasil penelitian lama.

## v0.1.1 public integration API

- Menambahkan `PolicyProfile` untuk bobot, threshold, shadow mode, dan batas
  burst yang dapat dikonfigurasi per-endpoint tanpa mengubah policy global.
- Menambahkan registry `ratf.policy()` dan parameter
  `@ratf.protect(..., policy=...)`.
- Menambahkan pemilihan `policy_id` pada evaluation service AuthZEN agar
  aplikasi non-Python dapat memakai profil kebijakan yang sama.
- Menambahkan nama policy pada response header, hasil evaluasi, dan audit.
- Menambahkan contoh endpoint pembayaran dengan policy lebih ketat serta
  dashboard untuk memilih policy endpoint.
- Menyederhanakan skrip pada folder contoh Flask dan Node.js yang sudah ada,
  serta menambahkan snapshot debug untuk histori konteks dan event terbaru.
- Menambahkan metadata distribusi, dokumentasi publikasi, dan workflow CI/PyPI.

## v0.1.0 reusable framework

- Memisahkan `RequestContext`, konfigurasi kebijakan, kontrak, dan evaluation
  engine dari Flask.
- Menambahkan packaging `pyproject.toml`, wheel, lisensi MIT, dan Flask
  extension `RATF`.
- Menambahkan adapter local registry, callback aplikasi, dan OIDC token
  introspection untuk Identity Provider.
- Menambahkan shadow mode yang tidak melewati autentikasi/replay serta step-up
  hook untuk MFA milik aplikasi.
- Menambahkan AuthZEN-compatible evaluation endpoint dan OpenAPI 3.1.
- Menambahkan contoh integrasi Flask dan Node.js serta dashboard konfigurasi.
- Menambahkan 12 validation test berbasis unittest; seluruhnya lulus pada
  regression, integration, interoperability, security, dan performance smoke.
- Mengimpor hasil eksperimen keamanan dan kinerja lama ke
  `results/research_final` dengan manifest sumber dan pemeriksaan konflik.
- Memperbarui naskah BAB I–V dan PPT tanpa mengubah angka eksperimen lama.

## Pembaruan client PyCharm

- Menempatkan body, konteks, dan request utama pada masing-masing file S1–S15.
- Memindahkan fungsi teknis yang berulang ke `demo_client_tools.py`.
- Mempertahankan penyamaran kredensial, hasil JSON, dan audit hash chain.

## v6.0 final fix

- Menyelaraskan HMAC GET/HEAD dengan body kosong agar S7 mencapai rate limiter.
- Membagi S7 menjadi setup sampai hard limit dan tepat N sampel serangan.
- Menambahkan response request-counter khusus bukti eksperimen.
- Membekukan kontrak keputusan/status/reason code untuk S1–S15.
- Menyamakan jumlah sampel primer seluruh skenario; current-token control S3
  dipindahkan menjadi setup.
- Menambahkan scenario-contract dan security-protocol fingerprint.
- Membuat analyzer gagal ketika skenario hilang, jumlah tidak tepat, fase salah,
  outcome menyimpang, atau bukti S7 tidak valid.
- Menambahkan paired preflight, exact repetition gate, counterbalancing, dan
  pencegahan pencampuran stale results.
- Menambahkan ekspor otomatis Tabel 4.15–4.18 dan final validation report.
- Memperbaiki Docker `PYTHONPATH`, package `scripts`, dan cache pytest non-root.
- Menambah regression suite dari 18 menjadi 26 test.
- Membersihkan residual state kedua Redis database sebelum setiap k6 run dan
  mewajibkan kelengkapan VU serta resource samples.

## v5 final testing protocol

- Menyelaraskan kriteria performa dengan proposal: tambahan p95 latency maksimal 10 ms.
- Menambahkan otomasi k6 lima pengulangan pada VUS 1, 10, 25, dan 50.
- Menambahkan warm-up, counterbalancing urutan sistem, serta pencatatan CPU/memori API dan Redis.
- Menambahkan analisis otomatis per-run, agregat mean/SD, dan perbandingan Standard versus R-ATF.
- Memisahkan latensi skenario keamanan dari bukti performa utama k6.

## v5 startup reliability fix

- Menambahkan entrypoint Docker dengan validasi konfigurasi, pemeriksaan izin audit log, dan bounded wait untuk Redis.
- Mencegah satu kegagalan ping Redis saat app factory dibentuk berubah menjadi restart loop Gunicorn.
- Mengembalikan HTTP 503 pada `/health` ketika storage tidak tersedia.
- Membatasi restart API menjadi lima percobaan dan menambahkan masa awal health check.
- Menambahkan pengujian untuk status health yang degraded.

## v5

- Mempertahankan judul penelitian dan menambahkan dokumen penyelarasan proposal.
- Menambahkan generated `.env`, strict startup, preflight, config snapshot, dan config fingerprint.
- Mengubah Redis menjadi fail-closed untuk eksperimen final.
- Melindungi device enrollment dan mencegah role/scope escalation dari token request.
- Device secret tidak lagi disimpan plaintext di Redis.
- Menambahkan baseline konteks saat token diterbitkan.
- Context history hanya belajar dari request allow untuk mencegah profile poisoning.
- Menggunakan atomic claim untuk nonce dan idempotency key.
- Memakai satu request counter untuk standard controls dan trust score.
- Menambahkan access-token replacement policy per session family.
- Menambahkan HMAC hash chain pada audit log.
- Menambahkan skenario stolen-before-first-use dan legitimate roaming.
- Menambahkan run manifest, experiment quality checks, repeated-run aggregation, dan system comparison.
- Menambahkan validasi payload order/pembayaran dan security response headers.
- Menjalankan container sebagai non-root dan membatasi port ke localhost.
- Menambahkan 15 unit/integration tests.

## v4

- Memperkuat baseline menjadi standard controls.
- Menambahkan JWT dan opaque token, registry, revocation, scope, nonce, device proof, rate limit, dan R-ATF.
- Memisahkan strict FPR, challenge rate, dan friction rate.
