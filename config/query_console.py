"""
Custom MongoDB Query Console - safe, whitelist-based parser and executor.

Accepts a single line/block of mongo-shell-like text such as:
    db.events.find({ category: "Technical" }).sort({ date: 1 })
    db.registrations.countDocuments({})
    db.events.aggregate([{ $group: { _id: "$category", total: { $sum: 1 } } }])

Design goals (viva-relevant):
- NEVER uses eval()/exec() or any dynamic code execution. The query text is
  parsed into a plain Python dict/list using regex + json.loads(), then that
  data is handed straight to PyMongo's normal find()/aggregate()/etc methods.
- Everything is whitelist-based: only two collections, five operations, and a
  fixed set of MongoDB operators/aggregation stages are ever allowed. Anything
  else is rejected with a clean message instead of running.
"""
import json
import re
from datetime import datetime

from bson import ObjectId

ALLOWED_COLLECTIONS = {"events", "registrations"}
ALLOWED_OPS = {"find", "countDocuments", "aggregate", "updateOne", "deleteOne"}
ALLOWED_STAGES = {
    "$match", "$group", "$sort", "$limit", "$project",
    "$lookup", "$unwind", "$addFields", "$count",
}
ALLOWED_OPERATORS = {
    "$gt", "$gte", "$lt", "$lte", "$eq", "$ne", "$in", "$nin",
    "$regex", "$options", "$and", "$or", "$exists",
    "$set", "$sum", "$avg", "$size", "$first", "$last", "$push", "$min", "$max",
}
ALLOWED_DOLLAR_KEYS = ALLOWED_STAGES | ALLOWED_OPERATORS
MAX_RESULTS = 500


class QueryError(Exception):
    """Raised for any query the console refuses to run - always shown as a clean message."""


# ---------- text -> safe Python data ----------

def _js_like_to_json(text):
    """Turn a mongo-shell style object literal into valid JSON text.

    Only handles the two things real MongoDB shell syntax needs that JSON
    doesn't allow: unquoted keys (category: ...) and single-quoted strings.
    """
    text = re.sub(r'([{,]\s*)([A-Za-z_$][A-Za-z0-9_$]*)\s*:', r'\1"\2":', text)
    text = re.sub(r"'([^']*)'", r'"\1"', text)
    return text


def _parse_json_part(raw):
    raw = raw.strip()
    if not raw:
        return {}
    try:
        return json.loads(_js_like_to_json(raw))
    except json.JSONDecodeError:
        raise QueryError("Unsupported query syntax. Check for matching braces/quotes.")


def _extract_balanced(text, open_idx):
    """Given text[open_idx] == '(', return (contents, index_after_matching_close)."""
    if open_idx >= len(text) or text[open_idx] != "(":
        raise QueryError("Unsupported query syntax. Expected '(' after the operation name.")
    depth = 0
    in_str = None
    i = open_idx
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"'):
                in_str = ch
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
                if depth == 0:
                    return text[open_idx + 1:i], i + 1
        i += 1
    raise QueryError("Unsupported query syntax. Unbalanced parentheses in query.")


def _split_top_level(text):
    """Split on commas that are not nested inside brackets/braces/quotes."""
    parts, depth, in_str, last = [], 0, None, 0
    i = 0
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"'):
                in_str = ch
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append(text[last:i])
                last = i + 1
        i += 1
    parts.append(text[last:])
    return [p.strip() for p in parts if p.strip() != ""]


