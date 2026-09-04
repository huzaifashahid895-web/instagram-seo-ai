#!/usr/bin/env python3
# Quick script to check existing user in database

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.db import Base

# Connect to database
engine = create_engine('sqlite:///aism.db')
session = Session(engine)

# Query users
users = session.execute(select(User)).scalars().all()

print(f"\nFound {len(users)} user(s) in database:\n")
for user in users:
    print(f"  Email: {user.email}")
    print(f"  Name: {user.full_name}")
    print(f"  Active: {user.is_active}")
    print(f"  Created: {user.created_at}")
    print()

session.close()
