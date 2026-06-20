# ☕ MachaDB — The Filter Coffee Database

Welcome to **MachaDB**, the database engine built by Bengaluru engineering students running entirely on filter coffee, Darshini dosas, and pure assignment panic. 

SQL is for corporate weaklings. We use **Bangalore Slang**.

If your startup needs a database that acts like your sleep-deprived friend debugging production at 3 AM, you're in the right place, boss.

---

## 🚀 How to Start (Quick Setup Macha)

Don't panic. Setting this up is easier than finding an auto-rickshaw in Koramangala when it's raining.

1. **Clone/Download the Code**
   Make sure all the `.py` files in the `machadb` folder are sitting safely in your directory.
   
2. **Open the Godaamu (Terminal)**
   No external libraries needed. Pure Python 3. Just run the REPL:
   ```bash
   python -m machadb.repl
   ```
   Or if you want to write a Python script:
   ```python
   from machadb import MachaDB
   
   db = MachaDB("./machadb_data")
   db.execute("huttu jana (id sankhye, hesar pathya)")
   ```

3. **Start Typing Commands**
   You're now in the `pydb>` shell. Type `sahaaya` if you're feeling lost.

---

## 📖 The Sacred Queries (Command Guide)

Forget everything you know about `SELECT`, `INSERT`, or `DROP`. Here is the true vocabulary.

### Data Types
* `sankhye` = INTEGER
* `pathya` = TEXT
* `dashaamsha` = FLOAT
* `haan_illa` = BOOLEAN (use `haan` / `illa` or `true` / `false`)

### 1. CREATE TABLE (`huttu`)
When you want to birth a new table:
```sql
huttu jana (
    id sankhye,
    hesar pathya,
    active haan_illa
)
```

### 2. INSERT (`haaku`)
When you want to dump data inside:
```sql
haaku jana (1, 'Dheer', haan)
haaku jana (2, 'Boss', illa)
```

### 3. SELECT (`torsu`)
When you want the database to show you what's inside. You can filter using `elli` (WHERE).
```sql
-- Show everything
torsu * jana

-- Show specific columns with a condition
torsu id, hesar jana elli active = haan
```

### 4. UPDATE (`change_madu`)
When you made a mistake and need to fix it before the manager sees:
```sql
change_madu jana set hesar = 'Big Boss' elli id = 2
```

### 5. DELETE (`en_kilthya`)
When you need to completely erase someone from existence:
```sql
en_kilthya jana elli id = 2
```

### 6. DROP TABLE (`sutaku`)
Burn the table to the ground:
```sql
sutaku jana
```

### 7. TRANSACTIONS
Because sometimes you need to back out of a bad decision:
```sql
pakka  -- COMMIT: Save everything immediately
beda   -- ROLLBACK: Undo everything (currently throws away dirty memory)
```

### 8. SYSTEM STATUS
When you need to check the mood of the database:
```sql
yenide        -- SHOW TABLES: What's in the godaamu?
scene_enu     -- STATUS: Basic health check
full_scene    -- DEBUG: Get the full panic report
sahaaya       -- HELP: Command list
hogthini      -- EXIT: Close the terminal and go sleep
```

---

## 🌍 How to Deploy (Going to Production)

You want to deploy this? Nkn, you are brave boss. Here is how you push this to "Production":

### 1. Folder Setup
MachaDB stores everything locally in files (Pager, Buffer Pool, Catalog). So wherever you run your Python script, MachaDB will create its `.tbl` and `.json` files. 

```python
# Pass an absolute path for production so you don't lose data macha!
db = MachaDB("/var/data/machadb_prod")
```

### 2. The Cloud Server (EC2 / VPS)
1. Get a cheap Ubuntu server.
2. Install Python 3.10+.
3. Put the `machadb` folder there.
4. If you're building an API, wrap MachaDB with **FastAPI** or **Flask**.

*Example FastAPI wrapper:*
```python
from fastapi import FastAPI
from machadb import MachaDB

app = FastAPI()
db = MachaDB("/app/data")

@app.get("/users")
def get_users():
    return db.execute("torsu * jana")
```

### 3. Running it
Use `uvicorn` or `gunicorn` with `systemd` to keep it running.
> **Warning Boss:** MachaDB doesn't have concurrency locks yet. Run your web server with **only 1 worker** (`--workers 1`), or your files will get corrupted faster than Silk Board traffic!

### 4. Backups
Because we persist to `.tbl` files and a `jamakhaana.json` catalog, "taking a backup" just means copying the folder. Write a cron job to zip the folder every night.
```bash
0 3 * * * tar -czvf /backups/machadb_$(date +\%F).tar.gz /var/data/machadb_prod
```

---

Made with ❤️ and filter coffee. If it breaks, raise an issue, but don't expect a reply until after our exams.
