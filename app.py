# app.py — Speza: Smart Expense Tracker (Flask version)

from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
from pathlib import Path
import plotly.express as px
import json, os
# --------------------------------
# App Initialization
# --------------------------------
app = Flask(__name__)
app.secret_key = "speza_secret_key"  # required for flash messages

# --------------------------------
# File Paths
# --------------------------------
DATA_PATH = Path("data/expenses.csv")

# --------------------------------
# Ensure Data File Exists
# --------------------------------
if not DATA_PATH.exists() or DATA_PATH.stat().st_size == 0:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(columns=["Date", "Type", "Category", "Amount", "Note"])
    df.to_csv(DATA_PATH, index=False)



# --------------------------------
# Helper Functions
# --------------------------------
def load_data():
    """Load CSV data into a pandas DataFrame, handle empty file case."""
    try:
        return pd.read_csv(DATA_PATH)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["Date", "Type", "Category", "Amount", "Note"])


def save_data(date, type_, category, amount, note):
    """Append a new transaction to the CSV file."""
    df = load_data()
    new_entry = pd.DataFrame(
        [[date, type_, category, amount, note]],
        columns=["Date", "Type", "Category", "Amount", "Note"]
    )
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(DATA_PATH, index=False)


# --------------------------------
# Routes
# --------------------------------

@app.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    """Dashboard with data visualization and mood analysis."""
    df = load_data()
    if df.empty:
        flash("No transactions found. Add some income or expenses to see your dashboard.")
        return redirect(url_for("add_expense"))

    total_income = df.loc[df["Type"] == "Income", "Amount"].sum()
    total_expense = df.loc[df["Type"] == "Expense", "Amount"].sum()
    balance = total_income - total_expense

    # Mood logic
    if total_expense > total_income:
        mood = {"status": "bad", "text": "🔴 Caution! Expenses exceed income."}
    elif abs(total_income - total_expense) < 2000:
        mood = {"status": "neutral", "text": "🟡 You're spending close to your income."}
    else:
        mood = {"status": "good", "text": "🟢 Great! You're saving money."}

    # Pie chart (Expense Breakdown)
    exp_df = df[df["Type"] == "Expense"]
    if not exp_df.empty:
        fig = px.pie(
            exp_df,
            names="Category",
            values="Amount",
            title="Expense Breakdown",
            color_discrete_sequence=["#00C896", "#1E90FF", "#FFB84D", "#9B5DE5", "#FF6B6B"]
        )

        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            margin=dict(t=40, b=80)   # optional but improves spacing
        )

        chart = fig.to_html(full_html=False, include_plotlyjs="cdn")
    else:
        chart = "<p>No expenses yet to display.</p>"



    # --- Monthly Income vs Expense Analysis ---
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Month"] = df["Date"].dt.strftime("%b %Y")

    monthly_summary = (
        df.groupby(["Month", "Type"])["Amount"].sum().unstack(fill_value=0).reset_index()
    )

    monthly_labels = monthly_summary["Month"].tolist()
    monthly_income = monthly_summary.get("Income", pd.Series()).tolist()
    monthly_expense = monthly_summary.get("Expense", pd.Series()).tolist()




    return render_template(
        "dashboard.html",
        chart=chart,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        mood=mood,
        monthly_labels=json.dumps(monthly_labels),
        monthly_income=json.dumps(monthly_income),
        monthly_expense=json.dumps(monthly_expense))







@app.route("/add", methods=["GET", "POST"])
def add_expense():
    """Form page for adding income or expense."""
    if request.method == "POST":
        date = request.form["date"]
        type_ = request.form["type"]
        category = request.form["category"]
        amount = request.form["amount"]
        note = request.form["note"]

        try:
            amount = float(amount)
            save_data(date, type_, category, amount, note)
            flash(f"{type_} added successfully!")
            return redirect(url_for("dashboard"))
        except ValueError:
            flash("Invalid amount. Please enter a valid number.")
            return redirect(url_for("add_expense"))

    return render_template("add_transaction.html")


# Transactions Page
@app.route("/transactions")
def transactions():
    df = load_data()
    df.reset_index(drop=True, inplace=True)

    if df.empty:
        flash("No transactions available.")
        return redirect(url_for("add_expense"))
    return render_template("transactions.html", transactions=df.to_dict(orient="records"))


# Delete a transaction
@app.route("/delete/<int:index>", methods=["POST"])
def delete_transaction(index):
    df = load_data()
    df.reset_index(drop=True, inplace=True)

    if 0 <= index < len(df):
        df = df.drop(index)
        df.to_csv(DATA_PATH, index=False)
        flash("Transaction deleted successfully!")
    return redirect(url_for("transactions"))


# Edit a transaction
@app.route("/edit/<int:index>", methods=["POST"])
def edit_transaction(index):
    df = load_data()
    df.reset_index(drop=True, inplace=True)

    if 0 <= index < len(df):
        df.loc[index, "Date"] = request.form.get("date")
        df.loc[index, "Type"] = request.form.get("type")
        df.loc[index, "Category"] = request.form.get("category")
        df.loc[index, "Amount"] = float(request.form.get("amount"))
        df.loc[index, "Note"] = request.form.get("note")
        df.to_csv(DATA_PATH, index=False)
        flash("Transaction updated successfully!")
    return redirect(url_for("transactions"))



@app.route("/settings")
def settings():
    """Settings page."""
    return render_template("settings.html")


@app.route("/clear_data", methods=["POST"])
def clear_data():
    """Clears all stored transaction data."""
    try:
        df = pd.DataFrame(columns=["Date", "Type", "Category", "Amount", "Note"])
        df.to_csv(DATA_PATH, index=False)
        return ("", 204)  # success, no content
    except Exception as e:
        print("Error clearing data:", e)
        return ("Error", 500)


# --------------------------------
# Run the App
# --------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

