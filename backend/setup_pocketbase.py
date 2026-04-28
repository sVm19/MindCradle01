"""
PocketBase Setup Script
========================
Run this ONCE to create all collections and seed the 24 resource cards.

Usage:
    python setup_pocketbase.py --email YOUR_ADMIN_EMAIL --password YOUR_ADMIN_PASSWORD

Requires: httpx (already installed)
"""

import httpx
import argparse
import json
import sys

PB_URL = "http://127.0.0.1:8090"


def admin_login(email: str, password: str) -> str:
    """Authenticate as PocketBase admin and return the token."""
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": email, "password": password},
    )
    if resp.status_code != 200:
        # Try the newer PocketBase auth endpoint format
        resp = httpx.post(
            f"{PB_URL}/api/collections/_superusers/auth-with-password",
            json={"identity": email, "password": password},
        )
    if resp.status_code != 200:
        print(f"❌ Admin login failed: {resp.text}")
        sys.exit(1)
    token = resp.json()["token"]
    print(f"✅ Logged in as admin")
    return token


def collection_exists(token: str, name: str) -> bool:
    """Check if a collection already exists."""
    resp = httpx.get(
        f"{PB_URL}/api/collections/{name}",
        headers={"Authorization": token},
    )
    return resp.status_code == 200


def create_collection(token: str, schema: dict) -> None:
    """Create a collection from a schema dict."""
    name = schema["name"]
    if collection_exists(token, name):
        print(f"  ⏩ Collection '{name}' already exists, skipping")
        return

    resp = httpx.post(
        f"{PB_URL}/api/collections",
        headers={"Authorization": token, "Content-Type": "application/json"},
        json=schema,
    )
    if resp.status_code == 200:
        print(f"  ✅ Created collection '{name}'")
    else:
        print(f"  ❌ Failed to create '{name}': {resp.text}")


# ============================================================
# Collection Schemas
# ============================================================

RESOURCES_SCHEMA = {
    "name": "resources",
    "type": "base",
    "schema": [
        {"name": "title",       "type": "text",   "required": True},
        {"name": "description", "type": "text",   "required": True},
        {"name": "icon",        "type": "text",   "required": True},
        {"name": "color_class", "type": "text",   "required": True},
        {"name": "category",    "type": "select", "required": True,
         "options": {"values": ["crisis","mindfulness","therapy","self-care","physical","creative","tools"]}},
        {"name": "order",       "type": "number", "required": True},
        {"name": "url",         "type": "url",    "required": False},
        {"name": "is_active",   "type": "bool",   "required": False},
    ],
    "listRule": "",       # Public read
    "viewRule": "",       # Public read
    "createRule": None,   # Admin only
    "updateRule": None,   # Admin only
    "deleteRule": None,   # Admin only
}

MOOD_LOGS_SCHEMA = {
    "name": "mood_logs",
    "type": "base",
    "schema": [
        {"name": "user",     "type": "relation", "required": True,
         "options": {"collectionId": "_pb_users_auth_", "maxSelect": 1}},
        {"name": "level",    "type": "number",   "required": True,
         "options": {"min": 1, "max": 10}},
        {"name": "emotions", "type": "json",     "required": False},
        {"name": "note",     "type": "text",     "required": False},
    ],
    "listRule": "user = @request.auth.id",
    "viewRule": "user = @request.auth.id",
    "createRule": "@request.auth.id != ''",
    "updateRule": "user = @request.auth.id",
    "deleteRule": "user = @request.auth.id",
}

JOURNAL_ENTRIES_SCHEMA = {
    "name": "journal_entries",
    "type": "base",
    "schema": [
        {"name": "user",          "type": "relation", "required": True,
         "options": {"collectionId": "_pb_users_auth_", "maxSelect": 1}},
        {"name": "prompt",        "type": "text",     "required": True},
        {"name": "content",       "type": "text",     "required": True},
        {"name": "ai_reflection", "type": "text",     "required": False},
    ],
    "listRule": "user = @request.auth.id",
    "viewRule": "user = @request.auth.id",
    "createRule": "@request.auth.id != ''",
    "updateRule": "user = @request.auth.id",
    "deleteRule": "user = @request.auth.id",
}

