import gzip
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.mysql import get_conn


BACKUP_DIR = Path("/www/backups/football")
RETENTION_DAYS = 14


def dump_database():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = BACKUP_DIR / f"football_data_{timestamp}.sql.gz"

    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES")
        tables = [next(iter(row.values())) for row in cursor.fetchall()]

        with gzip.open(output, "wt", encoding="utf-8") as backup_file:
            backup_file.write("SET FOREIGN_KEY_CHECKS=0;\n")
            for table in tables:
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_row = cursor.fetchone()
                create_sql = next(
                    value
                    for key, value in create_row.items()
                    if key.lower().startswith("create ")
                )
                backup_file.write(
                    f"\nDROP TABLE IF EXISTS `{table}`;\n{create_sql};\n"
                )

                cursor.execute(f"SELECT * FROM `{table}`")
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                if not rows:
                    continue

                column_sql = ",".join(f"`{column}`" for column in columns)
                batch = []
                for row in rows:
                    values = ",".join(
                        conn.literal(row[column])
                        for column in columns
                    )
                    batch.append("(" + values + ")")
                    if len(batch) >= 200:
                        backup_file.write(
                            f"INSERT INTO `{table}` ({column_sql}) VALUES\n"
                            + ",\n".join(batch)
                            + ";\n"
                        )
                        batch = []
                if batch:
                    backup_file.write(
                        f"INSERT INTO `{table}` ({column_sql}) VALUES\n"
                        + ",\n".join(batch)
                        + ";\n"
                    )
            backup_file.write("\nSET FOREIGN_KEY_CHECKS=1;\n")
    finally:
        cursor.close()
        conn.close()

    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    for file in BACKUP_DIR.glob("football_data_*.sql.gz"):
        if datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            file.unlink(missing_ok=True)

    print("鏁版嵁搴撳浠藉畬鎴?", output)


if __name__ == "__main__":
    dump_database()
