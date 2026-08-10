# Riwayat Koreksi False Positive (dipertahankan pada v6.0)

False positive pada paket lama muncul karena payload bisnis yang sama dianggap replay. Access token dan payload memang dapat digunakan berulang secara sah.

Perbaikan yang diperkenalkan pada v5 dan dipertahankan pada v6.0:

1. fingerprint hanya menjadi bukti audit;
2. nonce dan idempotency key harus unik pada request sah;
3. klaim nonce memakai operasi atomik;
4. request setup tidak dihitung;
5. context history hanya belajar dari request allow;
6. verify dilaporkan sebagai challenge rate;
7. perubahan subnet yang masih wajar diberi penalti ringan;
8. S15 menguji perpindahan jaringan besar agar strict FPR tidak hanya diuji pada kondisi ideal;
9. analyzer menolak duplikasi nonce/idempotency di luar S4;
10. manifest dan config fingerprint mencegah hasil dari konfigurasi berbeda tercampur.
