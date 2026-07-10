# Write-up з безпеки: DevSecOps Pipeline Demo

## Загальний огляд

Цей документ описує навмисно закладені вразливості у демонстраційному додатку
та пояснює, як кожна з них виявляється автоматизованим pipeline безпеки
(Bandit, Semgrep, Safety).

---

## 1. SQL Injection — `/login` (CWE-89)

**Розташування**: `app/main.py`, рядки 31–32

**Код**:
```python
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
result = conn.execute(query).fetchone()
```

**Опис**: Дані від користувача підставляються напряму у raw SQL-запит без
параметризації або екранування. Автентифікацію можна обійти повністю, не маючи
валідних облікових даних — достатньо передати `' OR '1'='1' --` у поле username.

**Приклад експлуатації**:
username: ' OR '1'='1' --
password: anything
**Виявлено**:
- Semgrep `python.flask.security.injection.tainted-sql-string` — Blocking
- Semgrep `python.django.security.injection.tainted-sql-string` — Blocking
- Semgrep `python.sqlalchemy.security.sqlalchemy-execute-raw-query` — Blocking

**Виправлення**: замінити конкатенацію на параметризований запит:
```python
query = "SELECT * FROM users WHERE username=? AND password=?"
result = conn.execute(query, (username, password)).fetchone()
```

---

## 2. Command Injection — `/ping` (CWE-78)

**Розташування**: `app/main.py`, рядок 58

**Код**:
```python
result = subprocess.check_output(f"ping -c 1 {host}", shell=True)
```

**Опис**: Параметр `host` з HTTP-запиту передається у shell-команду з `shell=True`.
Зловмисник може дописати довільні команди через shell-метасимволи і виконати їх
на сервері.

**Приклад експлуатації**:
GET /ping?host=localhost;cat /etc/passwd
**Виявлено**:
- Bandit `B602` — Severity: High, Confidence: High
- Semgrep `python.flask.security.injection.subprocess-injection` — Blocking
- Semgrep `python.lang.security.dangerous-subprocess-use` — Blocking
- Semgrep `python.lang.security.audit.subprocess-shell-true` — Blocking

**Виправлення**: прибрати `shell=True` і передавати аргументи списком:
```python
result = subprocess.check_output(["ping", "-c", "1", host])
```

---

## 3. Open Redirect — `/login` (CWE-601)

**Розташування**: `app/main.py`, рядок 35

**Код**:
```python
return redirect(f"/dashboard?user={username}")
```

**Опис**: Значення `username` з запиту передається у `redirect()` без валідації.
Потенційно дозволяє перенаправити користувача на зовнішній шкідливий ресурс.

**Виявлено**:
- Semgrep `python.flask.security.open-redirect.open-redirect` — Blocking

> Ця вразливість не була закладена навмисно — її знайшов Semgrep автоматично
> під час першого запуску pipeline. Це підтверджує цінність автоматизованого
> сканування поза межами відомого списку проблем.

**Виправлення**: використовувати `url_for()` для формування redirect-цілей:
```python
return redirect(url_for("dashboard", user=username))
```

---

## 4. Слабкий алгоритм хешування — `/hash` (CWE-327)

**Розташування**: `app/main.py`, рядок 71

**Код**:
```python
return hashlib.md5(data.encode()).hexdigest()
```

**Опис**: MD5 є криптографічно зламаним алгоритмом. Атаки на колізії добре
задокументовані, і використовувати MD5 для будь-яких завдань безпеки —
зберігання паролів, перевірки цілісності даних — неприпустимо.

**Виявлено**:
- Bandit `B324` — Severity: High, Confidence: High

**Виправлення**: використовувати SHA-256 як мінімум, або bcrypt/argon2 для паролів:
```python
return hashlib.sha256(data.encode()).hexdigest()
```

---

## 5. Debug Mode у продакшні (CWE-94)

**Розташування**: `app/main.py`, рядок 75

**Код**:
```python
app.run(debug=True, host="0.0.0.0")
```

**Опис**: Flask з увімкненим `debug=True` відкриває інтерактивний Werkzeug
debugger у браузері. Це дозволяє виконувати довільний Python-код на сервері
без будь-якої автентифікації.

**Виявлено**:
- Bandit `B201` — Severity: High, Confidence: Medium

**Виправлення**: керувати режимом debug через змінні середовища:
```python
app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
```

---

## 6. Hardcoded Credentials (CWE-798)

**Розташування**: `app/main.py`, рядки 8–9

**Код**:
```python
SECRET_KEY = "hardcoded_secret_123"
ADMIN_PASSWORD = "admin123"
```

**Опис**: Чутливі значення захардкоджені у сирцевому коді й доступні будь-кому
з доступом до репозиторію — включно з git-історією, де їх не можна повністю
видалити без перезапису history.

**Виявлено**:
- Bandit `B105` — Severity: Low

**Виправлення**: виносити чутливі значення у змінні середовища:
```python
SECRET_KEY = os.environ.get("SECRET_KEY")
```

---

## 7. Вразливі залежності

**Розташування**: `requirements.txt`

**Виявлено**: Safety

| Пакет | Версія | CVE |
|---|---|---|
| `pyyaml` | 5.3.1 | CVE-2020-14343 |
| `pillow` | 8.2.0 | CVE-2021-27921 |
| `cryptography` | 3.2 | CVE-2020-36242 |
| `requests` | 2.25.0 | CVE-2023-32681 |

**Виправлення**: оновити всі пакети до актуальних версій та інтегрувати Safety
або Dependabot для автоматичного відстеження нових CVE при кожному push.

---

## Підсумок виявлення по pipeline

| # | Вразливість | CWE | Bandit | Semgrep | Safety |
|---|---|---|---|---|---|
| 1 | SQL Injection | CWE-89 | — | ✓ (3 правила) | — |
| 2 | Command Injection | CWE-78 | B602 HIGH | ✓ (3 правила) | — |
| 3 | Open Redirect | CWE-601 | — | ✓ | — |
| 4 | Слабке хешування (MD5) | CWE-327 | B324 HIGH | — | — |
| 5 | Debug Mode | CWE-94 | B201 HIGH | — | — |
| 6 | Hardcoded Credentials | CWE-798 | B105 LOW | — | — |
| 7 | Вразливі залежності | CVE-various | — | — | ✓ |

**Загалом: 7 Blocking знахідок Semgrep + 3 HIGH Bandit + 4 CVE Safety**

Усі сканування запускаються автоматично при кожному push та pull request.
Повні JSON-звіти доступні як артефакти у вкладці GitHub Actions.
