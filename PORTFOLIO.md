---
# Portfolio – Multi-Repo Browser

name: "Multi-Repo Browser"
repo: "https://github.com/amirbiron/repo-browser"
status: "פעיל"

one_liner: "דפדפן קוד מרובה-ריפוזיטוריז עם חיפוש גלובלי, היסטוריה, diff וסינטקס הדגשה"

stack:
  - Python 3.11+
  - Flask 2.3+
  - MongoDB (Atlas/local)
  - Gunicorn
  - Git (bare mirrors)
  - CodeMirror (syntax highlighting)
  - Bootstrap Icons
  - Docker + Docker Compose
  - Jinja2

key_features:
  - ניהול ריפוזיטוריז מרובים בממשק אחד
  - דפדוף עץ קבצים אינטראקטיבי עם סינטקס הדגשה (100+ שפות)
  - חיפוש גלובלי בכל הריפוזיטוריז (git grep)
  - חיפוש לפי שם קובץ, תוכן, פונקציות ומחלקות
  - צפייה בהיסטוריית commits ו-diff
  - סנכרון mirror אוטומטי
  - API RESTful מלא
  - תמיכה RTL (עברית)

architecture:
  summary: |
    ארכיטקטורה תלת-שכבתית:
    - Presentation: Flask routes + Jinja2 templates + JavaScript
    - Business Logic: שירותים (git operations, search, repo management)
    - Data: MongoDB עם אינדקסים + Git bare mirrors
  entry_points:
    - app.py – Flask application factory
    - routes/repo_browser.py – API דפדוף קבצים וחיפוש
    - routes/repo_selector.py – API ניהול ריפוזיטוריז
    - services/git_mirror_service.py – פעולות Git

demo:
  live_url: "" # TODO: בדוק ידנית (deployed on Render)
  video_url: "" # TODO: בדוק ידנית

setup:
  quickstart: |
    1. git clone <repo-url> && cd repo-browser
    2. docker-compose up --build
    3. פתח http://localhost:5000
    # או:
    1. pip install -r requirements.txt
    2. cp .env.example .env && # הגדר MONGODB_URI
    3. python app.py

your_role: "פיתוח מלא – ארכיטקטורה, שירותי Git, חיפוש cross-repo, ממשק Web, deployment"

tradeoffs:
  - Git bare mirrors צורכים מקום דיסק אך מאפשרים חיפוש מהיר (git grep)
  - MongoDB לאינדוקס קבצים – גמישות גבוהה אך תלות נוספת
  - CodeMirror בצד הלקוח – עשיר אך מגדיל את גודל ה-bundle

metrics: "" # TODO: בדוק ידנית

faq:
  - q: "אפשר להוסיף ריפוזיטוריז פרטיים?"
    a: "כן – צריך להגדיר GITHUB_TOKEN במשתני הסביבה."
  - q: "כמה ריפוזיטוריז אפשר לנהל?"
    a: "אין מגבלה תוכנתית, רק מגבלת דיסק (bare mirrors) ו-MongoDB."
---
