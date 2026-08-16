"""
Seed script - clears events & registrations collections and inserts
realistic sample data using insertMany().
Run: python database/seed_data.py
"""
import sys
import os
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.database import get_db

events = [
    {"event_id": "EVT001", "event_name": "CodeStorm Hackathon", "category": "Hackathon",
     "description": "24-hour hackathon for building solutions around smart campus tech.",
     "date": "2026-09-12", "time": "09:00", "venue": "Main Auditorium",
     "organizer": "CSE Department", "max_participants": 120, "registration_fee": 300,
     "status": "Open"},
    {"event_id": "EVT002", "event_name": "Rangotsav Cultural Fest", "category": "Cultural",
     "description": "Annual inter-college cultural fest with dance, music and drama.",
     "date": "2026-09-20", "time": "17:00", "venue": "Open Air Theatre",
     "organizer": "Cultural Committee", "max_participants": 300, "registration_fee": 100,
     "status": "Open"},
    {"event_id": "EVT003", "event_name": "Inter-College Cricket Cup", "category": "Sports",
     "description": "T20 cricket tournament between affiliated colleges.",
     "date": "2026-08-25", "time": "08:00", "venue": "College Sports Ground",
     "organizer": "Sports Department", "max_participants": 160, "registration_fee": 200,
     "status": "Open"},
    {"event_id": "EVT004", "event_name": "Python for Data Science Workshop", "category": "Workshop",
     "description": "Hands-on workshop covering pandas, numpy and basic ML.",
     "date": "2026-08-18", "time": "10:00", "venue": "Computer Lab 2",
     "organizer": "BCA Department", "max_participants": 60, "registration_fee": 150,
     "status": "Open"},
    {"event_id": "EVT005", "event_name": "AI & Future of Work Seminar", "category": "Seminar",
     "description": "Guest lecture on AI's impact on employment and industry.",
     "date": "2026-08-30", "time": "11:00", "venue": "Seminar Hall A",
     "organizer": "IT Department", "max_participants": 150, "registration_fee": 0,
     "status": "Open"},
    {"event_id": "EVT006", "event_name": "Web Dev Bootcamp", "category": "Technical",
     "description": "Two-day bootcamp on HTML, CSS, JS and Flask basics.",
     "date": "2026-09-05", "time": "09:30", "venue": "Computer Lab 1",
     "organizer": "CSE Department", "max_participants": 80, "registration_fee": 250,
     "status": "Open"},
    {"event_id": "EVT007", "event_name": "Robo Race Championship", "category": "Technical",
     "description": "Line-following robot competition for engineering students.",
     "date": "2026-09-15", "time": "10:00", "venue": "Mechanical Block Arena",
     "organizer": "Robotics Club", "max_participants": 50, "registration_fee": 400,
     "status": "Open"},
    {"event_id": "EVT008", "event_name": "Classical Dance Night", "category": "Cultural",
     "description": "Solo and group classical dance performances.",
     "date": "2026-07-28", "time": "18:30", "venue": "Open Air Theatre",
     "organizer": "Cultural Committee", "max_participants": 100, "registration_fee": 50,
     "status": "Completed"},
    {"event_id": "EVT009", "event_name": "Badminton Doubles Tournament", "category": "Sports",
     "description": "Knockout badminton doubles tournament, open to all years.",
     "date": "2026-08-22", "time": "07:30", "venue": "Indoor Sports Complex",
     "organizer": "Sports Department", "max_participants": 64, "registration_fee": 100,
     "status": "Open"},
    {"event_id": "EVT010", "event_name": "Cyber Security Workshop", "category": "Workshop",
     "description": "Ethical hacking basics, network security and CTF challenge.",
     "date": "2026-09-08", "time": "10:00", "venue": "Computer Lab 3",
     "organizer": "IT Department", "max_participants": 70, "registration_fee": 350,
     "status": "Open"},
    {"event_id": "EVT011", "event_name": "Entrepreneurship Summit", "category": "Seminar",
     "description": "Panel discussion with startup founders and alumni.",
     "date": "2026-07-15", "time": "11:30", "venue": "Seminar Hall B",
     "organizer": "BBA Department", "max_participants": 200, "registration_fee": 0,
     "status": "Completed"},
    {"event_id": "EVT012", "event_name": "App Development Challenge", "category": "Hackathon",
     "description": "48-hour mobile app building challenge for student teams.",
     "date": "2026-10-02", "time": "09:00", "venue": "Innovation Center",
     "organizer": "CSE Department", "max_participants": 100, "registration_fee": 500,
     "status": "Open"},
    {"event_id": "EVT013", "event_name": "Photography Exhibition", "category": "Cultural",
     "description": "Student photography showcase with theme 'Campus Life'.",
     "date": "2026-08-05", "time": "16:00", "venue": "Art Gallery Hall",
     "organizer": "Photography Club", "max_participants": 90, "registration_fee": 0,
     "status": "Cancelled"},
    {"event_id": "EVT014", "event_name": "Kabaddi Championship", "category": "Sports",
     "description": "Traditional kabaddi tournament between departments.",
     "date": "2026-09-25", "time": "08:00", "venue": "College Sports Ground",
     "organizer": "Sports Department", "max_participants": 140, "registration_fee": 150,
     "status": "Open"},
    {"event_id": "EVT015", "event_name": "Cloud Computing Workshop", "category": "Workshop",
     "description": "Introduction to AWS, Azure and deployment basics.",
     "date": "2026-09-18", "time": "10:30", "venue": "Computer Lab 2",
     "organizer": "IT Department", "max_participants": 55, "registration_fee": 300,
     "status": "Full"},
]

