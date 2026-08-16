# CampusConnect – College Event & Registration Management System

## 1. Project Description

CampusConnect is a web application that lets a college administrator manage
college events (hackathons, workshops, seminars, cultural and sports fests)
and lets students register for them online. It is built as a BCA Semester 5
Distributed Database project to demonstrate practical use of **MongoDB**
through a Flask + PyMongo backend.

## 2. Objectives

- Demonstrate MongoDB as a NoSQL document database in a real application.
- Implement full CRUD operations (Create, Read, Update, Delete) on MongoDB collections.
- Demonstrate filtering, regex searching, sorting, and aggregation pipelines.
- Connect a plain HTML/CSS/JavaScript frontend to a Flask backend using PyMongo.

## 3. Features

- Landing page, admin dashboard with live KPIs
- Event Management: add / edit / delete / search / filter events
- Student Event Registration with validation and duplicate prevention
- Registration Management (admin view, search/filter)
- **MongoDB Query Center** – 15 live queries/aggregations run directly against MongoDB
- Toast notifications, delete confirmation modal, responsive layout

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript, Bootstrap grid |
| Backend | Python 3, Flask |
| Database | MongoDB |
| Driver | PyMongo |

```
HTML/CSS/JavaScript → Flask → PyMongo → MongoDB
```

## 5. MongoDB Database Structure

Database: **campusconnect**

### Collection: `events`
```js
{
  event_id: "EVT001",
  event_name: "CodeStorm Hackathon",
  category: "Hackathon",       // Technical | Cultural | Sports | Workshop | Seminar | Hackathon
  description: "...",
  date: "2026-09-12",
  time: "09:00",
  venue: "Main Auditorium",
  organizer: "CSE Department",
  max_participants: 120,
  registration_fee: 300,
  status: "Open",               // Open | Full | Completed | Cancelled
  created_at: ISODate(...)
}
```

### Collection: `registrations`
```js
{
  registration_id: "REG0001",
  event_id: "EVT001",
  student_name: "Aarav Sharma",
  enrollment_number: "22BCA045",
  email: "aarav.sharma@example.com",
  phone: "9876543210",
  department: "BCA",
  year: "3rd Year",
  registered_at: ISODate(...)
}
```

Indexes: `events.event_id` (unique), `registrations.registration_id` (unique),
compound `(event_id, enrollment_number)` (unique — blocks duplicate registrations).

## 6. CRUD Operations (where to find them in `app.py`)

| Operation | Route | PyMongo call |
|---|---|---|
| Create event | `POST /events/add` | `db.events.insert_one()` |
| Read events | `GET /api/events` | `db.events.find()` |
| Update event | `POST /events/edit/<event_id>` | `db.events.update_one()` |
| Delete event | `POST /events/delete/<event_id>` | `db.events.delete_one()` |
| Create registration | `POST /register` | `db.registrations.insert_one()` |
| Read registrations | `GET /api/registrations` | `db.registrations.find()` |

Also used: `count_documents()`, `.sort()`, regex `find()`, `aggregate()` with
`$group`, `$lookup`, `$sort`, `$project`, `$unwind`.

## 7. MongoDB Queries Used (Query Center)

1. View All Events – `find({})`
2. Technical / Cultural / Sports / Workshop / Hackathon Events – `find({category: ...})`
3. Upcoming Events – `find({date: {$gte: today}, status: "Open"})`
4. Completed Events – `find({status: "Completed"})`
5. Fee > ₹500 – `find({registration_fee: {$gt: 500}})`
6. Capacity > 100 – `find({max_participants: {$gt: 100}})`
7. Search Event by Name – `find({event_name: {$regex, $options: "i"}})`
8. Sort Events by Date – `find({}).sort({date: 1})`
9. Most Registered Events – aggregation: `$group` + `$sort` + `$lookup`
10. Registration Count by Event – aggregation: `$lookup` + `$project`
11. Total Registrations – `count_documents({})`

## 8. Folder Structure

```
CampusConnect/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── config/
│   └── database.py
├── database/
│   └── seed_data.py
├── templates/
│   ├── base.html, index.html, dashboard.html, events.html,
│   │   add_event.html, edit_event.html, register.html,
│   │   registrations.html, queries.html
└── static/
    ├── css/style.css
    └── js/ (app.js, events.js, registrations.js, queries.js, form-validate.js)
```

## 9. Installation & Running (Windows)

**Prerequisites:** Python 3.10+, MongoDB running locally (`mongod` service).

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set MongoDB connection (optional — defaults to localhost:27017 / campusconnect)
copy .env.example .env

# 5. Seed sample data (15 events, 25 registrations)
python database\seed_data.py

# 6. Start Flask
python app.py

# 7. Open in browser
# http://127.0.0.1:5000
```

## 10. Sample MongoDB Queries (mongosh)

```js
use campusconnect
db.events.find({ category: "Hackathon" })
db.events.find({ registration_fee: { $gt: 500 } })
db.registrations.countDocuments({})
db.registrations.aggregate([
  { $group: { _id: "$event_id", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])
```

## 11. Project Demonstration Flow

1. Home page → explain project purpose.
2. Dashboard → show KPIs are live from MongoDB (`count_documents`).
3. Event Management → add an event (insert_one), edit it (update_one), delete it (delete_one).
4. Student Registration → register for an event, show duplicate registration is blocked.
5. Registration Management → search/filter registrations.
6. MongoDB Query Center → run each of the 15 queries live, point out the printed query syntax.

## 12. Viva Explanation Points

- MongoDB is schema-less (NoSQL, document-based) — each event/registration is a JSON-like document (BSON).
- `insert_one`, `find`, `update_one`, `delete_one` are the core CRUD primitives (map to SQL INSERT/SELECT/UPDATE/DELETE).
- Regex-based `find` implements case-insensitive search without a separate search engine.
- Unique indexes (`event_id`, `registration_id`, `event_id+enrollment_number`) enforce data integrity at the database level, similar to SQL UNIQUE constraints.
- Aggregation pipeline (`$group`, `$lookup`, `$sort`, `$project`) performs SQL-JOIN-like and GROUP BY-like operations across `events` and `registrations`.
- Flask routes call PyMongo directly — no ORM — so every MongoDB operation is visible and explainable in `app.py`.
