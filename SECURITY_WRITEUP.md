# DevSecOps Pipeline Demo — Security Write-up

## Мета проєкту

Показати, як CI/CD pipeline на базі GitHub Actions автоматично виявляє
вразливості в коді (SAST) та в залежностях (dependency scanning) ще до
того, як код потрапить у продакшн.

## Архітектура pipeline

`.github/workflows/security.yml` запускається на кожен `push` і `pull_request`
у гілку `main` та складається з чотирьох job'ів:

| Job | Інструмент | Що перевіряє |
|---|---|---|
| `bandit` | [Bandit](https://bandit.readthedocs.io/) | SAST для Python: небезпечні виклики, injection-патерни |
| `semgrep` | [Semgrep](https://semgrep.dev/) | SAST з правилами `auto` (OWASP Top 10, CWE) |
| `dependency-check` | [Safety](https://pyup.io/safety/) | Відомі CVE в пакетах з `requirements.txt` |
| `gate` | — | Підсумковий job-гейт, залежний від трьох попередніх |

Результати Bandit і Semgrep вантажаться у форматі SARIF у вкладку
**Security → Code scanning alerts** репозиторію.

## Знайдені вразливості в `app/main.py`

| ID | Вразливість | CWE | Рядок / місце | Хто ловить |
|---|---|---|---|---|
| VULN-01 | Hardcoded secret key | CWE-798 | `app.secret_key = "..."` | Semgrep, Bandit (B105) |
| VULN-02 | SQL Injection через string formatting | CWE-89 | `login()`, `%s`-запит | Bandit (B608), Semgrep |
| VULN-03 | Слабкий алгоритм хешування — MD5 для паролів | CWE-327 | `register()`, `hashlib.md5` | Bandit (B303/B324) |
| VULN-04 | OS Command Injection через `shell=True` | CWE-78 | `ping()` | Bandit (B602/B605), Semgrep |
| VULN-05 | Server-Side Template Injection | CWE-1336 | `greet()`, `render_template_string` | Semgrep |
| VULN-06 | Розкриття інформації — весь `os.environ` у відповіді | CWE-200 | `debug_info()` | Semgrep (custom rule) |
| VULN-07 | Debug mode + bind на `0.0.0.0` | CWE-489, CWE-605 | `app.run(debug=True, host="0.0.0.0")` | Bandit (B104, B201) |

## Вразливі залежності в `requirements.txt`

Пакети навмисно зафіксовані на старих версіях, щоб `safety check` знайшов
реальні опубліковані CVE:

- **Flask 0.12.2** — множинні відомі проблеми, застаріла гілка без патчів
- **Jinja2 2.10.1** — вразливість sandbox escape (CVE-2019-10906) та інші
- **Werkzeug 0.15.4** — DoS та проблеми з debugger console
- **urllib3 1.24.1** — CVE-2019-11324 (некоректна перевірка сертифікатів)
- **requests 2.19.1** — витік заголовка `Authorization` при редиректах на інший хост
- **PyYAML 5.3** — небезпечний `yaml.load` без `SafeLoader` (CVE-2020-1747, CVE-2020-14343)

`safety check` виводить список CVE ID, severity та рекомендовану версію
для апгрейду по кожному пакету.

## Як це працює в pipeline на практиці

1. Розробник робить `push` або відкриває `pull request` у `main`.
2. GitHub Actions паралельно запускає `bandit`, `semgrep`, `dependency-check`.
3. Bandit і Semgrep публікують SARIF-звіти → вони з'являються як anotації
   прямо в diff pull request'а та у вкладці Security.
4. Safety виводить у логи job'а список CVE з посиланнями.
5. Job `gate` — точка, куди пізніше можна додати `if: failure()` /
   `exit 1`, щоб pipeline блокував merge при critical/high знахідках
   (зараз стоїть `continue-on-error: true`, щоб pipeline не падав під час
   демонстрації і всі звіти встигали завантажитись).

## Що можна зробити далі (roadmap)

- Прибрати `continue-on-error` для критичних severity, залишивши його
  тільки для low/medium — це перетворить сканування на реальний quality gate.
- Додати `pip-audit` або OWASP Dependency-Check (Java-based) як другий
  незалежний сканер залежностей для крос-перевірки.
- Виправити всі 7 знайдених вразливостей у гілці `fix/security-issues` і
  показати "до/після" в pipeline — наочна демонстрація ефективності.
- Додати secret-scanning (наприклад, Gitleaks) окремим job'ом — hardcoded
  secret key (VULN-01) якраз це б підсвітив.
