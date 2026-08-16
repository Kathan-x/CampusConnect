"""
CampusConnect - College Event & Registration Management System
Flask + PyMongo backend. MongoDB operations are commented for viva reference.
"""
import re
import time
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from pymongo.errors import DuplicateKeyError, PyMongoError

from config.database import get_db, check_connection
from config.query_console import (
    QueryError,
    parse_custom_query,
    execute_read_query,
    prepare_write_query,
)

app = Flask(__name__)
app.secret_key = "campusconnect-dev-secret"

CATEGORIES = ["Technical", "Cultural", "Sports", "Workshop", "Seminar", "Hackathon"]
STATUSES = ["Open", "Full", "Completed", "Cancelled"]
CATEGORY_COLORS = {
    "Technical": "#6366f1",
    "Cultural": "#a78bfa",
    "Workshop": "#14b8a6",
    "Sports": "#f59e0b",
    "Seminar": "#f43f5e",
    "Hackathon": "#7c3aed",
}
DEFAULT_CATEGORY_COLOR = "#94a3b8"


# ---------- helpers ----------

def next_sequence_id(db, collection_name, field, prefix, width):
    """Generates the next EVT/REG style id by counting existing documents."""
    count = db[collection_name].count_documents({})
    return f"{prefix}{count + 1:0{width}d}"


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or "") is not None


def is_valid_phone(phone):
    return re.match(r"^\d{10}$", phone or "") is not None


# ---------- pages ----------

def get_dashboard_stats(db):
    """Shared MongoDB-backed stats used by both the Home command-center and Dashboard pages."""
    today = datetime.now().strftime("%Y-%m-%d")

    total_events = db.events.count_documents({})
    total_registrations = db.registrations.count_documents({})
    upcoming_events = db.events.count_documents({"date": {"$gte": today}})  # scheduled from today onward
    open_events = db.events.count_documents({"status": "Open"})
    completed_events = db.events.count_documents({"status": "Completed"})

    # aggregation: upcoming events with live registered_count per event ($lookup)
    upcoming_list = list(db.events.aggregate([
        {"$match": {"date": {"$gte": today}}},
        {"$lookup": {
            "from": "registrations", "localField": "event_id",
            "foreignField": "event_id", "as": "regs"
        }},
        {"$addFields": {"registered_count": {"$size": "$regs"}}},
        {"$project": {"_id": 0, "regs": 0}},
        {"$sort": {"date": 1}},
        {"$limit": 5},
    ]))
    for e in upcoming_list:
        e["color"] = CATEGORY_COLORS.get(e["category"], DEFAULT_CATEGORY_COLOR)

    # find() with sort + limit for the recent registrations preview
    recent_registrations = list(db.registrations.find().sort("registered_at", -1).limit(5))
    event_names = {e["event_id"]: e["event_name"] for e in db.events.find({}, {"_id": 0, "event_id": 1, "event_name": 1})}
    for r in recent_registrations:
        r["event_name"] = event_names.get(r["event_id"], "Unknown Event")

    # aggregation: count events grouped by category, with color + share % for the donut chart
    category_breakdown = list(db.events.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]))
    max_category_count = max((c["count"] for c in category_breakdown), default=0)
    for c in category_breakdown:
        c["color"] = CATEGORY_COLORS.get(c["_id"], DEFAULT_CATEGORY_COLOR)
        c["percentage"] = round(c["count"] / total_events * 100) if total_events else 0

    # aggregation: total seat capacity across all events
    capacity_result = list(db.events.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$max_participants"}}}
    ]))
    total_capacity = capacity_result[0]["total"] if capacity_result else 0

    return {
        "total_events": total_events,
        "total_registrations": total_registrations,
        "upcoming_events": upcoming_events,
        "open_events": open_events,
        "completed_events": completed_events,
        "upcoming_list": upcoming_list,
        "recent_registrations": recent_registrations,
        "category_breakdown": category_breakdown,
        "max_category_count": max_category_count,
        "total_capacity": total_capacity,
        "today_display": datetime.now().strftime("%A, %d %B %Y"),
    }


