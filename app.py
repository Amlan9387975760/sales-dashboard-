from flask import Flask, render_template, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
import json, datetime, os

app = Flask(__name__)

HEADERS        = ["ID", "Company Name", "Demo Start Date", "Challenge Type", "Status", "Sales Rep", "Notes"]
CHALLENGE_TYPES = ["Race", "Streak", "Marathon", "Weekly Custom", "Journey"]
STATUS_OPTIONS  = ["Demo", "Live", "Not Converted"]

if os.environ.get("SERVICE_ACCOUNT_JSON"):
    SERVICE_ACCOUNT_INFO = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])
else:
    with open("service_account.json") as f:
        SERVICE_ACCOUNT_INFO = json.load(f)

SHEET_ID = os.environ.get("SHEET_ID", "1ZPYxiNnJ6xCACg86YorR3899wIoyUb3SUG5MvNf7yPo")

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=scopes)
    client = gspread.authorize(creds)
    ws     = client.open_by_key(SHEET_ID).sheet1
    if not ws.get_all_values() or ws.cell(1,1).value != "ID":
        ws.clear()
        ws.append_row(HEADERS)
    return ws

def get_all_clients():
    ws   = get_sheet()
    rows = ws.get_all_records()
    return rows, ws

@app.route("/")
def index():
    return render_template("index.html",
        challenge_types=CHALLENGE_TYPES,
        status_options=STATUS_OPTIONS)

@app.route("/api/clients")
def api_clients():
    clients, _ = get_all_clients()
    return jsonify(clients)

@app.route("/api/add", methods=["POST"])
def api_add():
    data = request.json
    clients, ws = get_all_clients()
    new_id = max((int(c["ID"]) for c in clients if str(c["ID"]).isdigit()), default=0) + 1
    ws.append_row([
        new_id,
        data.get("company",""),
        data.get("demo_date",""),
        data.get("challenge",""),
        data.get("status",""),
        data.get("sales_rep",""),
        data.get("notes",""),
    ])
    return jsonify({"success": True})

@app.route("/api/update", methods=["POST"])
def api_update():
    data       = request.json
    client_id  = str(data.get("id"))
    new_status = data.get("status")
    reason     = data.get("reason","")
    _, ws      = get_all_clients()
    ids        = ws.col_values(1)
    for i, v in enumerate(ids):
        if str(v) == client_id:
            row_num    = i + 1
            status_col = HEADERS.index("Status") + 1
            notes_col  = HEADERS.index("Notes") + 1
            old_status = ws.cell(row_num, status_col).value
            ws.update_cell(row_num, status_col, new_status)
            if reason:
                old_notes = ws.cell(row_num, notes_col).value or ""
                entry     = f"[{datetime.date.today()}] {old_status}→{new_status}: {reason}"
                ws.update_cell(row_num, notes_col, f"{old_notes} | {entry}".strip(" |"))
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Client not found"})

@app.route("/api/delete", methods=["POST"])
def api_delete():
    client_id = str(request.json.get("id"))
    _, ws     = get_all_clients()
    ids       = ws.col_values(1)
    for i, v in enumerate(ids):
        if str(v) == client_id:
            ws.delete_rows(i + 1)
            return jsonify({"success": True})
    return jsonify({"success": False})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5050)
