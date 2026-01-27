# 🚀 התחלה מהירה - Multi-Repo Browser

## Deployment ל-Render (5 דקות)

### 1. הכן MongoDB Atlas

1. לך ל-[MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. צור חשבון חינמי
3. Create Cluster → M0 (FREE)
4. לאחר יצירת ה-Cluster:
   - Database Access → Add User (שמור username + password)
   - Network Access → Add IP → 0.0.0.0/0
   - Connect → Drivers → Copy Connection String

### 2. Deploy ל-Render

1. לך ל-[Render](https://render.com) וצור חשבון
2. New → Web Service
3. Connect to GitHub (או העלה את הקבצים)
4. הגדרות:
   ```
   Name: my-repo-browser
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn app:app --bind 0.0.0.0:$PORT
   ```

5. **Environment Variables** (חשוב!):
   ```
   MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/repos
   # אם ה-URI בלי שם DB:
   # MONGODB_DB_NAME=repos
   FLASK_SECRET_KEY=your-secret-key-here-change-this
   REPO_MIRROR_PATH=/opt/render/project/src/repos
   ```

6. **Add Disk** (קריטי!):
   ```
   Name: repo-storage
   Mount Path: /opt/render/project/src/repos
   Size: 10GB
   ```

7. לחץ **Create Web Service**

### 3. המתן לפריסה

- Render יתחיל לבנות את האפליקציה
- זה לוקח 2-3 דקות
- כשמוכן, תקבל URL כמו: `https://my-repo-browser.onrender.com`

### 4. השתמש!

1. פתח את ה-URL
2. לחץ "הוסף ריפו"
3. הזן: `https://github.com/torvalds/linux`
4. המתן לסנכרון (זה יכול לקחת כמה דקות לריפו גדול)
5. דפדף בקוד!

---

## הרצה מקומית עם Docker (2 דקות)

```bash
# 1. Clone הפרויקט
git clone <your-repo>
cd multi-repo-browser

# 2. הרץ עם Docker Compose
docker-compose up

# 3. פתח בדפדפן
http://localhost:5000
```

זהו! MongoDB ירוץ אוטומטית ב-container.

---

## הרצה מקומית ללא Docker

```bash
# 1. Setup
./scripts/setup.sh

# 2. ערוך .env
nano .env
# הגדר MONGODB_URI (או MONGODB_DB_NAME אם אין DB ב-URI)

# 3. הפעל
source venv/bin/activate
flask run --debug

# 4. פתח בדפדפן
http://localhost:5000
```

---

## 🎉 זהו!

האפליקציה מוכנה לשימוש.

### טיפים:

- **ריפוים גדולים** (כמו Linux kernel) לוקחים זמן לסנכרון ראשוני
- **ריפוים קטנים** מסתכנים תוך שניות
- השתמש ב-**Ctrl+K** לחיפוש מהיר
- לחץ על **סנכרן הכל** לעדכון כל הריפוים

### בעיות?

1. **MongoDB connection error** - בדוק את ה-Connection String
2. **Git clone timeout** - ריפוים גדולים לוקחים זמן, התאזר בסבלנות
3. **Disk full** - הגדל את ה-Disk ב-Render

---

**יש שאלות? פתח issue ב-GitHub!**