@app.route("/")
def index():
    db = get_db()
    stats = get_dashboard_stats(db)
    return render_template("index.html", **stats)


@app.route("/dashboard")
def dashboard():
    db = get_db()
    stats = get_dashboard_stats(db)
    return render_template("dashboard.html", **stats)


@app.route("/events")
def events_page():
    initial_search = request.args.get("search", "").strip()
    return render_template(
        "events.html", categories=CATEGORIES, statuses=STATUSES, initial_search=initial_search
    )


@app.route("/api/events")
def api_events():
    db = get_db()
    match = {}

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()

    if search:
        match["event_name"] = {"$regex": re.escape(search), "$options": "i"}  # regex search
    if category:
        match["category"] = category
    if status:
        match["status"] = status

    # aggregation: attach live registered_count per event (for capacity indicators)
    events = list(db.events.aggregate([
        {"$match": match},
        {"$lookup": {
            "from": "registrations", "localField": "event_id",
            "foreignField": "event_id", "as": "regs"
        }},
        {"$addFields": {"registered_count": {"$size": "$regs"}}},
        {"$project": {"_id": 0, "regs": 0}},
        {"$sort": {"date": 1}},
    ]))
    return jsonify(events)


@app.route("/events/add", methods=["GET", "POST"])
def add_event():
    db = get_db()
    if request.method == "POST":
        form = request.form
        errors = validate_event_form(form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("add_event.html", categories=CATEGORIES, statuses=STATUSES, form=form)

        event_id = next_sequence_id(db, "events", "event_id", "EVT", 3)
        doc = {
            "event_id": event_id,
            "event_name": form["event_name"].strip(),
            "category": form["category"],
            "description": form.get("description", "").strip(),
            "date": form["date"],
            "time": form["time"],
            "venue": form["venue"].strip(),
            "organizer": form["organizer"].strip(),
            "max_participants": int(form["max_participants"]),
            "registration_fee": float(form["registration_fee"]),
            "status": form["status"],
            "created_at": datetime.now(timezone.utc),
        }
        try:
            db.events.insert_one(doc)  # CREATE
            flash(f"Event '{doc['event_name']}' created successfully.", "success")
            return redirect(url_for("events_page"))
        except DuplicateKeyError:
            flash("An event with this ID already exists.", "error")
        except PyMongoError:
            flash("Database error while creating event.", "error")

    return render_template("add_event.html", categories=CATEGORIES, statuses=STATUSES, form={})


@app.route("/events/edit/<event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    db = get_db()
    event = db.events.find_one({"event_id": event_id})  # READ single doc
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("events_page"))

    if request.method == "POST":
        form = request.form
        errors = validate_event_form(form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("edit_event.html", event=event, categories=CATEGORIES, statuses=STATUSES)

        update_fields = {
            "event_name": form["event_name"].strip(),
            "category": form["category"],
            "description": form.get("description", "").strip(),
            "date": form["date"],
            "time": form["time"],
            "venue": form["venue"].strip(),
            "organizer": form["organizer"].strip(),
            "max_participants": int(form["max_participants"]),
            "registration_fee": float(form["registration_fee"]),
            "status": form["status"],
        }
        try:
            result = db.events.update_one({"event_id": event_id}, {"$set": update_fields})  # UPDATE
            if result.matched_count == 0:
                flash("Event not found.", "error")
            else:
                flash("Event updated successfully.", "success")
            return redirect(url_for("events_page"))
        except PyMongoError:
            flash("Database error while updating event.", "error")

    return render_template("edit_event.html", event=event, categories=CATEGORIES, statuses=STATUSES)


@app.route("/events/delete/<event_id>", methods=["POST"])
def delete_event(event_id):
    db = get_db()
    try:
        result = db.events.delete_one({"event_id": event_id})  # DELETE
        if result.deleted_count == 0:
            return jsonify({"success": False, "message": "Event not found."}), 404
        return jsonify({"success": True, "message": "Event deleted successfully."})
    except PyMongoError:
        return jsonify({"success": False, "message": "Database error while deleting event."}), 500


def validate_event_form(form):
    errors = []
    if not form.get("event_name", "").strip():
        errors.append("Event name is required.")
    if form.get("category") not in CATEGORIES:
        errors.append("Please select a valid category.")
    if not form.get("date"):
        errors.append("Date is required.")
    if not form.get("venue", "").strip():
        errors.append("Venue is required.")
    if not form.get("organizer", "").strip():
        errors.append("Organizer is required.")
    try:
        if int(form.get("max_participants", -1)) <= 0:
            errors.append("Maximum participants must be a positive number.")
    except ValueError:
        errors.append("Maximum participants must be a number.")
    try:
        if float(form.get("registration_fee", -1)) < 0:
            errors.append("Registration fee cannot be negative.")
    except ValueError:
        errors.append("Registration fee must be a number.")
    if form.get("status") not in STATUSES:
        errors.append("Please select a valid status.")
    return errors


# ---------- registrations ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    db = get_db()
    open_events = list(db.events.find({"status": "Open"}, {"_id": 0}).sort("event_name", 1))

    if request.method == "POST":
        form = request.form
        errors = []
        if not form.get("student_name", "").strip():
            errors.append("Student name is required.")
        if not form.get("enrollment_number", "").strip():
            errors.append("Enrollment number is required.")
        if not is_valid_email(form.get("email")):
            errors.append("Please enter a valid email address.")
        if not is_valid_phone(form.get("phone")):
            errors.append("Phone number must be exactly 10 digits.")
        if not form.get("department", "").strip():
            errors.append("Department is required.")
        if not form.get("year"):
            errors.append("Year is required.")
        event_id = form.get("event_id")
        event = db.events.find_one({"event_id": event_id}) if event_id else None
        if not event:
            errors.append("Please select a valid event.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", events=open_events, form=form)

        registration_id = next_sequence_id(db, "registrations", "registration_id", "REG", 4)
        doc = {
            "registration_id": registration_id,
            "event_id": event_id,
            "student_name": form["student_name"].strip(),
            "enrollment_number": form["enrollment_number"].strip(),
            "email": form["email"].strip(),
            "phone": form["phone"].strip(),
            "department": form["department"].strip(),
            "year": form["year"],
            "registered_at": datetime.now(timezone.utc),
        }
        try:
            db.registrations.insert_one(doc)  # CREATE registration
            flash("Registration successful!", "success")
            return redirect(url_for("register"))
        except DuplicateKeyError:
            flash("You have already registered for this event.", "error")
        except PyMongoError:
            flash("Database error while registering.", "error")

    return render_template("register.html", events=open_events, form={})


@app.route("/registrations")
def registrations_page():
    db = get_db()
    events = list(db.events.find({}, {"_id": 0, "event_id": 1, "event_name": 1}))
    return render_template("registrations.html", events=events)


def validate_registration_form(form):
    errors = []
    if not form.get("student_name", "").strip():
        errors.append("Student name is required.")
    if not form.get("enrollment_number", "").strip():
        errors.append("Enrollment number is required.")
    if not is_valid_email(form.get("email")):
        errors.append("Please enter a valid email address.")
    if not is_valid_phone(form.get("phone")):
        errors.append("Phone number must be exactly 10 digits.")
    if not form.get("department", "").strip():
        errors.append("Department is required.")
    if not form.get("year"):
        errors.append("Year is required.")
    if not form.get("event_id"):
        errors.append("Please select an event.")
    return errors


@app.route("/registrations/edit/<registration_id>", methods=["GET", "POST"])
def edit_registration(registration_id):
    db = get_db()
    registration = db.registrations.find_one({"registration_id": registration_id})  # READ single doc
    if not registration:
        flash("Registration not found.", "error")
        return redirect(url_for("registrations_page"))

    all_events = list(db.events.find({}, {"_id": 0}).sort("event_name", 1))

    if request.method == "POST":
        form = request.form
        errors = validate_registration_form(form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("edit_registration.html", registration=registration, events=all_events)

        update_fields = {
            "student_name": form["student_name"].strip(),
            "enrollment_number": form["enrollment_number"].strip(),
            "email": form["email"].strip(),
            "phone": form["phone"].strip(),
            "department": form["department"].strip(),
            "year": form["year"],
            "event_id": form["event_id"],
        }
        try:
            result = db.registrations.update_one(
                {"registration_id": registration_id}, {"$set": update_fields}
            )  # UPDATE
            if result.matched_count == 0:
                flash("Registration not found.", "error")
            else:
                flash("Registration updated successfully.", "success")
            return redirect(url_for("registrations_page"))
        except DuplicateKeyError:
            flash("This student is already registered for the selected event.", "error")
        except PyMongoError:
            flash("Database error while updating registration.", "error")

    return render_template("edit_registration.html", registration=registration, events=all_events)


@app.route("/api/registrations")
def api_registrations():
    db = get_db()
    query = {}
    search = request.args.get("search", "").strip()
    event_id = request.args.get("event_id", "").strip()
    department = request.args.get("department", "").strip()

    if search:
        query["$or"] = [
            {"student_name": {"$regex": re.escape(search), "$options": "i"}},
            {"enrollment_number": {"$regex": re.escape(search), "$options": "i"}},
        ]
    if event_id:
        query["event_id"] = event_id
    if department:
        query["department"] = department

    registrations = list(db.registrations.find(query, {"_id": 0}).sort("registered_at", -1))

    # attach event name + category for display (simple lookup loop - easy to explain in viva)
    event_lookup = {
        e["event_id"]: e
        for e in db.events.find({}, {"_id": 0, "event_id": 1, "event_name": 1, "category": 1})
    }
    for r in registrations:
        ev = event_lookup.get(r["event_id"])
        r["event_name"] = ev["event_name"] if ev else "Unknown Event"
        r["category"] = ev["category"] if ev else None

    return jsonify(registrations)


# ---------- MongoDB Query Center ----------

@app.route("/queries")
def queries_page():
    return render_template("queries.html")


QUERY_DEFINITIONS = {
    "all_events": "db.events.find({})",
    "technical": "db.events.find({category: 'Technical'})",
    "cultural": "db.events.find({category: 'Cultural'})",
    "sports": "db.events.find({category: 'Sports'})",
    "workshop": "db.events.find({category: 'Workshop'})",
    "hackathon": "db.events.find({category: 'Hackathon'})",
    "upcoming": "db.events.find({date: {$gte: today}, status: 'Open'})",
    "completed": "db.events.find({status: 'Completed'})",
    "fee_above_500": "db.events.find({registration_fee: {$gt: 500}})",
    "capacity_above_100": "db.events.find({max_participants: {$gt: 100}})",
    "search_by_name": "db.events.find({event_name: {$regex: <term>, $options: 'i'}})",
    "sort_by_date": "db.events.find({}).sort({date: 1})",
    "most_registered": "db.registrations.aggregate([$group by event_id, $sort desc, $lookup events])",
    "registration_count_by_event": "db.events aggregate with $lookup into registrations, $project count",
    "total_registrations": "db.registrations.count_documents({})",
}


@app.route("/api/query/<query_key>")
def run_query(query_key):
    db = get_db()
    label = QUERY_DEFINITIONS.get(query_key)
    if not label:
        return jsonify({"success": False, "message": "Unknown query."}), 400

    try:
        if query_key == "all_events":
            data = list(db.events.find({}, {"_id": 0}).sort("date", 1))
        elif query_key in ("technical", "cultural", "sports", "workshop", "hackathon"):
            category = query_key.capitalize()
            data = list(db.events.find({"category": category}, {"_id": 0}))
        elif query_key == "upcoming":
            today = datetime.now().strftime("%Y-%m-%d")
            data = list(db.events.find({"date": {"$gte": today}, "status": "Open"}, {"_id": 0}).sort("date", 1))
        elif query_key == "completed":
            data = list(db.events.find({"status": "Completed"}, {"_id": 0}))
        elif query_key == "fee_above_500":
            data = list(db.events.find({"registration_fee": {"$gt": 500}}, {"_id": 0}))
        elif query_key == "capacity_above_100":
            data = list(db.events.find({"max_participants": {"$gt": 100}}, {"_id": 0}))
        elif query_key == "search_by_name":
            term = request.args.get("term", "")
            data = list(db.events.find(
                {"event_name": {"$regex": re.escape(term), "$options": "i"}}, {"_id": 0}
            ))
        elif query_key == "sort_by_date":
            data = list(db.events.find({}, {"_id": 0}).sort("date", 1))
        elif query_key == "most_registered":
            data = list(db.registrations.aggregate([
                {"$group": {"_id": "$event_id", "registration_count": {"$sum": 1}}},
                {"$sort": {"registration_count": -1}},
                {"$lookup": {
                    "from": "events", "localField": "_id",
                    "foreignField": "event_id", "as": "event_info"
                }},
                {"$unwind": {"path": "$event_info", "preserveNullAndEmptyArrays": True}},
                {"$project": {
                    "_id": 0,
                    "event_id": "$_id",
                    "event_name": "$event_info.event_name",
                    "registration_count": 1,
                }},
            ]))
        elif query_key == "registration_count_by_event":
            data = list(db.events.aggregate([
                {"$lookup": {
                    "from": "registrations", "localField": "event_id",
                    "foreignField": "event_id", "as": "regs"
                }},
                {"$project": {
                    "_id": 0,
                    "event_id": 1,
                    "event_name": 1,
                    "registration_count": {"$size": "$regs"},
                }},
                {"$sort": {"registration_count": -1}},
            ]))
        elif query_key == "total_registrations":
            data = {"total_registrations": db.registrations.count_documents({})}
        else:
            data = []

        return jsonify({"success": True, "query": label, "result": data})
    except PyMongoError as ex:
        return jsonify({"success": False, "message": f"Database error: {ex}"}), 500


# ---------- Custom MongoDB Query Console (additive, whitelist-based - see config/query_console.py) ----------

@app.route("/api/custom-query", methods=["POST"])
def custom_query():
    db = get_db()
    payload = request.get_json(silent=True) or {}
    raw_query = (payload.get("query") or "").strip()
    confirmed = bool(payload.get("confirmed"))

    if not raw_query:
        return jsonify({"success": False, "error": "Please enter a query to execute."}), 400

    try:
        collection, op, args_str, sort_str = parse_custom_query(raw_query)
        start = time.perf_counter()

        if op in ("updateOne", "deleteOne"):
            filter_doc, update_doc, summary = prepare_write_query(collection, op, args_str)

            if not confirmed:
                return jsonify({
                    "success": True,
                    "requires_confirmation": True,
                    "operation": op,
                    "collection": collection,
                    "summary": summary,
                })

            coll = db[collection]
            if op == "updateOne":
                result = coll.update_one(filter_doc, update_doc)  # UPDATE (custom console)
                elapsed = round((time.perf_counter() - start) * 1000, 1)
                return jsonify({
                    "success": True, "result_type": "update",
                    "matched_count": result.matched_count, "modified_count": result.modified_count,
                    "execution_time_ms": elapsed,
                })
            else:
                result = coll.delete_one(filter_doc)  # DELETE (custom console)
                elapsed = round((time.perf_counter() - start) * 1000, 1)
                return jsonify({
                    "success": True, "result_type": "delete",
                    "deleted_count": result.deleted_count,
                    "execution_time_ms": elapsed,
                })

        result = execute_read_query(db, collection, op, args_str, sort_str)  # READ / AGGREGATE
        result["execution_time_ms"] = round((time.perf_counter() - start) * 1000, 1)
        result["success"] = True
        return jsonify(result)

    except QueryError as qe:
        return jsonify({"success": False, "error": str(qe)}), 400
    except PyMongoError:
        return jsonify({"success": False, "error": "Database error while executing the query."}), 500
    except Exception:
        return jsonify({
            "success": False,
            "error": "Unsupported query syntax. Try one of the supported MongoDB operations.",
        }), 400


# ---------- error handling ----------

@app.errorhandler(404)
def not_found(e):
    db = get_db()
    stats = get_dashboard_stats(db)
    return render_template("index.html", **stats), 404


if __name__ == "__main__":
    if not check_connection():
        print("WARNING: could not connect to MongoDB. Check that mongod is running.")
    app.run(debug=True, port=5000)
