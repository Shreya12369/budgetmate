import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from database_test import init_db
from PIL import Image

init_db()

# authentication functions
def login(username, password):
    conn = sqlite3.connect('budget_app.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    result = c.fetchone()
    conn.close()
    return result

def signup(username, password):
    try:
        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# streamlit page setup
st.set_page_config(page_title="💸 Budget Mate", layout="centered")
st.image("logo.png", width=120)

# state initialization
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "monthly_budget" not in st.session_state:
    st.session_state.monthly_budget = 0.0

# login/sign up
if st.session_state.user is None:
    st.title("Budget Mate - Personal Expense Tracker")
    menu = ["Login", "Sign Up"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Login":
        st.subheader("Enter Login Details")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login(username, password)
            if user:
                st.session_state.user = user
                st.success(f"Welcome {username}!")
                st.rerun()
            else:
                st.error("Invalid credentials.")


    elif choice == "Sign Up":
        st.subheader("Create New Account")
        username = st.text_input("Username", key="signup_user")
        password = st.text_input("Password", type="password", key="signup_pass")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pass")
        if st.button("Sign Up"):
            if password != confirm_password:
                st.error("Passwords do not match. Please try again.")
            elif len(password) < 6:
                st.warning("Password should be at least 6 characters long.")
            elif signup(username, password):
                st.success("Account created. Go to Login.")
            else:
                st.error("Username already exists.")

# main app page
else:
    with st.sidebar:
        st.markdown("### 📂 Contents")
        menu_options = ["Dashboard", "Your Transactions", "Export & Reports", "Goals", "Logout"]
        selected = st.selectbox("", menu_options, key="menu_selection")
        st.session_state.page = selected

    current_month = datetime.now().strftime("%Y-%m")

    # dashboard page
    if st.session_state.page == "Dashboard":
        st.header("📊 Home")

        # budget
        if "edit_budget" not in st.session_state:
            st.session_state.edit_budget = False

        current_month = datetime.now().strftime("%Y-%m")
        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()
        c.execute("SELECT budget FROM budgets WHERE user_id=? AND month=?", (st.session_state.user[0], current_month))
        result = c.fetchone()

        if result:
            st.session_state.monthly_budget = result[0]
        else:
            c.execute("INSERT INTO budgets (user_id, month, budget) VALUES (?, ?, ?)",
                      (st.session_state.user[0], current_month, 0.0))
            conn.commit()
        conn.close()

        st.subheader("💰 Monthly Budget")

        if not st.session_state.edit_budget:
            st.info(f"Monthly Budget for {current_month}: `{st.session_state.monthly_budget:.2f}`")
            if st.button("✏️ Edit Budget"):
                st.session_state.edit_budget = True
        else:
            new_budget = st.number_input("Set New Monthly Budget", min_value=0.0, step=500.0, value=0.0, format="%.2f")
            if st.button("✅ Save Budget"):
                conn = sqlite3.connect('budget_app.db')
                c = conn.cursor()
                c.execute("UPDATE budgets SET budget=? WHERE user_id=? AND month=?",
                          (new_budget, st.session_state.user[0], current_month))
                conn.commit()
                conn.close()
                st.session_state.monthly_budget = new_budget
                st.session_state.edit_budget = False

        # add transactions
        st.subheader("➕ Add Transaction")
        with st.form("add_transaction", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                t_type = st.selectbox("Type", ["Income", "Expense"])
                category = st.selectbox(
                    "Category",
                    ["Salary", "Rent", "Food", "Transportation", "Fuel", "Groceries", "Utilities", "Entertainment", "Healthcare",
                     "Clothing", "Education", "Trip", "Gym", "Other"]
                )

                amount = st.number_input("Amount", min_value=0.0, step=500.0, value=0.0, format="%.2f")
            with col2:
                date = st.date_input("Date", value=datetime.today())
                note = st.text_input("Note")

            if st.form_submit_button("Add Transaction"):
                conn = sqlite3.connect('budget_app.db')
                c = conn.cursor()
                c.execute("INSERT INTO transactions (user_id, type, category, amount, date, note) VALUES (?, ?, ?, ?, ?, ?)",
                          (st.session_state.user[0], t_type, category, amount, date.strftime("%Y-%m-%d"), note))
                conn.commit()
                conn.close()
                st.success("Transaction added!")

    # transactions page
    elif st.session_state.page == "Your Transactions":
        st.header("📄 Your Transactions")

        # budget summary
        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()
        c.execute("SELECT amount FROM transactions WHERE user_id=? AND type='Expense'", (st.session_state.user[0],))
        expenses = [row[0] for row in c.fetchall()]
        conn.close()

        total_expense = sum(expenses)
        monthly_budget = st.session_state.monthly_budget
        remaining = monthly_budget - total_expense

        st.markdown(f"### 💸 Budget Summary")
        st.markdown(f"**Spent / Budget:** `{total_expense:,.2f}` / `{monthly_budget:,.2f}`")
        st.markdown(f"**Remaining:** `{remaining:,.2f}`")

        # Warning when close to budget
        if monthly_budget > 0 and total_expense >= 0.9 * monthly_budget and remaining > 0:
            st.warning("⚠️ You are close to reaching your monthly budget!")

        # Alert when budget is fully used
        if remaining <= 0:
            st.error("🚫 You have reached your monthly budget limit. Consider reviewing your expenses.")

        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()
        c.execute("SELECT id, type, category, amount, date, note FROM transactions WHERE user_id=?", (st.session_state.user[0],))
        rows = c.fetchall()
        conn.close()

        if rows:
            df = pd.DataFrame(rows, columns=["ID", "Type", "Category", "Amount", "Date", "Note"])
            st.dataframe(df, use_container_width=True)

            st.subheader("🗑️ Delete a Transaction")
            delete_id = st.number_input("Enter Transaction ID to Delete (Incase there was a mistake when inputting data.)", step=1, min_value=1)

            if "confirm_delete_id" not in st.session_state:
                st.session_state.confirm_delete_id = None

            if st.button("Delete Transaction"):
                st.session_state.confirm_delete_id = delete_id

            if st.session_state.confirm_delete_id:
                st.warning(f"Are you sure you want to delete transaction ID {st.session_state.confirm_delete_id}?")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✅ Yes, Delete"):
                        conn = sqlite3.connect('budget_app.db')
                        c = conn.cursor()
                        c.execute("DELETE FROM transactions WHERE id=? AND user_id=?",
                                  (st.session_state.confirm_delete_id, st.session_state.user[0]))
                        conn.commit()
                        conn.close()
                        st.success(f"Transaction ID {st.session_state.confirm_delete_id} deleted.")
                        st.session_state.confirm_delete_id = None
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel"):
                        st.info("Deletion cancelled.")
                        st.session_state.confirm_delete_id = None

    # export and report page
    elif st.session_state.page == "Export & Reports":
        st.header("📁 Export & Reports")

        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()
        c.execute("SELECT type, category, amount, date FROM transactions WHERE user_id=?", (st.session_state.user[0],))
        data = c.fetchall()
        conn.close()

        if data:
            df = pd.DataFrame(data, columns=["Type", "Category", "Amount", "Date"])
            df["Date"] = pd.to_datetime(df["Date"])

            st.download_button("📥 Download CSV", data=df.to_csv(index=False), file_name="transactions.csv")

            # filter only expenses
            expense_df = df[df["Type"] == "Expense"]

            if not expense_df.empty:
                #line chart
                st.subheader("📈 Expense Over Time (Line Chart)")
                date_summary = expense_df.groupby("Date")["Amount"].sum().sort_index()
                st.line_chart(date_summary)

                #pie chart
                st.subheader("📊 Expense Breakdown by Category (Pie Chart)")
                category_summary = expense_df.groupby("Category")["Amount"].sum()

                import matplotlib.pyplot as plt

                fig, ax = plt.subplots(figsize=(4, 4))  # Smaller pie chart
                category_summary.plot.pie(autopct='%1.1f%%', ylabel="", ax=ax)
                st.pyplot(fig)

            else:
                st.info("No expense data to show charts.")
        else:
            st.info("No transactions to display.")

    #goals
    elif st.session_state.page == "Goals":
        st.header("🎯 Your Savings Goals")

        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()

        # --- Initialize session states ---
        if "show_goals" not in st.session_state:
            st.session_state.show_goals = False
        if "goal_to_delete" not in st.session_state:
            st.session_state.goal_to_delete = None

        # --- ADD NEW GOAL ---
        st.subheader("➕ Add New Goal")
        with st.form("add_goal_form", clear_on_submit=True):
            goal_name = st.text_input("Goal Name")
            target_amount = st.number_input("Target Amount", min_value=0.0, step=500.0)
            saved_amount = st.number_input("Saved So Far", min_value=0.0, step=500.0)
            submit_goal = st.form_submit_button("Add Goal")
            if submit_goal:
                c.execute("INSERT INTO goals (user_id, name, target_amount, saved_amount) VALUES (?, ?, ?, ?)",
                          (st.session_state.user[0], goal_name, target_amount, saved_amount))
                conn.commit()
                st.success("Goal added!")
                st.rerun()

        # --- Toggle Show/Hide Button ---
        st.markdown("---")
        if st.button("📂 Show My Goals" if not st.session_state.show_goals else "📂 Hide My Goals"):
            st.session_state.show_goals = not st.session_state.show_goals

        # --- Show Goals ONLY if toggled ---
        if st.session_state.show_goals:
            st.subheader("🎯 My Goals")
            c.execute("SELECT id, name, target_amount, saved_amount FROM goals WHERE user_id=?",
                      (st.session_state.user[0],))
            goals = c.fetchall()

            if goals:
                for goal in goals:
                    goal_id, name, target, saved = goal
                    st.markdown(f"#### {name}")
                    progress = min(saved / target, 1.0) if target > 0 else 0.0
                    st.progress(progress)
                    st.markdown(f"**Saved:** Rs.{saved:,.2f} / Rs.{target:,.2f}")

                    if progress >= 1.0:
                        st.success("✅ Goal Completed! Woo-Hoo!!")
                    else:
                        st.info("⏳ In Progress")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button(f"Edit Goal - {goal_id}"):
                            st.session_state.editing_goal_id = goal_id
                            st.session_state.editing_goal_data = goal
                            st.rerun()
                    with col2:
                        if st.button(f"Delete Goal - {goal_id}"):
                            st.session_state.goal_to_delete = (goal_id, name)

                    # --- Delete Confirmation ---
                    if st.session_state.goal_to_delete and st.session_state.goal_to_delete[0] == goal_id:
                        st.warning(f"Are you sure you want to delete the goal: **{name}**?")
                        conf_col1, conf_col2 = st.columns([1, 1])
                        with conf_col1:
                            if st.button("✅ Yes, Delete"):
                                c.execute("DELETE FROM goals WHERE id=? AND user_id=?",
                                          (goal_id, st.session_state.user[0]))
                                conn.commit()
                                st.success(f"Goal '{name}' deleted.")
                                st.session_state.goal_to_delete = None
                                st.rerun()
                        with conf_col2:
                            if st.button("❌ Cancel"):
                                st.session_state.goal_to_delete = None
                                st.rerun()

                # --- Edit Goal Form ---
                if "editing_goal_id" in st.session_state:
                    edit_id = st.session_state.editing_goal_id
                    name, target, saved = st.session_state.editing_goal_data[1:]

                    st.markdown("---")
                    st.subheader("Edit Goal")

                    with st.form("edit_goal_form"):
                        new_name = st.text_input("Goal Name", value=name)
                        new_target = st.number_input("Target Amount", value=target, min_value=0.0, step=500.0)
                        new_saved = st.number_input("Saved So Far", value=saved, min_value=0.0, step=500.0)
                        if st.form_submit_button("Save Changes"):
                            c.execute(
                                "UPDATE goals SET name=?, target_amount=?, saved_amount=? WHERE id=? AND user_id=?",
                                (new_name, new_target, new_saved, edit_id, st.session_state.user[0]))
                            conn.commit()
                            st.success("Goal updated.")
                            del st.session_state.editing_goal_id
                            del st.session_state.editing_goal_data
                            st.rerun()
            else:
                st.info("🚫 No goals to display.")


    # logout page
    elif st.session_state.page == "Logout":
        st.header("🚪 Logout Confirmation")
        st.markdown("### Are you sure you want to logout?")

        import time

        if st.button("✅ Yes", type="primary", key="confirm_logout"):
            st.success("Logging you out... Please wait.")
            time.sleep(1.5)
            st.session_state.clear()
            st.session_state.user = None
            st.session_state.page = "Login"
            st.rerun()



