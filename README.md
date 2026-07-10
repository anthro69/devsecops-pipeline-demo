# DevSecOps Pipeline Demo

Навмисно вразливий Python/Flask-додаток для демонстрації автоматизованого
сканування безпеки в CI/CD pipeline на базі GitHub Actions.

## Мета

Показати як SAST та dependency-сканування автоматично виявляють вразливості
на кожному push — ще до того як код потрапляє у production.

## Стек

- **Додаток**: Python / Flask (навмисно вразливий)
- **SAST**: Bandit, Semgrep
- **Dependency scanning**: Safety
- **CI/CD**: GitHub Actions

## Вразливості у проєкті

| Вразливість | Розташування | CWE |
|---|---|---|
| SQL Injection | `app/main.py` → `/login` | CWE-89 |
| Command Injection | `app/main.py` → `/ping` | CWE-78 |
| Open Redirect | `app/main.py` → `/login` | CWE-601 |
| Слабке хешування (MD5) | `app/main.py` → `/hash` | CWE-327 |
| Debug Mode увімкнений | `app/main.py` | CWE-94 |
| Hardcoded Credentials | `app/main.py` | CWE-798 |
| Вразливі залежності | `requirements.txt` | CVE-various |

## Як запустити локально

```bash
pip install -r requirements.txt
python app/main.py
```

## Результати сканування

Після кожного push у вкладці **Actions** запускається pipeline.
JSON-звіти доступні як артефакти:
- `bandit-report.json`
- `semgrep-report.json`

## Документація

- [WRITEUP.md](WRITEUP.md) — технічний опис вразливостей та як їх виправити
- [SECURITY_WRITEUP.md](SECURITY_WRITEUP.md) — звіт з реальними результатами сканування

>  Це навчальний проєкт з навмисно вразливим кодом.
> Не деплоїти у production.
