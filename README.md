# DevSecOps Pipeline Demo

CI/CD pipeline на GitHub Actions зі вбудованим security scanning для
Python (Flask) проєкту. Демонструє, як SAST та dependency-сканування
автоматично ловлять реальні вразливості ще до merge в `main`.

## Що всередині

- **`app/main.py`** — навмисно вразливий Flask-застосунок (тестовий
  полігон): SQL Injection, OS Command Injection, SSTI, слабке
  хешування паролів, hardcoded секрети та інше. Список і CWE-коди — в
  [`SECURITY_WRITEUP.md`](./SECURITY_WRITEUP.md).
- **`requirements.txt`** — залежності зі свідомо застарілими версіями,
  щоб dependency-сканер знаходив реальні опубліковані CVE.
- **`.github/workflows/security.yml`** — pipeline, що запускається на
  кожен `push`/`pull request` у `main`:
  - **Bandit** — SAST для Python-коду
  - **Semgrep** — SAST з правилами OWASP Top 10 / CWE
  - **Dependency check** — пошук CVE у залежностях

## Як запустити застосунок локально

```bash
git clone https://github.com/anthro69/devsecops-pipeline-demo.git
cd devsecops-pipeline-demo
pip install -r requirements.txt
python app/main.py
```

Застосунок підніметься на `http://localhost:5000`.

> ⚠️ Це навчальний проєкт з навмисно вразливим кодом. Не деплойте
> `app/main.py` у продакшн і не використовуйте в реальних застосунках.

## Як подивитись результати сканування

1. Зробіть будь-який push у гілку `main` (або відкрийте pull request).
2. Перейдіть у вкладку **Actions** репозиторію — там запуститься
   workflow **Security Pipeline**.
3. Звіти Bandit і Semgrep доступні як артефакти job'а та (якщо
   налаштовано SARIF-upload) у вкладці **Security → Code scanning**.

## Структура репозиторію

```
devsecops-pipeline-demo/
├── app/
│   └── main.py
├── .github/
│   └── workflows/
│       └── security.yml
├── requirements.txt
├── SECURITY_WRITEUP.md
└── README.md
```

## Документація

Детальний розбір знайдених вразливостей, CVE в залежностях і того, як
саме pipeline їх виявляє — у [`SECURITY_WRITEUP.md`](./SECURITY_WRITEUP.md).
