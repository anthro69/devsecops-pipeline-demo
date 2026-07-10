# DevSecOps Pipeline Demo — Security Write-up

## Мета проєкту

Показати, як CI/CD pipeline на базі GitHub Actions автоматично виявляє
вразливості в коді (SAST) та в залежностях (dependency scanning) ще до
того, як код потрапить у продакшн — і як перетворити сканування на
реальний quality gate, що блокує merge на critical-знахідках.

## Архітектура pipeline

`.github/workflows/security.yml` запускається на кожен `push` і `pull_request`
у гілку `main` та складається з шести job'ів:

| Job | Інструмент | Що перевіряє | Блокує merge? |
|---|---|---|---|
| `bandit` | [Bandit](https://bandit.readthedocs.io/) | SAST для Python: небезпечні виклики, injection-патерни | так, на HIGH severity |
| `semgrep` | [Semgrep](https://semgrep.dev/) | SAST з правилами `auto` (OWASP Top 10, CWE) | так, на ERROR severity |
| `safety` | [Safety](https://pyup.io/safety/) | Відомі CVE в пакетах з `requirements.txt` (база PyUp) | ні, informational |
| `pip-audit` | [pip-audit](https://pypi.org/project/pip-audit/) | Відомі CVE в пакетах (база OSV) — незалежна крос-перевірка | ні, informational |
| `gate` | — | Підсумковий job, дивиться на результати `bandit` і `semgrep` | так — падає, якщо впав хоч один |

Результати Bandit і Semgrep вантажаться у форматі SARIF у вкладку
**Security → Code scanning alerts**, а також як build-артефакти. Звіти
Safety і pip-audit доступні в логах job'а (pip-audit — ще й окремим
JSON-артефактом).

### Як влаштований quality gate

Кожен SAST-job розділений на два кроки:

1. **Full report** — сканує всі severity, завжди `continue-on-error: true`,
   щоб звіт встиг завантажитись навіть при знахідках.
2. **Gate-крок** — без `continue-on-error`, запускає той самий сканер
   з фільтром лише на критичну severity:
   - Bandit: `bandit -r app/ -lll` (тільки HIGH)
   - Semgrep: `semgrep scan --severity ERROR --error` (тільки ERROR)

Якщо gate-крок знаходить critical-issue — job падає, а підсумковий job
`gate` (який залежить від `bandit` і `semgrep` через `needs`) перевіряє
`needs.bandit.result` / `needs.semgrep.result` і теж падає — весь workflow
стає червоним, і pull request не можна змержити, доки не поправлять
критичні знахідки. Low/medium знахідки й далі просто лягають у звіт, не
блокуючи роботу.

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

Більшість цих знахідок мають HIGH severity в Bandit — саме тому вони і
блокують pipeline через quality gate, а не просто лягають у звіт.

## Вразливі залежності в `requirements.txt`

Пакети навмисно зафіксовані на старих версіях, щоб `safety` і `pip-audit`
знайшли реальні опубліковані CVE:

- **Flask 0.12.2** — множинні відомі проблеми, застаріла гілка без патчів
- **Jinja2 2.10.1** — вразливість sandbox escape (CVE-2019-10906) та інші
- **Werkzeug 0.15.4** — DoS та проблеми з debugger console
- **urllib3 1.24.1** — CVE-2019-11324 (некоректна перевірка сертифікатів)
- **requests 2.19.1** — витік заголовка `Authorization` при редиректах на інший хост
- **PyYAML 5.3** — небезпечний `yaml.load` без `SafeLoader` (CVE-2020-1747, CVE-2020-14343)

`safety` бере дані з бази PyUp, `pip-audit` — з бази OSV (Google). Бази
частково не перетинаються, тому запуск обох — це не дублювання, а реальна
крос-перевірка: пакет, пропущений однією базою, може знайтись у другій.

## Як це працює в pipeline на практиці

1. Розробник робить `push` або відкриває `pull request` у `main`.
2. GitHub Actions паралельно запускає всі п'ять сканувальних job'ів.
3. Bandit і Semgrep публікують SARIF-звіти → вони з'являються як анотації
   прямо в diff pull request'а та у вкладці Security.
4. Safety і pip-audit виводять у логи job'ів списки CVE з посиланнями;
   pip-audit додатково зберігає JSON-артефакт.
5. Якщо Bandit знайшов HIGH severity або Semgrep — ERROR severity,
   відповідний job падає, а разом з ним падає й підсумковий `gate` —
   pull request отримує червону перевірку і його не можна змержити без
   виправлення критичних знахідок.

## Реалізовано (було в roadmap)

- **Quality gate замість суцільного `continue-on-error`** — тепер
  HIGH/ERROR severity блокують pipeline, а low/medium лише потрапляють у
  звіт.
- **Другий незалежний dependency-сканер** — додано `pip-audit` (база
  OSV) поруч із Safety (база PyUp) для крос-перевірки.

