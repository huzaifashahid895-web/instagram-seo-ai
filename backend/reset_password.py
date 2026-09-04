#!/usr/bin/env python3
# Password reset utility for single-operator mode
# Cost classification: FREE + OPEN SOURCE

import sys
from pathlib import Path
from getpass import getpass

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password

def reset_password():
    """Interactive password reset for the single user"""
    engine = create_engine('sqlite:///aism.db')
    session = Session(engine)
    
    try:
        # Get the single user
        user = session.execute(select(User)).scalar_one_or_none()
        
        if not user:
            print("\n❌ No user found in database.")
            print("   Register a new account at http://localhost:8000/docs\n")
            return
        
        print(f"\n✓ Found user: {user.email} ({user.full_name})")
        print(f"  Created: {user.created_at}\n")
        
        # Get new password
        while True:
            new_password = getpass("Enter new password: ")
            if len(new_password) < 6:
                print("❌ Password must be at least 6 characters. Try again.\n")
                continue
            
            confirm_password = getpass("Confirm new password: ")
            if new_password != confirm_password:
                print("❌ Passwords don't match. Try again.\n")
                continue
            
            break
        
        # Update password
        user.hashed_password = hash_password(new_password)
        session.commit()
        
        print(f"\n✅ Password updated successfully for {user.email}")
        print(f"   You can now log in with this new password.\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Password Reset Utility")
    print("="*50)
    reset_password()
