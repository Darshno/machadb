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


### Snapshots:
<img width="679" height="414" alt="image" src="https://github.com/user-attachments/assets/884d78ba-f756-4672-bb2e-a3ba7de34009" />
<img width="948" height="411" alt="image" src="https://github.com/user-attachments/assets/c1352c65-c226-49fd-96c7-c06e48644992" />
<img width="214" height="47" alt="image" src="https://github.com/user-attachments/assets/f88c3320-f49e-45ab-a329-c88acbf594af" />


Made with ❤️ and filter coffee. If it breaks, raise an issue, but don't expect a reply until after our exams.