AI_CONVERSATIONS_SCHEMA = {
    "name": "ai_conversations",
    "type": "base",
    "schema": [
        {"name": "user",    "type": "relation", "required": True,
         "options": {"collectionId": "_pb_users_auth_", "maxSelect": 1}},
        {"name": "messages","type": "json",     "required": False},
        {"name": "summary", "type": "text",     "required": False},
    ],
    "listRule": "user = @request.auth.id",
    "viewRule": "user = @request.auth.id",
    "createRule": "@request.auth.id != ''",
    "updateRule": "user = @request.auth.id",
    "deleteRule": "user = @request.auth.id",
}


# ============================================================
# Seed Data — The 24 Original Resource Cards
# ============================================================

SEED_RESOURCES = [
    {"title": "Immediate Help",      "description": "Access 24/7 crisis hotlines and immediate text support resources.",                    "icon": "support_agent",        "color_class": "blue",   "category": "crisis",      "order": 1,  "is_active": True},
    {"title": "Guided Meditations",  "description": "Audio and visual guides to help you center yourself and find peace.",                 "icon": "self_improvement",     "color_class": "green",  "category": "mindfulness", "order": 2,  "is_active": True},
    {"title": "Therapy Finder",      "description": "Tools to help you locate and connect with licensed professionals.",                   "icon": "psychology",           "color_class": "purple", "category": "therapy",     "order": 3,  "is_active": True},
    {"title": "Self-Care Routines",  "description": "Daily habits and checklists for maintaining emotional health.",                       "icon": "checklist",            "color_class": "yellow", "category": "self-care",   "order": 4,  "is_active": True},
    {"title": "Anxiety Toolkit",     "description": "Practical grounding exercises and breathing techniques for panic.",                   "icon": "monitor_heart",        "color_class": "red",    "category": "tools",       "order": 5,  "is_active": True},
    {"title": "Support Groups",      "description": "Connect with local and online communities of people who understand.",                 "icon": "groups",               "color_class": "teal",   "category": "therapy",     "order": 6,  "is_active": True},
    {"title": "Journaling Prompts",  "description": "Guided questions to help process your thoughts and emotions daily.",                  "icon": "edit_note",            "color_class": "blue",   "category": "creative",    "order": 7,  "is_active": True},
    {"title": "Sleep Hygiene",       "description": "Tips and relaxing routines to improve your sleep quality and rest.",                   "icon": "bedtime",              "color_class": "purple", "category": "self-care",   "order": 8,  "is_active": True},
    {"title": "Mood Tracker",        "description": "Printable logs and digital tools to observe your emotional patterns.",                "icon": "mood",                 "color_class": "yellow", "category": "tools",       "order": 9,  "is_active": True},
    {"title": "Nutrition & Mind",    "description": "Learn how certain foods and hydration impact your mental energy.",                    "icon": "restaurant_menu",      "color_class": "green",  "category": "physical",    "order": 10, "is_active": True},
    {"title": "Movement & Yoga",     "description": "Gentle stretches and physical activities to release bodily tension.",                 "icon": "directions_run",       "color_class": "teal",   "category": "physical",    "order": 11, "is_active": True},
    {"title": "Goal Setting",        "description": "Break down overwhelming tasks into small, manageable milestones.",                    "icon": "flag",                 "color_class": "red",    "category": "tools",       "order": 12, "is_active": True},
    {"title": "Boundary Setting",    "description": "Scripts and advice for communicating your limits to others.",                         "icon": "pan_tool",             "color_class": "blue",   "category": "self-care",   "order": 13, "is_active": True},
    {"title": "Podcasts & Audio",    "description": "Curated list of uplifting and educational mental health podcasts.",                   "icon": "podcasts",             "color_class": "purple", "category": "creative",    "order": 14, "is_active": True},
    {"title": "Nature Therapy",      "description": "Discover the grounding benefits of ecotherapy and outdoor time.",                     "icon": "park",                 "color_class": "green",  "category": "mindfulness", "order": 15, "is_active": True},
    {"title": "Digital Detox",       "description": "Strategies to unplug, reduce screen time, and stay present.",                         "icon": "phonelink_erase",      "color_class": "yellow", "category": "self-care",   "order": 16, "is_active": True},
    {"title": "Hydration Tracker",   "description": "Reminders and logs to ensure you drink enough water throughout the day.",             "icon": "water_drop",           "color_class": "blue",   "category": "physical",    "order": 17, "is_active": True},
    {"title": "Art Therapy",         "description": "Creative prompts and digital sketchpads to express feelings visually.",               "icon": "palette",              "color_class": "purple", "category": "creative",    "order": 18, "is_active": True},
    {"title": "Gratitude Journal",   "description": "Space to note three positive things that happen to you each day.",                    "icon": "volunteer_activism",   "color_class": "yellow", "category": "creative",    "order": 19, "is_active": True},
    {"title": "Breathing Exercises", "description": "Interactive pacing visuals for box breathing and 4-7-8 techniques.",                  "icon": "air",                  "color_class": "teal",   "category": "mindfulness", "order": 20, "is_active": True},
    {"title": "Mindfulness Bells",   "description": "Periodic gentle chimes to remind you to check your posture and breathe.",             "icon": "notifications_active", "color_class": "green",  "category": "mindfulness", "order": 21, "is_active": True},
    {"title": "Panic Button",        "description": "Immediate access to your pre-configured emergency contacts and coping steps.",        "icon": "emergency",            "color_class": "red",    "category": "crisis",      "order": 22, "is_active": True},
    {"title": "Habit Builder",       "description": "Tools to slowly integrate positive routines without feeling overwhelmed.",             "icon": "route",                "color_class": "blue",   "category": "tools",       "order": 23, "is_active": True},
    {"title": "Music for Focus",     "description": "Binaural beats and lo-fi playlists curated for calm concentration.",                  "icon": "headphones",           "color_class": "purple", "category": "creative",    "order": 24, "is_active": True},
]


