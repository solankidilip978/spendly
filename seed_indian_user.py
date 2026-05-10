import random
from datetime import datetime

from werkzeug.security import generate_password_hash

from database.db import get_db


FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Karan", "Rahul", "Siddharth",
    "Ishaan", "Kabir", "Reyansh", "Aryan", "Dhruv", "Pranav", "Vikram", "Aniket",
    "Saurabh", "Manish", "Nikhil", "Tanmay", "Harsh", "Yash", "Ritesh", "Aakash",
    "Ananya", "Diya", "Priya", "Neha", "Pooja", "Riya", "Kavya", "Sneha",
    "Ishita", "Aditi", "Meera", "Shreya", "Tanvi", "Nisha", "Anjali", "Divya",
    "Pallavi", "Swati", "Rashmi", "Lakshmi", "Sanya", "Ritika",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Agarwal", "Mehta", "Patel", "Shah", "Jain",
    "Kumar", "Singh", "Yadav", "Mishra", "Pandey", "Tiwari", "Chauhan", "Rao",
    "Reddy", "Naidu", "Iyer", "Nair", "Menon", "Pillai", "Krishnan", "Subramanian",
    "Banerjee", "Chatterjee", "Mukherjee", "Bose", "Das", "Ghosh", "Sen",
    "Solanki", "Joshi", "Desai", "Trivedi", "Bhatt", "Khanna", "Kapoor", "Malhotra",
]

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]


def generate_user():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    suffix = random.randint(10, 999)
    domain = random.choice(EMAIL_DOMAINS)
    email = f"{first.lower()}.{last.lower()}{suffix}@{domain}"
    return name, email


def main():
    conn = get_db()
    try:
        while True:
            name, email = generate_user()
            row = conn.execute(
                "SELECT 1 FROM users WHERE email = ?", (email,)
            ).fetchone()
            if row is None:
                break

        password_hash = generate_password_hash("password123")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (name, email, password_hash, created_at),
        )
        conn.commit()
        new_id = cursor.lastrowid

        print(f"id:    {new_id}")
        print(f"name:  {name}")
        print(f"email: {email}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
