# Catatan Implementasi v6.0

## Urutan kontrol

1. Bearer token tersedia.
2. JWT diverifikasi atau opaque token dicari pada registry.
3. Status active, expiration, issuer, audience, client, registry claims, dan scope diperiksa.
4. Device binding, timestamp, dan HMAC request proof diverifikasi.
5. Nonce dan idempotency diklaim secara atomik.
6. Rate limit dihitung.
7. Standard mode meneruskan request.
8. R-ATF menghitung trust score.
9. Context history diperbarui hanya setelah allow.
10. Keputusan dan bukti ditulis ke audit hash chain.

## Koreksi S7

GET dan HEAD tidak mengirim body JSON. Runner karena itu menandatangani
`SHA256(b"")`, bukan hash serialisasi `{}`. Fase setup memakai token family dan
endpoint yang sama sampai counter mencapai hard limit. Fase serangan kemudian
tetap memakai nonce/request ID baru, sehingga HTTP 429 hanya dapat diatribusikan
pada rate limit, bukan replay atau signature failure.

Analyzer memeriksa keputusan, HTTP status, reason code, metode, endpoint,
keunikan nonce/request ID, urutan fase, dan counter 1 sampai hard limit + N.

## Formula

```text
TS = w1Cip + w2Cdevice + w3Ctime + w4Freq + w5Htoken
```

Konteks penerbitan token menjadi baseline awal. Ini mengurangi blind spot ketika token dicuri sebelum protected request pertama. IP dan user-agent tetap hanya indikator risiko, bukan bukti identitas.

## Access-token replacement

Token baru pada session family yang sama mencabut token sebelumnya secara default. Mekanisme ini bertujuan membatasi kumpulan access token aktif pada eksperimen. Istilah ini bukan OAuth refresh-token rotation dan tidak diklaim sebagai implementasi authorization server standar.

## Pencegahan profile poisoning

Request verify dan block tidak ditambahkan ke histori tepercaya. Tanpa aturan ini, penyerang dapat mengirim konteks anomali berulang sampai konteks tersebut dianggap normal.

## Reproducibility

Kontrak S1–S15 berada pada `scripts/scenario_contract.py`. Setiap manifest
menyimpan fingerprint kontrak dan parameter protokol. Agregasi serta
perbandingan berhenti apabila fingerprint tidak identik atau salah satu quality
report gagal.
