# Contributing to AutoBloggerApp

Welcome, Agent. Here's how to sync in fast, clean, and error-free.

---

## 🛠️ Setup

1. **Clone + install**
   ```bash
   git clone https://github.com/yourname/autobloggerapp.git
   cd autobloggerapp
   pip install -r requirements.txt
   ```

2. **Copy environment template**
   ```bash
   cp .env.example .env
   # Then edit .env with your secrets
   ```

3. **Install pre-commit hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

---

## 📏 Code Standards

* **Python ≥ 3.9**
* **Black**: for formatting
* **Flake8**: for linting
* **isort**: for import sorting

All of this runs automatically on `git commit`. Stay green.

---

## ✅ Git Rules

* Branch from `develop`, not `main`
* PRs must pass all tests and hooks
* Use conventional commit messages:
  * `feat: add LinkedIn parser`
  * `fix: resolve scraper crash`
  * `chore: cleanup .env.example`

---

## 🧪 Testing

Run the full suite:
```bash
pytest tests/ -v
```

---

## 🧠 Notes

* Never commit `.env`
* Keep files < 300 lines when possible
* Use atomic file writes for all I/O
* Log like your future self will need it

---

Let's build something legendary. 