students = [
    ("Aarav Sharma", "22BCA045", "aarav.sharma@example.com", "9876543210", "BCA", "3rd Year"),
    ("Priya Patel", "22BCA012", "priya.patel@example.com", "9823456712", "BCA", "3rd Year"),
    ("Rohan Mehta", "23BCA078", "rohan.mehta@example.com", "9765432189", "BCA", "2nd Year"),
    ("Sneha Iyer", "21BCA033", "sneha.iyer@example.com", "9654321098", "BCA", "Final Year"),
    ("Karan Verma", "23BCS021", "karan.verma@example.com", "9543210987", "BCS", "2nd Year"),
    ("Ananya Singh", "22BCS056", "ananya.singh@example.com", "9432109876", "BCS", "3rd Year"),
    ("Vikram Rao", "21BCS009", "vikram.rao@example.com", "9321098765", "BCS", "Final Year"),
    ("Ishita Joshi", "23BBA014", "ishita.joshi@example.com", "9210987654", "BBA", "1st Year"),
    ("Aditya Kulkarni", "22BBA028", "aditya.kulkarni@example.com", "9109876543", "BBA", "3rd Year"),
    ("Neha Gupta", "23BCA061", "neha.gupta@example.com", "9098765432", "BCA", "1st Year"),
    ("Siddharth Nair", "22BCA019", "siddharth.nair@example.com", "8987654321", "BCA", "3rd Year"),
    ("Riya Desai", "21BCA047", "riya.desai@example.com", "8876543210", "BCA", "Final Year"),
    ("Manav Choudhary", "23BCS033", "manav.choudhary@example.com", "8765432109", "BCS", "2nd Year"),
    ("Pooja Reddy", "22BCS041", "pooja.reddy@example.com", "8654321098", "BCS", "3rd Year"),
    ("Arjun Malhotra", "23BCA052", "arjun.malhotra@example.com", "8543210987", "BCA", "2nd Year"),
    ("Kavya Menon", "21BBA017", "kavya.menon@example.com", "8432109876", "BBA", "Final Year"),
    ("Yash Agarwal", "22BCA073", "yash.agarwal@example.com", "8321098765", "BCA", "3rd Year"),
    ("Divya Bhatt", "23BCS008", "divya.bhatt@example.com", "8210987654", "BCS", "1st Year"),
    ("Nikhil Pandey", "22BCA034", "nikhil.pandey@example.com", "8109876543", "BCA", "3rd Year"),
    ("Tanvi Kapoor", "21BCA025", "tanvi.kapoor@example.com", "8098765432", "BCA", "Final Year"),
    ("Harsh Trivedi", "23BBA039", "harsh.trivedi@example.com", "7987654321", "BBA", "2nd Year"),
    ("Meera Pillai", "22BCS062", "meera.pillai@example.com", "7876543210", "BCS", "3rd Year"),
    ("Devansh Saxena", "23BCA084", "devansh.saxena@example.com", "7765432109", "BCA", "1st Year"),
    ("Ritika Chauhan", "21BCS015", "ritika.chauhan@example.com", "7654321098", "BCS", "Final Year"),
    ("Om Prakash", "22BBA046", "om.prakash@example.com", "7543210987", "BBA", "3rd Year"),
]

# (student_index, event_id) pairs - spread across events, no duplicates
registration_pairs = [
    (0, "EVT001"), (1, "EVT001"), (2, "EVT001"), (3, "EVT004"), (4, "EVT004"),
    (5, "EVT006"), (6, "EVT006"), (7, "EVT002"), (8, "EVT002"), (9, "EVT002"),
    (10, "EVT003"), (11, "EVT003"), (12, "EVT009"), (13, "EVT009"), (14, "EVT005"),
    (15, "EVT005"), (16, "EVT010"), (17, "EVT010"), (18, "EVT012"), (19, "EVT012"),
    (20, "EVT007"), (21, "EVT014"), (22, "EVT015"), (23, "EVT001"), (24, "EVT004"),
]


def seed():
    db = get_db()

    db.events.delete_many({})
    db.registrations.delete_many({})

    now = datetime.now(timezone.utc)
    for e in events:
        e["created_at"] = now
    db.events.insert_many(events)
    print(f"Inserted {len(events)} events.")

    reg_docs = []
    for i, (student_idx, event_id) in enumerate(registration_pairs, start=1):
        name, enrollment, email, phone, dept, year = students[student_idx]
        reg_docs.append({
            "registration_id": f"REG{i:04d}",
            "event_id": event_id,
            "student_name": name,
            "enrollment_number": enrollment,
            "email": email,
            "phone": phone,
            "department": dept,
            "year": year,
            "registered_at": now,
        })
    db.registrations.insert_many(reg_docs)
    print(f"Inserted {len(reg_docs)} registrations.")


if __name__ == "__main__":
    seed()
