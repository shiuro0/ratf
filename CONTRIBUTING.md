# Contributing

Kontribusi harus mempertahankan pemisahan antara core, adapter framework web,
dan artefak penelitian. Perubahan keputusan keamanan wajib menyertakan test dan
tidak boleh mengubah hasil eksperimen lama secara diam-diam.

Sebelum membuat pull request:

```bash
pip install -e ".[demo,test]"
python run_all_checks.py
```

Jangan memasukkan `.env`, secret, access token, audit log mentah, atau data
pengguna. Jelaskan perubahan perilaku, alasan keamanan, dan kompatibilitasnya
pada pull request.
