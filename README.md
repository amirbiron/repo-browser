# 🔍 Multi-Repo Browser

דפדפן קוד מתקדם לניהול מספר repositories מ-GitHub עם חיפוש גלובלי, היסטוריה ו-diff.

## ✨ תכונות

- **ניהול ריפוים מרובים** - הוספה, הסרה וסנכרון של repositories
- **דפדפון קבצים** - עץ קבצים אינטראקטיבי עם צפייה בקוד
- **חיפוש מתקדם** - חיפוש גלובלי בכל הריפוים או בריפו ספציפי
- **היסטוריה ו-Diff** - צפייה בהיסטוריית commits והשוואות
- **Syntax Highlighting** - תמיכה ב-100+ שפות תכנות
- **Git Mirror** - יעילות מקסימלית עם bare mirrors

## 🚀 Deployment ב-Render

### דרישות

1. חשבון ב-[Render](https://render.com)
2. חשבון ב-MongoDB Atlas (או MongoDB אחר)
3. GitHub token (אופציונלי - לריפוים פרטיים)

### שלבי ההתקנה

#### 1. הכנת MongoDB

1. צור חשבון ב-[MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. צור Cluster חדש (free tier מספיק להתחלה)
3. בחר Database Access → Add New Database User
4. בחר Network Access → Add IP Address → Allow Access from Anywhere (0.0.0.0/0)
5. העתק את ה-Connection String

#### 2. Deploy ל-Render

**אופציה א: דרך Dashboard**

1. לחץ על New → Web Service
2. חבר את ה-repository שלך
3. הגדרות:
   - **Name**: multi-repo-browser
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

4. Environment Variables:
   ```
   MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/multi_repo_browser
   # אם ה-URI לא כולל שם DB:
   # MONGODB_DB_NAME=multi_repo_browser
   FLASK_SECRET_KEY=<generate-random-string>
   REPO_MIRROR_PATH=/opt/render/project/src/repos
   GITHUB_TOKEN=<optional-for-private-repos>
   ```

5. Disk (חשוב!):
   - לחץ על Add Disk
   - Name: repo-storage
   - Mount Path: `/opt/render/project/src/repos`
   - Size: 10GB (או יותר לפי הצורך)

6. לחץ Create Web Service

**אופציה ב: עם render.yaml (מומלץ)**

1. הקובץ `render.yaml` כבר מוכן בפרויקט
2. צור New → Blueprint
3. חבר את ה-repository
4. Render יזהה את render.yaml אוטומטית
5. הגדר את MONGODB_URI ב-Environment Variables (או MONGODB_DB_NAME אם אין DB ב-URI)

#### 3. בדיקה

1. פתח את ה-URL שקיבלת מ-Render
2. לחץ "הוסף ריפו"
3. הזן URL של repository ציבורי (למשל: `https://github.com/torvalds/linux`)
4. המתן לסנכרון
5. דפדף בקוד!

## 🛠️ הרצה מקומית (Development)

### דרישות

- Python 3.11+
- MongoDB (מקומי או Atlas)
- Git

### התקנה

```bash
# 1. Clone הפרויקט
git clone <your-repo-url>
cd multi-repo-browser

# 2. צור virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# או
venv\Scripts\activate  # Windows

# 3. התקן dependencies
pip install -r requirements.txt

# 4. העתק את .env.example
cp .env.example .env

# 5. ערוך את .env
# הגדר את MONGODB_URI לשרת MongoDB שלך
nano .env

# 6. צור תיקיית repos
mkdir -p /var/data/repos
# או שנה את REPO_MIRROR_PATH ב-.env לתיקייה אחרת

# 7. הרץ את האפליקציה
flask run --debug
```

האפליקציה תהיה זמינה ב-http://localhost:5000

## 📁 מבנה הפרויקט

```
multi-repo-browser/
├── app.py                  # Flask application entry point
├── config.py               # Configuration
├── requirements.txt        # Python dependencies
├── Procfile               # Render deployment
├── render.yaml            # Render blueprint
│
├── services/              # Business logic
│   ├── git_mirror_service.py      # Git operations
│   ├── repo_manager.py            # Multi-repo management
│   ├── repo_search_service.py     # Search in single repo
│   └── cross_repo_search.py       # Search across repos
│
├── routes/                # API endpoints
│   ├── repo_browser.py            # Browser API
│   └── repo_selector.py           # Repo management API
│
├── database/              # MongoDB
│   └── db_manager.py              # DB connection & indexes
│
├── templates/             # HTML templates
│   └── repo/
│       ├── base_repo.html
│       └── index.html
│
└── static/                # Frontend assets
    ├── css/
    │   └── repo-browser.css
    └── js/
        └── repo-browser.js
```

## 🔧 API Endpoints

### Repo Management
- `GET /repos/` - רשימת ריפוים
- `POST /repos/` - הוספת ריפו
- `DELETE /repos/<name>` - מחיקת ריפו
- `POST /repos/<name>/sync` - סנכרון ריפו
- `POST /repos/sync-all` - סנכרון כל הריפוים

### Browser
- `GET /repo/api/tree` - עץ קבצים
- `GET /repo/api/file/<repo>/<path>` - תוכן קובץ
- `GET /repo/api/search` - חיפוש
- `GET /repo/api/history` - היסטוריית קובץ
- `GET /repo/api/diff/<repo>/<commit1>/<commit2>` - Diff

## 🔐 אבטחה

- Path traversal protection
- Input validation
- Safe Git operations
- XSS prevention

## 📊 מסד נתונים

### Collections

**repos**
```json
{
  "name": "owner_repo",
  "url": "https://github.com/owner/repo",
  "default_branch": "main",
  "last_sync": ISODate("..."),
  "sync_status": "synced"
}
```

**repo_files**
```json
{
  "repo_name": "owner_repo",
  "path": "src/main.py",
  "language": "python",
  "size": 1234,
  "lines": 50
}
```

## 🚨 Troubleshooting

### בעיות נפוצות

**MongoDB connection failed**
- בדוק את MONGODB_URI
- וודא שה-IP מאושר ב-MongoDB Atlas
**No default database name defined**
- הוסף שם DB ל-MONGODB_URI או הגדר MONGODB_DB_NAME

**Git clone timeout**
- ריפוים גדולים לוקחים זמן
- הגדל את הזמן ב-config.py (GIT_CLONE_TIMEOUT)

**Disk full**
- הגדל את גודל ה-Disk ב-Render
- מחק ריפוים ישנים

## 📝 רישיון

MIT License - ראה LICENSE לפרטים

## 🤝 תרומה

Pull requests מתקבלים בברכה!

## 📞 תמיכה

פתח issue ב-GitHub לשאלות ובעיות.

---

**Built with ❤️ using Flask, MongoDB & Git**
