# 🎬 CineGuess Cloud

Game tebak film berbasis cloud — tebak judul film dari clue yang dibuka satu per satu. Semakin sedikit clue yang dipakai, semakin tinggi skormu!

## Tech Stack

| Komponen | Teknologi |
|---|---|
| Backend | Python + Flask |
| Object Storage | MiniStack S3 |
| Database | MiniStack DynamoDB |
| Data Film | TMDB API |
| Frontend | HTML + CSS + JavaScript |

## Cara Menjalankan

### Prasyarat
- Python 3.12
- Docker Desktop
- AWS CLI (konfigurasi dengan nilai dummy)

```
aws configure
Access Key ID     : test
Secret Access Key : test
Default Region    : us-east-1
Output Format     : json
```

### Setup (sekali saja)
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Ubah Isi File .env
```
TMDB_API_KEY=masukkan_api_disini
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
MINISTACK_ENDPOINT=http://localhost:4566
```
Ganti teks "masukkan_api_disini" dengan TMDB API Key yang tertera di user manual

### Jalankan Aplikasi
```bash
# Terminal 1 — jalankan MiniStack
docker run -p 4566:4566 ministackorg/ministack

# Terminal 2 — jalankan Flask
venv\Scripts\activate
python setup.py
python initialmovie.py
python app.py
```

Buka browser: **http://localhost:5000**
