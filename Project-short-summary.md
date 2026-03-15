# Multi-Repo Browser

**ריפו:** [amirbiron/repo-browser](https://github.com/amirbiron/repo-browser)
**סטטוס:** פעיל

דפדפן קוד מרובה-ריפוזיטוריז עם חיפוש גלובלי, היסטוריית commits, diff, וסינטקס הדגשה ל-100+ שפות.

## פיצ'רים מרכזיים
- ניהול ודפדוף ריפוזיטוריז מרובים בממשק אחד
- חיפוש גלובלי cross-repo (git grep) לפי תוכן, שם קובץ, פונקציות ומחלקות
- צפייה בהיסטוריית commits ו-diff בין גרסאות
- סינטקס הדגשה ל-100+ שפות (CodeMirror)
- סנכרון אוטומטי של Git bare mirrors
- API RESTful מלא עם תמיכה RTL

## Tech Stack
Python 3.11+, Flask, MongoDB, Git (bare mirrors), Gunicorn, CodeMirror, Docker, Jinja2

## לינקים
- Live / Demo: <!-- TODO: בדוק ידנית -->
- Docs: README + QUICKSTART.md בריפו

## מה עשיתי
פיתוח מלא – ארכיטקטורה תלת-שכבתית, שירותי Git mirror, מנוע חיפוש cross-repo, אינדוקס MongoDB, ממשק Web, ו-deployment (Docker + Render).