def seed_resources(token: str) -> None:
    """Insert the 24 resource cards into PocketBase."""
    # Check if already seeded
    resp = httpx.get(
        f"{PB_URL}/api/collections/resources/records",
        headers={"Authorization": token},
        params={"perPage": 1},
    )
    if resp.status_code == 200 and resp.json().get("totalItems", 0) > 0:
        count = resp.json()["totalItems"]
        print(f"  ⏩ Resources already seeded ({count} records), skipping")
        return

    print(f"  🌱 Seeding {len(SEED_RESOURCES)} resources...")
    for r in SEED_RESOURCES:
        resp = httpx.post(
            f"{PB_URL}/api/collections/resources/records",
            headers={"Authorization": token, "Content-Type": "application/json"},
            json=r,
        )
        if resp.status_code == 200:
            print(f"    ✅ {r['title']}")
        else:
            print(f"    ❌ {r['title']}: {resp.text}")


def main():
    parser = argparse.ArgumentParser(description="Set up PocketBase for The Calm Center")
    parser.add_argument("--email", required=True, help="PocketBase admin email")
    parser.add_argument("--password", required=True, help="PocketBase admin password")
    args = parser.parse_args()

    print("🔧 The Calm Center — PocketBase Setup")
    print("=" * 40)

    # 1. Login
    token = admin_login(args.email, args.password)

    # 2. Create collections
    print("\n📦 Creating collections...")
    create_collection(token, RESOURCES_SCHEMA)
    create_collection(token, MOOD_LOGS_SCHEMA)
    create_collection(token, JOURNAL_ENTRIES_SCHEMA)
    create_collection(token, AI_CONVERSATIONS_SCHEMA)

    # 3. Seed resources
    print("\n🌱 Seeding data...")
    seed_resources(token)

    print("\n✅ Setup complete!")
    print(f"   Admin UI: {PB_URL}/_/")
    print(f"   API:      {PB_URL}/api/")


if __name__ == "__main__":
    main()
