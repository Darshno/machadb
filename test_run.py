import os
from machadb import MachaDB
from machadb.repl import print_table

print("Starting MachaDB Phase 5 Test...")

# Delete old db for a clean run
import shutil
if os.path.exists("./test_db"):
    shutil.rmtree("./test_db")

db = MachaDB("./test_db")

print("\n--- Setup ---")
print(db.execute("huttu jana (id sankhye, hesar pathya, active haan_illa)"))

print("\n--- Creating Shortcut (Index) ---")
print(db.execute("huttu_shortcut id mele jana"))

print("\n--- Insert ---")
print(db.execute("haaku jana (1, 'Dheer', haan)"))
print(db.execute("haaku jana (2, 'Boss', illa)"))
print(db.execute("haaku jana (3, 'Macha', haan)"))

print("\n--- Indexed Select (Should use B-Tree) ---")
results = db.execute("torsu * jana elli id = 2")
print_table(results)

print("\n--- Update Indexed Value ---")
print(db.execute("change_madu jana set id = 20 elli id = 2"))

print("\n--- Indexed Select on New Value ---")
results = db.execute("torsu * jana elli id = 20")
print_table(results)

print("\n--- Indexed Select on Old Value (Should be empty) ---")
results = db.execute("torsu * jana elli id = 2")
print_table(results)

print("\n--- Status ---")
print(db.execute("scene_enu"))

db.close()
print("\nDone, macha.")
