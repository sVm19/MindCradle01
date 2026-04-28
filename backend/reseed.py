"""Re-seed resources with proper data now that fields exist."""
import httpx

PB = "http://127.0.0.1:8090"

r = httpx.post(
    f"{PB}/api/collections/_superusers/auth-with-password",
    json={"identity": "imshubham7004@gmail.com", "password": "Pulser@220"},
)
token = r.json()["token"]
H = {"Authorization": token, "Content-Type": "application/json"}
print("Logged in")

# Delete all existing empty records
recs = httpx.get(f"{PB}/api/collections/resources/records", headers=H, params={"perPage": 50})
items = recs.json().get("items", [])
for item in items:
    httpx.delete(f"{PB}/api/collections/resources/records/{item['id']}", headers=H)
print(f"Deleted {len(items)} empty records")

RESOURCES = [
    {"title": "Immediate Help",      "description": "Access 24/7 crisis hotlines and immediate text support resources.",          "icon": "support_agent",        "color_class": "blue",   "category": "crisis",      "order": 1,  "is_active": True},
    {"title": "Guided Meditations",  "description": "Audio and visual guides to help you center yourself and find peace.",       "icon": "self_improvement",     "color_class": "green",  "category": "mindfulness", "order": 2,  "is_active": True},
    {"title": "Therapy Finder",      "description": "Tools to help you locate and connect with licensed professionals.",         "icon": "psychology",           "color_class": "purple", "category": "therapy",     "order": 3,  "is_active": True},
    {"title": "Self-Care Routines",  "description": "Daily habits and checklists for maintaining emotional health.",             "icon": "checklist",            "color_class": "yellow", "category": "self-care",   "order": 4,  "is_active": True},
    {"title": "Anxiety Toolkit",     "description": "Practical grounding exercises and breathing techniques for panic.",         "icon": "monitor_heart",        "color_class": "red",    "category": "tools",       "order": 5,  "is_active": True},
    {"title": "Support Groups",      "description": "Connect with local and online communities of people who understand.",       "icon": "groups",               "color_class": "teal",   "category": "therapy",     "order": 6,  "is_active": True},
    {"title": "Journaling Prompts",  "description": "Guided questions to help process your thoughts and emotions daily.",        "icon": "edit_note",            "color_class": "blue",   "category": "creative",    "order": 7,  "is_active": True},
    {"title": "Sleep Hygiene",       "description": "Tips and relaxing routines to improve your sleep quality and rest.",         "icon": "bedtime",              "color_class": "purple", "category": "self-care",   "order": 8,  "is_active": True},
    {"title": "Mood Tracker",        "description": "Digital tools to observe your emotional patterns.",                          "icon": "mood",                 "color_class": "yellow", "category": "tools",       "order": 9,  "is_active": True},
    {"title": "Nutrition and Mind",  "description": "Learn how certain foods and hydration impact your mental energy.",           "icon": "restaurant_menu",      "color_class": "green",  "category": "physical",    "order": 10, "is_active": True},
    {"title": "Movement and Yoga",   "description": "Gentle stretches and physical activities to release bodily tension.",        "icon": "directions_run",       "color_class": "teal",   "category": "physical",    "order": 11, "is_active": True},
    {"title": "Goal Setting",        "description": "Break down overwhelming tasks into small, manageable milestones.",           "icon": "flag",                 "color_class": "red",    "category": "tools",       "order": 12, "is_active": True},
    {"title": "Boundary Setting",    "description": "Scripts and advice for communicating your limits to others.",                "icon": "pan_tool",             "color_class": "blue",   "category": "self-care",   "order": 13, "is_active": True},
    {"title": "Podcasts and Audio",  "description": "Curated list of uplifting and educational mental health podcasts.",          "icon": "podcasts",             "color_class": "purple", "category": "creative",    "order": 14, "is_active": True},
    {"title": "Nature Therapy",      "description": "Discover the grounding benefits of ecotherapy and outdoor time.",            "icon": "park",                 "color_class": "green",  "category": "mindfulness", "order": 15, "is_active": True},
    {"title": "Digital Detox",       "description": "Strategies to unplug, reduce screen time, and stay present.",                "icon": "phonelink_erase",      "color_class": "yellow", "category": "self-care",   "order": 16, "is_active": True},
    {"title": "Hydration Tracker",   "description": "Reminders and logs to ensure you drink enough water.",                       "icon": "water_drop",           "color_class": "blue",   "category": "physical",    "order": 17, "is_active": True},
    {"title": "Art Therapy",         "description": "Creative prompts and digital sketchpads to express feelings visually.",      "icon": "palette",              "color_class": "purple", "category": "creative",    "order": 18, "is_active": True},
    {"title": "Gratitude Journal",   "description": "Space to note three positive things that happen to you each day.",           "icon": "volunteer_activism",   "color_class": "yellow", "category": "creative",    "order": 19, "is_active": True},
    {"title": "Breathing Exercises", "description": "Interactive pacing visuals for box breathing and 4-7-8 techniques.",         "icon": "air",                  "color_class": "teal",   "category": "mindfulness", "order": 20, "is_active": True},
    {"title": "Mindfulness Bells",   "description": "Periodic gentle chimes to remind you to check your posture.",                "icon": "notifications_active", "color_class": "green",  "category": "mindfulness", "order": 21, "is_active": True},
    {"title": "Panic Button",        "description": "Immediate access to your emergency contacts and coping steps.",              "icon": "emergency",            "color_class": "red",    "category": "crisis",      "order": 22, "is_active": True},
    {"title": "Habit Builder",       "description": "Tools to slowly integrate positive routines without overwhelm.",             "icon": "route",                "color_class": "blue",   "category": "tools",       "order": 23, "is_active": True},
    {"title": "Music for Focus",     "description": "Binaural beats and lo-fi playlists curated for calm concentration.",         "icon": "headphones",           "color_class": "purple", "category": "creative",    "order": 24, "is_active": True},
]

ok = 0
for res in RESOURCES:
    resp = httpx.post(f"{PB}/api/collections/resources/records", headers=H, json=res)
    if resp.status_code == 200:
        ok += 1
        print(f"  + {res['title']}")
    else:
        print(f"  FAIL: {res['title']}: {resp.text[:200]}")

print(f"\nSeeded {ok}/24 resources")

# Verify
v = httpx.get(f"{PB}/api/collections/resources/records", headers=H, params={"perPage": 1, "sort": "order"})
sample = v.json()["items"][0]
print(f"Verify: {sample['title']} | {sample['icon']} | {sample['category']}")
