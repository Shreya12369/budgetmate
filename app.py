import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from matplotlib.animation import Animation
import random
from database import init_db
from PIL import Image
import base64
import matplotlib.pyplot as plt
from calendar import monthrange

def set_background_image(image_file):
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
init_db()

# authentication functions
def login(username, password):
    conn = sqlite3.connect('budget_app.db')
    c = conn.cursor()
    c.execute("SELECT id, username, email FROM users WHERE username=? AND password=?", (username, password))
    result = c.fetchone()
    conn.close()
    return result

def is_username_taken(username):
    conn = sqlite3.connect('budget_app.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    return result is not None

def signup(username, password, email):
    try:
        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, email, currency) VALUES (?, ?, ?, ?)", (username, password, email, "₹"))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# streamlit page setup
st.set_page_config(page_title="💸 Budget Mate", layout="centered")
st.image("logo.png", width=120)

set_background_image("background.png")

st.markdown("""
    <style>
    /* Make all general text black (excluding sidebar and buttons) */
    .block-container, .stMarkdown, .stText, .stHeader, .stSubheader, .stCaption,
    .stBody, .stDataFrame, .stDataTable, .stExpanderHeader,
    .stRadio > label, .stCheckbox > label, .stSelectbox > label,
    .stNumberInput > label, .stDateInput > label, .stMultiSelect > label,
    label, p, h1, h2, h3, h4, h5, h6, span {
        color: black !important;
    }

    /* Keep button text white (for all buttons including submit, login etc.) */
    button, button * {
        color: white !important;
    }

    /* Prevent sidebar text override */
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# state initialization
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "monthly_budget" not in st.session_state:
    st.session_state.monthly_budget = 0.0

conn = sqlite3.connect('budget_app.db')
c = conn.cursor()
c.execute("PRAGMA table_info(users);")
columns = [col[1] for col in c.fetchall()]
if 'email' not in columns:
    c.execute("ALTER TABLE users ADD COLUMN email TEXT;")
if 'currency' not in columns:
    c.execute("ALTER TABLE users ADD COLUMN currency TEXT DEFAULT '₹';")
conn.commit()
conn.close()

# login/sign up
if st.session_state.user is None:
    st.title("Budget Mate - Personal Expense Tracker")
    menu = ["Login", "Sign Up"]
    choice = st.sidebar.selectbox("Menu", menu, index=menu.index(st.session_state.get("auth_menu", "Login")))
    st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

    from streamlit_lottie import st_lottie
    import json

    # load animation
    def load_lottie_file(filepath):
        with open(filepath, "r") as f:
            return json.load(f)

    login_animation = load_lottie_file("Animation - 1749802035577.json")

    # display the animation
    st_lottie(login_animation, height=250, key="login")

    if choice == "Login":
        st.subheader("Enter Login Details")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            user = login(username, password)
            if user:
                st.session_state.user = user
                conn = sqlite3.connect('budget_app.db')
                c = conn.cursor()
                c.execute("SELECT currency FROM users WHERE id=?", (user[0],))
                result = c.fetchone()
                conn.close()
                if result and result[0]:
                    st.session_state.currency = result[0]
                else:
                    st.session_state.currency = "₹"
                st.session_state.page = "Dashboard"
                st.rerun()
            else:
                st.error("Invalid Username or Password.")

        #forgot password section (login page only)
        if st.button("Forgot Password?"):
            st.session_state.page = "ForgotPassword"
            st.session_state.auth_menu = "Login"
            st.rerun()

    # initialize page state before widget rendering
    if "signup_success" not in st.session_state:
        st.session_state.signup_success = False

    # forgot password page
    if st.session_state.page == "ForgotPassword":
        st.subheader("Reset Your Password")

        reset_email = st.text_input("Enter your registered email")
        if st.button("Verify Email"):
            conn = sqlite3.connect('budget_app.db')
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE email=?", (reset_email,))
            result = c.fetchone()
            conn.close()

            if result:
                st.session_state.reset_user_id = result[0]
                st.session_state.page = "ResetPassword"
                st.rerun()
            else:
                st.error("❌ No account found with that email.")

    # set new password page
    if st.session_state.page == "ResetPassword":
        st.subheader("🔒 Set a New Password")

        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if st.button("Update Password"):
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 6:
                st.warning("Password should be at least 6 characters long.")
            else:
                conn = sqlite3.connect("budget_app.db")
                c = conn.cursor()
                c.execute("UPDATE users SET password=? WHERE id=?", (new_password, st.session_state.reset_user_id))
                conn.commit()
                conn.close()
                st.success("✅ Your password has been updated.")
                st.session_state.page = "Login"
                st.rerun()

    # sign up page
    if choice == "Sign Up":
        st.subheader("Create New Account")
        username = st.text_input("Username", key="signup_user")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pass")

        if st.button("Sign Up"):
            if password != confirm_password:
                st.error("Passwords do not match. Please try again.")
            elif len(password) < 6:
                st.warning("Password should be at least 6 characters long.")
            elif is_username_taken(username):
                st.error("Username already exists. Please choose another one.")
            elif signup(username, password, email):
                st.success("Account created successfully!")

# main app page
elif st.session_state.user:
    with st.sidebar:
        st.markdown("### 📂 Contents")
        menu_options = ["Dashboard", "Your Transactions", "Export & Reports", "Goals", "Savings","Saving Advice", "Your Profile", "Logout"]
        selected = st.selectbox("", menu_options, key="menu_selection")
        st.session_state.page = selected

    current_month = datetime.now().strftime("%Y-%m")
    user_id = st.session_state.user[0]

    # dashboard page
    if st.session_state.page == "Dashboard":
        st.header("📊 Home")

        #currency change
        currency_options = ["₹", "Rs", "$", "£", "€", "¥", "₩", "₽", "₺", "₪", "₫", "₴", "฿", "₦", "₱", "₵", "R", "د.إ"]
        selected_currency = st.selectbox(
            "Choose your currency", currency_options, index=currency_options.index(st.session_state.currency)
        )
        if selected_currency != st.session_state.currency:
            conn = sqlite3.connect('budget_app.db')
            c = conn.cursor()
            c.execute("UPDATE users SET currency=? WHERE id=?", (selected_currency, st.session_state.user[0]))
            conn.commit()
            conn.close()
            st.session_state.currency = selected_currency
            st.success("✅ Currency updated successfully!")

        # budget
        if "edit_budget" not in st.session_state:
            st.session_state.edit_budget = False

        today = datetime.today()
        current_month = today.strftime("%Y-%m")
        user_id = st.session_state.user[0]

        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()

        # check if there's a budget for the current month
        c.execute("SELECT budget FROM budgets WHERE user_id=? AND month=?", (user_id, current_month))
        result = c.fetchone()

        if result:
            st.session_state.monthly_budget = result[0]
        else:
            c.execute("INSERT INTO budgets (user_id, month, budget) VALUES (?, ?, ?)",
                      (user_id, current_month, 0.0))
            conn.commit()
            st.session_state.monthly_budget = 0.0

        conn.close()

        st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

        st.subheader("💰 Monthly Budget")
        if not st.session_state.edit_budget:
            st.info(f"Monthly Budget for {current_month}: {st.session_state.currency} `{st.session_state.monthly_budget:.2f}`")
            if st.button("✏️ Edit Budget"):
                st.session_state.edit_budget = True

            st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

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
                    ["Salary", "Pocket Money", "Rent", "Food", "Transportation", "Fuel", "Groceries", "Utilities", "Entertainment", "Healthcare",
                     "Clothing", "Education", "Trip", "Gym", "Loans", "Other"]
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

        money_tips = [
            "Track Every Expense - Keep an eye on small purchases – they add up quickly.",
            "Set Monthly Budget Goals - Stick to your monthly budget to avoid overspending.",
            "Cook More, Eat Out Less - Home-cooked meals save a lot more money than takeout.",
            "Unsubscribe from Unused Subscriptions - Cancel streaming, software, or service subscriptions you barely use.",
            "Follow the 24-Hour Rule - Wait 24 hours before making non-essential purchases to avoid impulse buying.",
            "Use Cashback and Rewards Apps - Take advantage of offers that give cash back on spending.",
            "Save Before You Spend - Move a portion of your income into savings as soon as you receive it.",
            "Avoid Buy Now, Pay Later Plans - These encourage spending money you don’t yet have.",
            "Set Clear Financial Goals - Having goals like travel or emergency funds makes saving more motivating.",
            "Shop with a List and Stick to It - Lists reduce impulse purchases and keep spending focused.",
            "Review Your Budget Weekly - Weekly check-ins help you adjust before it’s too late.",
            "Use Public Transport - It’s often cheaper than driving daily.",
            "Declutter & Sell Unused Items - Turn your clutter into cash with a garage sale or online marketplaces.",
            "Turn Off Lights & Save Electricity - Small utility savings pile up over time.",
            "Avoid ATM Fees - Use your bank’s ATMs to avoid unnecessary charges.",
            "Pack Snacks for Outings - Avoid costly impulse snacks by packing your own.",
            "Buy Generic brands - Store brands are usually just as good and cheaper.",
            "Limit Online Shopping - Avoid browsing apps when bored - it leads to overspending.",
            "Meal Prep on Sundays - Saves time and stops weekday takeout temptation.",
            "Avoid Late Fees - Set up auto-pay or reminders for bills.",
            "Buy Only What you can Afford - Avoid credit purchases unless its an emergency.",
            "Wait for Big Tech Updates - New versions drop proces on older models.",
            "Use Student or ID Discounts - Always ask if a discount is available.",
            "Cancel Free Trials on Time - Set reminders before they start charging.",
            "Use Price Comparison Tools - Use Apps like Honey or Google Shopping to help find deals.",
            "Set a Fun Budget - Dont restrict joy, just assign a limit."
        ]
        
        # generate a consistent tip of the day
        today = datetime.now().date()
        random.seed(str(today))
        tip_of_the_day = random.choice(money_tips)

        st.markdown(f"💡 **Tip of the Day:** {tip_of_the_day}")


        st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)
        st.subheader("📉 Set Monthly Spending Limit")

        # display existing limits
        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()

        with st.form("set_spending_limit"):
            category_limit = st.selectbox("Select Category", [
                "Rent", "Food", "Transportation", "Fuel", "Groceries", "Utilities", "Entertainment", "Healthcare",
                "Clothing", "Education", "Trip", "Gym", "Other"
            ])
            limit_amount = st.number_input("Spending Limit Amount", min_value=0.0, step=1000.0)
            submit_limit = st.form_submit_button("Save Limit")
            if submit_limit:
                c.execute("SELECT 1 FROM spending_limits WHERE user_id=? AND month=? AND category=?",
                          (user_id, current_month, category_limit))
                exists = c.fetchone()
                if exists:
                    c.execute("UPDATE spending_limits SET limit_amount=? WHERE user_id=? AND month=? AND category=?",
                              (limit_amount, user_id, current_month, category_limit))
                    st.success("Spending limit updated.")
                else:
                    c.execute(
                        "INSERT INTO spending_limits (user_id, month, category, limit_amount) VALUES (?, ?, ?, ?)",
                        (user_id, current_month, category_limit, limit_amount))
                    st.success("Spending limit set.")
                conn.commit()
                st.rerun()

    #transactions page
    elif st.session_state.page == "Your Transactions":
        st.header("🧾 Your Transactions")
        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()
        user_id = st.session_state.user[0]

        # fetch all transactions
        c.execute("SELECT id, type, category, amount, date, note FROM transactions WHERE user_id=?", (user_id,))
        rows = c.fetchall()
        conn.close()

        if rows:
            df = pd.DataFrame(rows, columns=["ID", "Type", "Category", "Amount", "Date", "Note"])
            df["Date"] = pd.to_datetime(df["Date"])
            df["Month"] = df["Date"].dt.to_period("M").astype(str)
            df["Date"] = df["Date"].dt.date

            st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

            # month selection
            st.subheader("- - - Select Month - - -")
            available_months = sorted(df["Month"].unique(), reverse=True)
            selected_month = st.selectbox("Choose a month to view transactions", available_months)
            selected_year_month = selected_month  # "YYYY-MM"

            # filter transactions
            filtered_df = df[df["Month"] == selected_month]

            # budget summary
            conn = sqlite3.connect('budget_app.db')
            c = conn.cursor()
            c.execute("SELECT budget FROM budgets WHERE user_id=? AND month=?",
                      (user_id, selected_year_month))
            result = c.fetchone()
            conn.close()

            monthly_budget = result[0] if result else 0.0
            total_expense = filtered_df[filtered_df["Type"] == "Expense"]["Amount"].sum()
            remaining = monthly_budget - total_expense

            st.markdown(f"### Budget Summary for {selected_month}")
            st.markdown(f"**Spent / Budget:** {st.session_state.currency} `{total_expense:,.2f}` / {st.session_state.currency} `{monthly_budget:,.2f}`")
            st.markdown(f"**Remaining:** {st.session_state.currency} `{remaining:,.2f}`")

            if monthly_budget > 0 and remaining <= 0.2 * monthly_budget and remaining > 0:
                st.warning("⚠️ Warning: You're down to the last 20% of your monthly budget! Consider slowing down")
            elif remaining == 0:
                st.error("🚫 You have reached your monthly budget limit. Consider reviewing your expenses.")
            elif remaining < 0:
                st.error("🛑 Easy there, you are currently spending over your monthly budget.")

            # congratulatory message for past months
            try:
                selected_month_date = datetime.strptime(selected_month, "%Y-%m")
                today = datetime.today()
                if selected_month_date.year < today.year or (
                        selected_month_date.year == today.year and selected_month_date.month < today.month
                ):
                    st.success(
                        f"🎉 Congratulations! You’ve saved {remaining:,.2f} from your budget for {selected_month}."
                    )

            except Exception:
                pass

            # monthly spending limits - table
            st.markdown("### 📊 Monthly Spending Limits")
            conn = sqlite3.connect('budget_app.db')
            c = conn.cursor()
            c.execute("SELECT category, limit_amount FROM spending_limits WHERE user_id=? AND month=?",
                      (user_id, selected_year_month))
            limit_data = c.fetchall()

            if limit_data:
                limit_display = []

                for category, limit in limit_data:
                    c.execute("""SELECT SUM(amount) FROM transactions 
                                 WHERE user_id=? AND type='Expense' AND category=? 
                                 AND strftime('%Y-%m', date)=?""",
                              (user_id, category, selected_year_month))
                    spent = c.fetchone()[0] or 0.0

                    # format as string with possible red warning text
                    if spent > limit:
                        spent_limit = f"🔴 {st.session_state.currency} {spent:,.0f} / {st.session_state.currency} {limit:,.0f} 🔴 (Overspending)"
                    # format for in limit
                    elif spent == limit:
                        spent_limit = f"✅ {st.session_state.currency} {spent:,.0f}/ {st.session_state.currency} {limit:,.0f} ✅ (Reached Limit)"
                    else:
                        spent_limit = f"{st.session_state.currency} {spent:,.0f}/ {st.session_state.currency} {limit:.0f} - (In Limit)"

                    limit_display.append({
                        "Category": category,
                        "Spent / Limit": spent_limit
                    })

                df_limits = pd.DataFrame(limit_display)
                st.dataframe(df_limits, use_container_width=True)

            else:
                st.info("No spending limits set for this month.")

            conn.close()

            st.subheader("📄 Transactions")
            # Show filtered transactions table
            st.dataframe(filtered_df.drop(columns="Month"), use_container_width=True)

            st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

            # Delete transaction
            st.subheader("🗑️ Delete a Transaction")
            delete_id = st.number_input(
                "Enter Transaction ID to Delete (Incase there was a mistake during data insertion)", step=1, min_value=1)

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
                                  (st.session_state.confirm_delete_id, user_id))
                        conn.commit()
                        conn.close()
                        st.success(f"Transaction ID {st.session_state.confirm_delete_id} deleted.")
                        st.session_state.confirm_delete_id = None
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel"):
                        st.info("Deletion cancelled.")
                        st.session_state.confirm_delete_id = None
        else:
            st.info("No transactions to display.")

    # export and report page
    elif st.session_state.page == "Export & Reports":
        st.header("📁 Export & Reports")

        # get all transactions
        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()
        c.execute("SELECT type, category, amount, date FROM transactions WHERE user_id=?", (st.session_state.user[0],))
        data = c.fetchall()
        conn.close()

        if data:
            df = pd.DataFrame(data, columns=["Type", "Category", "Amount", "Date"])
            df["Date"] = pd.to_datetime(df["Date"])
            df["Month"] = df["Date"].dt.to_period("M").astype(str)

            # month selector
            st.subheader("📆 Select Month")
            available_months = sorted(df["Month"].unique(), reverse=True)
            selected_month = st.selectbox("Choose a month to view reports", available_months)

            # filter data for selected month
            filtered_df = df[df["Month"] == selected_month]

            # download button for current month
            st.download_button(
                "📥 Download CSV for Selected Month",
                data=filtered_df.to_csv(index=False),
                file_name=f"transactions_{selected_month}.csv"
            )
            # show charts if any expense exists for that month
            expense_df = filtered_df[filtered_df["Type"] == "Expense"]
            if not expense_df.empty:
                # line Chart
                st.subheader("📈 Expense Over Time (Line Chart)")
                date_summary = expense_df.groupby("Date")["Amount"].sum().sort_index()
                st.line_chart(date_summary)

                # pie Chart
                st.subheader("📊 Expense Breakdown by Category (Pie Chart)")
                category_summary = expense_df.groupby("Category")["Amount"].sum()
                #plots
                fig, ax = plt.subplots(figsize=(4, 4))
                category_summary.plot.pie(autopct='%1.1f%%', ylabel="", ax=ax)
                st.pyplot(fig)
            else:
                st.info("No expense data to show charts for the selected month.")
        else:
            st.info("No transactions to display.")

    # view goals, create and manage savings goal
    elif st.session_state.page == "Goals":
        st.header("🎯 Your Savings Goals")

        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()

        # initialize session states
        if "show_goals" not in st.session_state:
            st.session_state.show_goals = False
        if "goal_to_delete" not in st.session_state:
            st.session_state.goal_to_delete = None

        # add new goal
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

        # toggle show/hide button
        st.markdown("---")
        if st.button("📂 Show My Goals" if not st.session_state.show_goals else "📂 Hide My Goals"):
            st.session_state.show_goals = not st.session_state.show_goals

        # show goals only if toggled
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
                    st.markdown(f"Saved: {st.session_state.currency} {saved:,.2f} /{st.session_state.currency} {target:,.2f}")

                    if progress >= 1.0:
                        st.success("✅ Goal Completed! Woo-Hoo!!🏆")
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

                    # delete confirmation message
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

                # editing goal form
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

    elif st.session_state.page == "Savings":
        st.header("💰 Savings Overview")
        conn = sqlite3.connect('budget_app.db')
        c = conn.cursor()
        # getting current dates
        today = datetime.today()
        current_day = today.day
        current_month = today.strftime("%m")
        current_year = today.strftime("%Y")

        st.subheader("➕ Add Manual Saving")
        with st.form("manual_saving"):
            manual_amount = st.number_input("Amount", min_value=0.0, step=500.0)
            submitted = st.form_submit_button("Save")
            if submitted:
                c.execute("INSERT INTO savings (user_id, month, year, amount, source) VALUES (?, ?, ?, ?, 'manual')",
                          (st.session_state.user[0], current_month, current_year, manual_amount))
                conn.commit()
                st.success(f"{st.session_state.currency}{manual_amount:.2f} added as manual saving.")
                st.rerun()

        st.subheader("Savings Table")
        c.execute(
            "SELECT id, month || '/' || year AS Period, amount, source FROM savings WHERE user_id=? ORDER BY id DESC",
            (st.session_state.user[0],)
        )
        savings_data = c.fetchall()
        if savings_data:
            df = pd.DataFrame(savings_data, columns=["ID", "Period", "Amount", "Source"])
            st.dataframe(df, use_container_width=True)
            total_saved = df["Amount"].sum()
            st.success(f"💵 Total Savings: You've saved {st.session_state.currency} {total_saved:,.2f}")
        else:
            st.info("No savings yet.")
        st.markdown("---")
        st.subheader("🗑️ Delete a Saving Entry")
        c.execute(
            "SELECT id, month || '/' || year AS Period, amount, source FROM savings WHERE user_id=? ORDER BY id DESC",
            (st.session_state.user[0],)
        )
        savings_records = c.fetchall()
        if savings_records:
            df_del = pd.DataFrame(savings_records, columns=["ID", "Period", "Amount", "Source"])
            selected_id = st.selectbox("Select the Saving entry ID to delete:", df_del["ID"].astype(str))
            selected_row = df_del[df_del["ID"].astype(str) == selected_id].iloc[0]
            st.warning(
                f"You are about to delete the entry for **{selected_row['Period']}** - {selected_row['Amount']:.2f} ({selected_row['Source']})."
            )
            col1, col2 = st.columns(2)
            with col1:

                if st.button("✅ Yes, Delete"):
                    c.execute("DELETE FROM savings WHERE id=? AND user_id=?", (selected_id, st.session_state.user[0]))
                    conn.commit()
                    st.success(f"Saving ID {selected_id} deleted.")
                    st.rerun()
            with col2:
                if st.button("❌ Cancel"):
                    st.info("Deletion cancelled.")

        conn.close()


    elif st.session_state.page == "Saving Advice":
        st.header("💡 Money Tips & Advice")
        st.markdown(
            "Explore a collection of tips to save money, build better financial habits, and plan ahead. Tips are grouped by category for easy reading!")

        st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

        # budgeting basics
        with st.expander("🧠 Budgeting Basics"):
            st.markdown("Track Every Expense - Monitor all your spending, no matter how small. This awareness helps identify unnecessary expenditures and areas to cut back.")
            st.markdown("Set Monthly Budget Goals - Define clear financial goals each month to guide your spending and savings decisions.")
            st.markdown("Use the 50/30/20 Rule - Allocate 50% of your income to needs, 30% to wants, and 20% to savings. This balanced approach ensures financial stability.")
            st.markdown("Review Your Budget Weekly - Regularly assess your budget to stay on track and make necessary adjustments promptly.")
            st.markdown("Automate Savings - Set up automatic transfers to your savings account to ensure consistent saving habits.")
            st.markdown("Create an Emergency Fund - Aim to save 3-6 months' worth of expenses to cover unexpected financial setbacks.")
            st.markdown("Avoid Lifestyle Inflation - As your income increases, resist the urge to increase your spending proportionally.")
            st.markdown("Use Budgeting Apps - Leverage technology to track expenses, set goals, and receive financial insights.")
            st.markdown("Set Realistic Financial Goals - Establish achievable short-term and long-term financial objectives to stay motivated.")
            st.markdown("Prioritize High-Interest Debt - Focus on paying off debts with the highest interest rates to reduce overall financial burden.")

        # food and dining
        with st.expander("🍽️ Food & Dining"):
            st.markdown("Plan Meals Weekly - Organize your meals in advance to avoid impulsive dining and reduce food waste.")
            st.markdown("Cook at Home - Preparing meals at home is generally more cost-effective and healthier than eating out.")
            st.markdown("Buy in Bulk - Purchase non-perishable items in bulk to save money over time. (eg: rice, pasta)")
            st.markdown("Use Grocery Lists - Stick to a shopping list to prevent unnecessary purchases.")
            st.markdown("Limit Dining Out - Reserve eating out for special occasions to control food expenses.")
            st.markdown("Utilize Coupons and Discounts - Take advantage of available deals to lower grocery bills.")
            st.markdown("Avoid Shopping When Hungry - Shopping on an empty stomach can lead to impulse buying.")
            st.markdown("Prepare Lunches - Bringing lunch to work or school can significantly reduce daily expenses.")
            st.markdown("Grow Your Own Herbs - Cultivating herbs at home can save money and enhance meal flavors.")
            st.markdown("Limit Specialty Coffees - Reducing purchases of specialty drinks can lead to substantial savings over time.")

        # transportation
        with st.expander("🚗 Transportation"):
            st.markdown("Use Public Transit - Opt for public transportation to save on fuel and maintenance costs.")
            st.markdown("Carpool When Possible - Sharing rides reduces transportation expenses and environmental impact.")
            st.markdown("Maintain Your Vehicle - Regular maintenance prevents costly repairs and extends vehicle lifespan.")
            st.markdown("Compare Insurance Rates - Shop around for insurance to ensure you're getting the best deal.")
            st.markdown("Drive Efficiently - Adopt fuel-efficient driving habits to reduce gas consumption.")
            st.markdown("Walk or Bike for Short Trips - Choosing to walk or bike saves money and promotes health.")
            st.markdown("Plan Errands Strategically - Combine errands into one trip to save time and fuel.")
            st.markdown("Use Fuel Rewards Programs - Enroll in programs that offer discounts or cashback on fuel purchases.")
            st.markdown("Avoid Premium Fuel Unless Necessary - Use the fuel grade recommended for your vehicle to avoid unnecessary costs.")
            st.markdown("Regularly Check Tire Pressure - Properly inflated tires improve fuel efficiency and safety.")

        # housing and utilities
        with st.expander("🏠 Housing & Utilities"):
            st.markdown("Refinance Your Mortgage - Explore refinancing options to secure lower interest rates.")
            st.markdown("Conduct Energy Audits - Identify areas to improve energy efficiency and reduce utility bills.")
            st.markdown("Install Programmable Thermostats - Automate temperature settings to save on heating and cooling costs.")
            st.markdown("Seal Leaks and Insulate - Proper insulation reduces energy loss and lowers bills.")
            st.markdown("Use Energy-Efficient Appliances - Invest in appliances that consume less energy to save in the long run.")
            st.markdown("Limit Water Usage - Implement water-saving practices to reduce utility expenses.")
            st.markdown("Negotiate Rent - Discuss rent terms with your landlord to potentially lower monthly payments.")
            st.markdown("Bundle Services - Combine internet, phone, and TV services for potential discounts.")
            st.markdown("Perform Regular Maintenance - Upkeep prevents costly repairs and maintains property value.")
            st.markdown("Rent Out Extra Space - Consider renting unused rooms to generate additional income.")

        # shopping and entertainment
        with st.expander("🛍️ Shopping & Entertainment"):
            st.markdown("Set a Shopping Budget - Allocate a specific amount for shopping to prevent overspending.")
            st.markdown("Wait Before Making Big Purchases - Implement a waiting period to determine if the purchase is necessary.")
            st.markdown("Buy Generic Brands - Generic products often offer similar quality at a lower price.")
            st.markdown("Use Cashback Apps - Earn rewards on purchases through cashback applications.")
            st.markdown("Limit Subscription Services - Regularly review and cancel unused subscriptions.")
            st.markdown("Attend Free Events - Explore community events that offer entertainment at no cost.")
            st.markdown("Borrow Instead of Buying - For infrequent needs, consider borrowing items instead of purchasing. (eg: Books)")
            st.markdown("Shop Off-Season - Purchase seasonal items during off-peak times for discounts.")
            st.markdown("Use Loyalty Programs - Join programs that offer discounts or rewards for frequent shoppers.")
            st.markdown("Avoid Impulse Buys - Stick to your shopping list to prevent unnecessary expenditures.")

        # debt management
        with st.expander("💳 Debt Management"):
            st.markdown("Create a Debt Repayment Plan - Outline a strategy to systematically pay off debts.")
            st.markdown("Pay More Than the Minimum - Contribute extra to debt payments to reduce interest over time.")
            st.markdown("Consolidate Debts - Combine multiple debts into one for easier management and potential lower rates.")
            st.markdown("Avoid New Debt - Limit taking on additional debt while paying off existing obligations.")
            st.markdown("Use Windfalls Wisely - Apply unexpected income, like bonuses or tax refunds, toward debt reduction.")
            st.markdown("Negotiate Interest Rates - Contact creditors to discuss lowering interest rates.")
            st.markdown("Understand Loan Terms - Fully comprehend the terms and conditions of any loan agreements.")
            st.markdown("Avoid Payday Loans - These often come with high-interest rates and fees; seek alternatives.")
            st.markdown("Monitor Credit Reports - Regularly check credit reports for accuracy and to track progress.")
            st.markdown("Seek Professional Advice - Consult financial advisors for personalized debt management strategies.")

        # healthcare and insurance
        with st.expander("🏥 Healthcare & Insurance"):
            st.markdown("Review Insurance Policies - Ensure coverage meets current needs and adjust as necessary.")
            st.markdown("Use Preventive Care - Regular check-ups can prevent costly medical issues later.")
            st.markdown("Shop for Insurance Annually - Compare plans each year to find the best rates and coverage.")
            st.markdown("Utilize Health Savings Accounts (HSAs) - HSAs offer tax advantages for medical expenses.")
            st.markdown("Understand Coverage Details - Know what services are covered to avoid unexpected bills.")
            st.markdown("Negotiate Medical Bills - Discuss payment plans or discounts with healthcare providers.")
            st.markdown("Use In-Network Providers - Staying within your insurance network reduces out-of-pocket costs.")
            st.markdown("Maintain a Healthy Lifestyle - Healthy habits can reduce medical expenses over time.")
            st.markdown("Use Generic Prescriptions - When possible, request generic medications from your doctor or pharmacist. They are usually just as effective but significantly cheaper than brand-name versions. (please keep in mind to check if you have any allergies what so ever)")
            st.markdown("Bundle Insurance Plans - Combining car, health, or home insurance policies under the same provider can result in lower premiums and discounts.")

        # education and learning
        with st.expander("📚 Education & Learning"):
            st.markdown("Apply for Scholarships & Grants - Never assume you're not eligible — apply for as many scholarships and grants as possible to reduce tuition burden.")
            st.markdown("Buy Used Textbooks - Purchase or rent second-hand books from online marketplaces, bookstores, or classmates to save hundreds each term.")
            st.markdown("Use Student Discounts - Take full advantage of your student ID. Many retailers, transport services, and software platforms offer discounted rates.")
            st.markdown("Learn Financial Literacy - Read books, follow finance blogs, or enroll in free courses to better manage your money.")
            st.markdown("Track Educational Expenses - Create a separate budget for tuition, supplies, and fees to avoid last-minute financial strain.")
            st.markdown("Use University Resources - Instead of paying for gym memberships or software, check if your university offers these for free.")
            st.markdown("Plan for Student Loan Repayment Early - Understand your loan type, interest, and repayment options before graduation to prevent default.")

        # work and side income
        with st.expander("💼 Work & Side Income"):
            st.markdown("Start a Side Hustle - Turn a hobby or skill (like tutoring, freelance writing, or graphic design) into a source of extra income.")
            st.markdown("Track Freelance Income Separately - If you're doing side gigs, keep this income distinct and set aside money for taxes.")
            st.markdown("Update Your Resume Regularly - A strong, current CV increases your chances of finding higher-paying jobs or part-time work.")
            st.markdown("Negotiate Your Salary - Don’t be afraid to ask for what you’re worth, especially if you’ve gained experience or added value.")
            st.markdown("Invest in Skills with ROI - Enroll in short courses that could help you land better-paying roles or gigs.")
            st.markdown("Use Job-Related Tax Deductions - If you're self-employed or freelancing, you may be eligible for deductions on work-related expenses.")

        # technology and digital spending
        with st.expander("🌐 Technology & Digital Spending"):
            st.markdown("Limit In-App Purchases - Disable in-app purchases or set restrictions to avoid unintentional spending.")
            st.markdown("Use Free Alternatives - Many paid software or apps have free versions or open-source alternatives with similar features.")
            st.markdown("Audit Digital Subscriptions Monthly - Review your subscriptions (music, TV, cloud storage) and cancel those you don’t actively use.")
            st.markdown("Use Wi-Fi Instead of Data - When possible, connect to Wi-Fi networks to limit mobile data charges.")
            st.markdown("Unplug Devices - Even idle devices consume power. Unplug chargers and appliances when not in use to save on electricity.")
            st.markdown("Set App Store Budgets - Platforms like Google Play or Apple allow spending limits to avoid digital overspending.")

        # habits and mindset
        with st.expander("📦 Habits & Mindset"):
            st.markdown("Set Financial Boundaries with Friends - Be honest about your budget when social plans come up. Suggest low-cost alternatives.")
            st.markdown("Celebrate Small Wins - Reward yourself (in budget-friendly ways) when you hit small savings or debt goals to stay motivated.")
            st.markdown("Practice Gratitude Over Materialism - Shift your mindset to value experiences or stability over unnecessary items.")
            st.markdown("Have No-Spend Days or Weeks - Designate time where you avoid all non-essential spending. It builds discipline and saves money.")
            st.markdown("Reflect Before Each Purchase - Ask yourself: “Do I need this? Will I still value it in a week?” before hitting “buy.”")
            st.markdown("Visualize Your Goals - Keeping a vision board or goal tracker can reinforce your purpose for saving.")
            st.markdown("Avoid Emotional Spending - Recognize triggers that lead to spending when bored, stressed, or sad, and find healthy alternatives.")
            st.markdown("Automate Bill Payments - Avoid late fees by setting up automatic payments for your fixed expenses.")
            st.markdown("Perform Monthly Budget Reviews - Spend 15–30 minutes each month reviewing your income, spending, and goals. Adjust as needed.")
            st.markdown("Always Spend Less Than You Earn - The golden rule of personal finance: If you consistently live below your means, wealth will follow.")
        st.markdown("---")
        st.success("Use these tips regularly to build strong financial habits!")

    # profile page
    elif st.session_state.page == "Your Profile":
        st.header("⚙️ Account")
        st.markdown("You can view and update your account details below.")
        st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)
        conn = sqlite3.connect("budget_app.db")
        c = conn.cursor()

        user_id = st.session_state.user[0]
        c.execute("SELECT username, email, password FROM users WHERE id=?", (user_id,))
        user_data = c.fetchone()
        conn.close()

        if user_data:
            username, email, password = user_data

            # username
            with st.expander(f"Username - {username}"):
                new_username = st.text_input("New Username", value=username, key="change_username")
                if st.button("Save Username"):
                    if new_username != username:
                        conn = sqlite3.connect("budget_app.db")
                        c = conn.cursor()
                        # check if username already exists and it's not this user's
                        c.execute("SELECT id FROM users WHERE username=? AND id != ?", (new_username, user_id))
                        if c.fetchone():
                            st.error("❌ This username is already taken. Please choose another.")
                        else:
                            c.execute("UPDATE users SET username=? WHERE id=?", (new_username, user_id))
                            conn.commit()
                            conn.close()
                            st.success("✅ Username updated successfully!")
                            st.session_state.user = (user_id, new_username, password)
                            st.rerun()
                    else:
                        st.info("No changes made.")

            # email
            with st.expander(f"Email - {email}"):
                new_email = st.text_input("New Email", value=email, key="change_email")
                if st.button("Save Email"):
                    if new_email != email:
                        conn = sqlite3.connect("budget_app.db")
                        c = conn.cursor()
                        # check if email already exists and it's not this user's
                        c.execute("SELECT id FROM users WHERE email=? AND id != ?", (new_email, user_id))
                        if c.fetchone():
                            st.error("❌ This email is already in use. Please use a different one.")
                        else:
                            c.execute("UPDATE users SET email=? WHERE id=?", (new_email, user_id))
                            conn.commit()
                            conn.close()
                            st.success("✅ Email updated successfully!")
                            st.rerun()
                    else:
                        st.info("No changes made.")
            # password
            with st.expander(f"Password - {'*' * len(password)}"):
                new_password = st.text_input("New Password", type="password", key="change_password")
                confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_change_password")

                if st.button("Save Password"):
                    if new_password != confirm_password:
                        st.error("❌ Passwords do not match.")
                    elif len(new_password) < 6:
                        st.warning("⚠️ Password should be at least 6 characters long.")
                    elif new_password == password:
                        st.info("You entered the same password as before.")
                    else:
                        conn = sqlite3.connect("budget_app.db")
                        c = conn.cursor()
                        c.execute("UPDATE users SET password=? WHERE id=?", (new_password, user_id))
                        conn.commit()
                        conn.close()
                        st.success("✅ Password updated successfully!")
                        st.rerun()

            st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

    # logout page
    elif st.session_state.page == "Logout":
        st.header("🚪 Logout Confirmation")
        st.markdown("Are you sure you want to logout?")

        import time
        if st.button("Yes", type="primary", key="confirm_logout"):
            st.success("Logging you out... Please wait.")
            time.sleep(1.5)
            st.session_state.clear()
            st.session_state.user = None
            st.session_state.page = "Login"
            st.rerun()
