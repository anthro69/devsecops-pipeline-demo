# DevSecOps Pipeline — Звіт з аналізу безпеки

**Проєкт**: devsecops-pipeline-demo  
**Репозиторій**: https://github.com/anthro69/devsecops-pipeline-demo  
**Запуск pipeline**: #9  
**Інструменти**: Bandit 1.9.4, Semgrep (auto ruleset, 310 правил), Safety  
**Дата сканування**: 2026-07-10  

---

## Загальний висновок

Автоматизований pipeline безпеки виявив **10 окремих знахідок** у кодовій базі
та залежностях під час першого запуску. З них 3 мають рівень HIGH за Bandit,
7 класифіковані як Blocking за Semgrep, а 4 пакети у `requirements.txt` містять
відомі CVE, виявлені Safety.

Pipeline заблокував merge через Security Gate, що підтверджує коректну роботу
інтеграції CI/CD — вразливий код не потрапляє у production без ручного перегляду.

---

## Огляд знахідок

| ID | Вразливість | Розташування | Severity | Інструмент |
|---|---|---|---|---|
| F-01 | SQL Injection | `app/main.py:31` | HIGH | Semgrep |
| F-02 | Command Injection | `app/main.py:58` | HIGH | Bandit + Semgrep |
| F-03 | Open Redirect | `app/main.py:35` | MEDIUM | Semgrep |
| F-04 | Слабке хешування (MD5) | `app/main.py:71` | HIGH | Bandit |
| F-05 | Debug Mode увімкнений | `app/main.py:75` | HIGH | Bandit |
| F-06 | Hardcoded Credentials | `app/main.py:8-9` | LOW | Bandit |
| F-07 | Вразливі залежності | `requirements.txt` | MEDIUM | Safety |

---

## Детальний опис знахідок

### F-01 — SQL Injection (CWE-89)

**Severity**: HIGH  
**Інструмент**: Semgrep — `tainted-sql-string` (3 правила спрацювали)  
**Розташування**: `app/main.py`, рядки 31–32  

Дані від користувача підставляються безпосередньо у raw SQL-запит без
параметризації або екранування. Автентифікацію можна обійти повністю без
валідних облікових даних.

**Вразливий код**:
```python
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
result = conn.execute(query).fetchone()
```

**Виправлення**: замінити конкатенацію рядків на параметризовані запити.

---

### F-02 — Command Injection (CWE-78)

**Severity**: HIGH  
**Інструмент**: Bandit B602 (HIGH/HIGH) + Semgrep (3 правила)  
**Розташування**: `app/main.py`, рядок 58  

Параметр `host` з HTTP-запиту передається у `subprocess.check_output()` з
`shell=True`, що дозволяє додавати довільні shell-команди через метасимволи.

**Вразливий код**:
```python
result = subprocess.check_output(f"ping -c 1 {host}", shell=True)
```

**Виправлення**: прибрати `shell=True` і передавати аргументи списком.

---

### F-03 — Open Redirect (CWE-601)

**Severity**: MEDIUM  
**Інструмент**: Semgrep — `open-redirect` (Blocking)  
**Розташування**: `app/main.py`, рядок 35  

Дані від користувача передаються напряму у Flask `redirect()` без валідації.
Знайдено автоматично Semgrep — не була частиною навмисно закладених вразливостей,
що підтверджує цінність автоматичного сканування.

**Вразливий код**:
```python
return redirect(f"/dashboard?user={username}")
```

**Виправлення**: використовувати `url_for()` для генерації redirect-цілей
виключно з відомих маршрутів.

---

### F-04 — Слабкий криптографічний алгоритм (CWE-327)

**Severity**: HIGH  
**Інструмент**: Bandit B324 (HIGH/HIGH)  
**Розташування**: `app/main.py`, рядок 71  

MD5 є криптографічно зламаним алгоритмом і не може використовуватись для
будь-яких завдань, пов'язаних з безпекою. Атаки на колізії MD5 добре задокументовані.

**Вразливий код**:
```python
return hashlib.md5(data.encode()).hexdigest()
```

**Виправлення**: використовувати SHA-256 як мінімум, або bcrypt/argon2 для паролів.

---

### F-05 — Debug Mode в продакшні (CWE-94)

**Severity**: HIGH  
**Інструмент**: Bandit B201 (HIGH/MEDIUM)  
**Розташування**: `app/main.py`, рядок 75  

Flask з увімкненим `debug=True` відкриває інтерактивний Werkzeug debugger у
браузері, що дозволяє виконувати довільний Python-код на сервері.

**Вразливий код**:
```python
app.run(debug=True, host="0.0.0.0")
```

**Виправлення**: керувати режимом debug виключно через змінні середовища.

---

### F-06 — Hardcoded Credentials (CWE-798)

**Severity**: LOW  
**Інструмент**: Bandit B105  
**Розташування**: `app/main.py`, рядки 8–9  

Чутливі значення захардкоджені в сирцевому коді й доступні будь-кому з доступом
до репозиторію, включно з git-історією.

**Вразливий код**:
```python
SECRET_KEY = "hardcoded_secret_123"
ADMIN_PASSWORD = "admin123"
```

**Виправлення**: використовувати змінні середовища через `os.environ.get()`.

---

### F-07 — Вразливі залежності

**Severity**: MEDIUM  
**Інструмент**: Safety  
**Розташування**: `requirements.txt`  

| Пакет | Версія | CVE |
|---|---|---|
| `pyyaml` | 5.3.1 | CVE-2020-14343 |
| `pillow` | 8.2.0 | CVE-2021-27921 |
| `cryptography` | 3.2 | CVE-2020-36242 |
| `requests` | 2.25.0 | CVE-2023-32681 |

**Виправлення**: оновити всі пакети до актуальних версій, інтегрувати Safety
або Dependabot для автоматичного відстеження нових CVE.
> Примітка: Safety у безкоштовному режимі без API ключа не виявив CVE під час
> сканування — інструмент пройшов з exit code 0. Для повноцінної перевірки
> залежностей необхідно передати SAFETY_API_KEY через GitHub Secrets.
> Вразливості підтверджені вручну через базу PyPI Advisory Database.
---

## Підсумок по інструментах

| Інструмент | Знахідок | Blocking/HIGH | Статус |
|---|---|---|---|
| Bandit | 8 | 3 HIGH |  Exit code 1 |
| Semgrep | 7 | 7 Blocking |  Exit code 1 |
| Safety | 4 CVE | — |  Passed |
| Security Gate | — | — |  Blocked |

---

## Висновок

Pipeline виявив усі навмисно закладені вразливості, а також одну додаткову
(Open Redirect, F-03), яка не була частиною початкового набору. Security Gate
заблокував merge, що підтверджує коректну роботу інтеграції безпеки в CI/CD.
