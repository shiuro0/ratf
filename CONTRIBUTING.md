# Contributing

Kontribusi harus mempertahankan pemisahan antara core, adapter web, dan aplikasi
contoh. Perubahan keputusan keamanan wajib menyertakan test serta penjelasan
dampaknya terhadap kompatibilitas dan model ancaman.

Sebelum membuat pull request:

```bash
pip install -e ".[demo,test]"
python run_checks.py
```

Jangan memasukkan `.env`, secret, access token, audit log mentah, atau data
pengguna. Jelaskan perubahan perilaku, alasan keamanan, dan kompatibilitasnya
pada pull request.

Jangan commit folder `results/`, `reports/`, `build/`, atau `dist/`. Hasil test
sementara cukup ditampilkan pada CI atau konsol pengembang.
