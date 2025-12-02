import sqlite3
from datetime import datetime

class DatabaseSetup:
    """SQLite DB setup and sample data for customer support system."""

    def __init__(self, db_path: str = "support.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        print(f"Connected to database at {self.db_path}")

    def create_tables(self):
        # Customers table with tier and billing_info
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'disabled')),
                tier TEXT NOT NULL DEFAULT 'standard' CHECK(tier IN ('standard','premium','enterprise')),
                billing_info TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tickets table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                issue TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','in_progress','resolved')),
                priority TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low','medium','high')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            )
        """)

        # Indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_tier ON customers(tier)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON tickets(customer_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")

        self.conn.commit()
        print("Tables created successfully.")

    def create_triggers(self):
        # Trigger for updating updated_at
        self.cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_update_customer
            AFTER UPDATE ON customers
            FOR EACH ROW
            BEGIN
                UPDATE customers SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        self.conn.commit()
        print("Triggers created successfully.")

    def insert_sample_data(self):
        """Insert diverse sample customers and tickets."""
        customers = [
            ("Ashwin Ram", "ashwinram232@gmail.com", "7738863498", "active", "premium", "Visa ****1234"),
            ("Nina Patel", "nina.patel@domain.com", "7735550101", "active", "standard", "Mastercard ****5678"),
            ("Liam Johnson", "liam.johnson@example.org", "7735550102", "disabled", "enterprise", None),
            ("Olivia Smith", "olivia.smith@company.com", "7735550103", "active", "premium", "Visa ****9876"),
            ("Ethan Brown", "ethan.brown@workplace.net", "7735550104", "active", "standard", "Amex ****4321"),
            ("Sophia Davis", "sophia.davis@tech.io", "7735550105", "active", "standard", None),
            ("Mason Wilson", "mason.wilson@enterprise.com", "7735550106", "active", "enterprise", "Mastercard ****2468"),
            ("Ava Martinez", "ava.martinez@startup.org", "7735550107", "disabled", "premium", None),
            ("Logan Garcia", "logan.garcia@solutions.com", "7735550108", "active", "standard", "Visa ****1357"),
            ("Isabella Lee", "isabella.lee@global.com", "7735550109", "active", "enterprise", None),
        ]

        self.cursor.executemany("""
            INSERT INTO customers (name,email,phone,status,tier,billing_info)
            VALUES (?,?,?,?,?,?)
        """, customers)

        # Only use customer_id 1-10
        tickets = [
            (1, "Cannot login to system", "open", "high"),
            (4, "Payment processing failed", "in_progress", "high"),
            (7, "Security breach reported", "open", "high"),
            (10, "Critical bug in dashboard", "in_progress", "high"),
            (5, "Data export not working", "resolved", "high"),
            (1, "Password reset not working", "in_progress", "medium"),
            (2, "Profile photo not uploading", "resolved", "medium"),
            (3, "Email notifications failing", "open", "medium"),
            (5, "Dashboard slow loading", "in_progress", "medium"),
            (6, "Report generation error", "open", "medium"),
            (8, "Search returning wrong results", "resolved", "medium"),
            (9, "Feature request: dark mode", "in_progress", "medium"),
            (10, "Mobile app crash on startup", "open", "medium"),
            (4, "API rate limiting too strict", "resolved", "medium"),
            (5, "Unable to access beta feature", "open", "medium"),
            (2, "Billing question", "resolved", "low"),
            (2, "Request additional language support", "open", "low"),
        ]

        self.cursor.executemany("""
            INSERT INTO tickets (customer_id, issue, status, priority)
            VALUES (?,?,?,?)
        """, tickets)

        self.conn.commit()
        print(f"{len(customers)} customers and {len(tickets)} tickets inserted.")

    def close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")


def main():
    db = DatabaseSetup("support.db")
    db.connect()
    db.create_tables()
    db.create_triggers()

    add_data = input("Insert sample data? (y/n): ").lower()
    if add_data == 'y':
        db.insert_sample_data()

    db.close()


if __name__ == "__main__":
    main()