def parse_custom_query(raw_text):
    """Returns (collection, operation, args_str, sort_str_or_None)."""
    text = raw_text.strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    if not text:
        raise QueryError("Please enter a query to execute.")

    m = re.match(r"^db\.([A-Za-z_][A-Za-z0-9_]*)\.", text)
    if not m:
        raise QueryError("Query must start with db.<collection>.<operation>(...).")
    collection = m.group(1)
    if collection not in ALLOWED_COLLECTIONS:
        raise QueryError(
            f"Collection '{collection}' is not allowed. Use 'events' or 'registrations'."
        )

    rest = text[m.end():]
    m2 = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\(", rest)
    if not m2:
        raise QueryError("Unsupported query syntax. Expected an operation like find({...}).")
    op = m2.group(1)
    if op not in ALLOWED_OPS:
        raise QueryError(
            f"Operation '{op}' is not supported. Allowed: find, countDocuments, aggregate, updateOne, deleteOne."
        )

    args_str, after_idx = _extract_balanced(rest, m2.end() - 1)

    sort_str = None
    chain = rest[after_idx:].strip()
    if chain:
        m3 = re.match(r"^\.sort\(", chain)
        if not m3:
            raise QueryError("Only .sort(...) chaining is supported after the main operation.")
        sort_str, sort_after_idx = _extract_balanced(chain, m3.end() - 1)
        trailing = chain[sort_after_idx:].strip()
        if trailing:
            raise QueryError("Unsupported extra chaining after .sort().")

    return collection, op, args_str, sort_str


def _validate_no_dangerous(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key.startswith("$") and key not in ALLOWED_DOLLAR_KEYS:
                raise QueryError(f"Operator '{key}' is not supported by this console.")
            _validate_no_dangerous(value)
    elif isinstance(obj, list):
        for item in obj:
            _validate_no_dangerous(item)


def sanitize_for_json(obj):
    """Make raw PyMongo results JSON-serializable (ObjectId/datetime -> strings)."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


# ---------- execution ----------

def execute_read_query(db, collection, op, args_str, sort_str):
    """Runs find / countDocuments / aggregate. Returns a plain result dict."""
    coll = db[collection]
    parts = _split_top_level(args_str)

    if op == "find":
        if len(parts) > 1:
            raise QueryError("find() supports only a single filter argument in this console.")
        filter_doc = _parse_json_part(parts[0]) if parts else {}
        _validate_no_dangerous(filter_doc)
        cursor = coll.find(filter_doc)
        if sort_str is not None:
            sort_doc = _parse_json_part(sort_str)
            _validate_no_dangerous(sort_doc)
            if not sort_doc:
                raise QueryError("sort({...}) requires at least one field.")
            cursor = cursor.sort(list(sort_doc.items()))
        docs = list(cursor.limit(MAX_RESULTS))
        return {"result_type": "find", "count": len(docs), "data": sanitize_for_json(docs)}

    if op == "countDocuments":
        if len(parts) > 1:
            raise QueryError("countDocuments() supports only a single filter argument.")
        filter_doc = _parse_json_part(parts[0]) if parts else {}
        _validate_no_dangerous(filter_doc)
        count = coll.count_documents(filter_doc)
        return {"result_type": "count", "count": count}

    if op == "aggregate":
        if sort_str is not None:
            raise QueryError(".sort() chaining is not supported after aggregate() - add a $sort stage instead.")
        if len(parts) != 1:
            raise QueryError("aggregate() expects a single pipeline array, e.g. aggregate([ ... ]).")
        pipeline = _parse_json_part(parts[0])
        if not isinstance(pipeline, list):
            raise QueryError("aggregate() argument must be an array of stages, e.g. [ { $match: {...} } ].")
        _validate_no_dangerous(pipeline)
        for stage in pipeline:
            if not isinstance(stage, dict) or len(stage) != 1:
                raise QueryError("Each aggregation stage must be a single-key object like { $match: {...} }.")
            stage_name = next(iter(stage))
            if stage_name not in ALLOWED_STAGES:
                raise QueryError(f"Aggregation stage '{stage_name}' is not supported.")
            if stage_name == "$lookup":
                frm = stage["$lookup"].get("from") if isinstance(stage["$lookup"], dict) else None
                if frm not in ALLOWED_COLLECTIONS:
                    raise QueryError(f"$lookup can only reference: {', '.join(sorted(ALLOWED_COLLECTIONS))}.")
        docs = list(coll.aggregate(pipeline))[:MAX_RESULTS]
        return {"result_type": "aggregate", "count": len(docs), "data": sanitize_for_json(docs)}

    raise QueryError(f"Operation '{op}' is not a read operation.")


def prepare_write_query(collection, op, args_str):
    """Parses+validates an updateOne/deleteOne call and returns (filter_doc, update_doc_or_None, summary)."""
    parts = _split_top_level(args_str)

    if op == "updateOne":
        if len(parts) != 2:
            raise QueryError("updateOne(filter, update) requires exactly two arguments.")
        filter_doc = _parse_json_part(parts[0])
        update_doc = _parse_json_part(parts[1])
        _validate_no_dangerous(filter_doc)
        _validate_no_dangerous(update_doc)
        if list(update_doc.keys()) != ["$set"]:
            raise QueryError(
                "For safety, updateOne() in this console only supports { $set: {...} } updates."
            )
        summary = (
            f"This will update the first '{collection}' document matching "
            f"{json.dumps(filter_doc)} - setting {json.dumps(update_doc['$set'])}."
        )
        return filter_doc, update_doc, summary

    if op == "deleteOne":
        if len(parts) != 1:
            raise QueryError("deleteOne(filter) requires exactly one argument.")
        filter_doc = _parse_json_part(parts[0])
        _validate_no_dangerous(filter_doc)
        summary = (
            f"This will permanently delete the first '{collection}' document matching "
            f"{json.dumps(filter_doc)}."
        )
        return filter_doc, None, summary

    raise QueryError(f"Operation '{op}' is not a write operation.")
