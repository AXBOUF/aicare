#!/usr/bin/env python3
"""
User management CLI for Zenith Healthcare AI Platform.
Create, list, and delete users in the MySQL database.

Usage:
  python scripts/manage_users.py create <username> <password> [--role=admin]
  python scripts/manage_users.py list
  python scripts/manage_users.py delete <username>
"""

import sys
import os
from pathlib import Path
from getpass import getpass

# Add parent dir to path so we can import the app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from werkzeug.security import generate_password_hash
from services.database import DatabaseService

db = DatabaseService()


def create_user(username: str, password: str = None, role: str = "user"):
    """Create a new user."""
    try:
        # Check if user exists
        existing = db.get_user_by_username(username)
        if existing:
            print(f"❌ User '{username}' already exists.")
            return False
        
        # Prompt for password if not provided
        if not password:
            while True:
                password = getpass(f"Enter password for {username}: ")
                confirm = getpass("Confirm password: ")
                if password != confirm:
                    print("❌ Passwords do not match. Try again.")
                    continue
                break
        
        # Hash and create
        pw_hash = generate_password_hash(password)
        user_id = db.create_user(username, pw_hash, role=role)
        print(f"✅ Created user '{username}' (ID: {user_id}) with role '{role}'")
        return True
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False


def list_users():
    """List all users."""
    try:
        conn = db._get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not users:
            print("No users found.")
            return
        
        print(f"\n{'ID':<5} {'Username':<20} {'Role':<15} {'Created':<20}")
        print("=" * 60)
        for u in users:
            print(f"{u['id']:<5} {u['username']:<20} {u['role']:<15} {str(u['created_at']):<20}")
        print()
    except Exception as e:
        print(f"❌ Error listing users: {e}")


def delete_user(username: str):
    """Delete a user."""
    try:
        user = db.get_user_by_username(username)
        if not user:
            print(f"❌ User '{username}' not found.")
            return False
        
        confirm = input(f"Delete user '{username}'? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Cancelled.")
            return False
        
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Deleted user '{username}'")
        return True
    except Exception as e:
        print(f"❌ Error deleting user: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "create":
        if len(sys.argv) < 4:
            print("Usage: python scripts/manage_users.py create <username> <password> [--role=admin]")
            sys.exit(1)
        username = sys.argv[2]
        password = sys.argv[3] if sys.argv[3] != "--role=admin" else None
        role = "admin" if len(sys.argv) > 4 and sys.argv[4].startswith("--role=") else "user"
        if sys.argv[3].startswith("--role="):
            role = sys.argv[3].split("=")[1]
            password = None
        create_user(username, password, role=role)
    
    elif command == "list":
        list_users()
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python scripts/manage_users.py delete <username>")
            sys.exit(1)
        username = sys.argv[2]
        delete_user(username)
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
