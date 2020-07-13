import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import re
import numpy as np

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

symbols_dict = {"EUR": "Euro",
                "JPY": "Japanese yen",
                "BGN": "Bulgarian lev",
                "CZK": "Czech koruna",
                "DKK": "Danish krone",
                "GBP": "Pound sterling",
                "HUF": "Hungarian forint",
                "PLN": "Polish zloty",
                "RON": "Romanian leu",
                "SEK": "Swedish krona",
                "CHF": "Swiss franc",
                "ISK": "Icelandic krona",
                "NOK": "Norwegian krone",
                "HRK": "Croatian kuna",
                "RUB": "Russian rouble",
                "TRY": "Turkish lira",
                "AUD": "Australian dollar",
                "BRL": "Brazilian real",
                "CAD": "Canadian dollar",
                "CNY": "Chinese yuan renminbi",
                "HKD": "Hong Kong dollar",
                "IDR": "Indonesian rupiah",
                "ILS": "Israeli shekel",
                "INR": "Indian rupee",
                "KRW": "South Korean won",
                "MXN": "Mexican peso",
                "MYR": "Malaysian ringgit",
                "NZD": "New Zealand dollar",
                "PHP": "Philippine peso",
                "SGD": "Singapore dollar",
                "THB": "Thai baht",
                "ZAR": "South African rand",
				}

@app.route("/")
def home():
    try:
        if session.user_id:
            return redirect("/portfolio")

    except (AttributeError):
        return render_template("home.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "GET":
        return render_template("contact.html")

    else:
        flash(u'Message sent!', 'alert-success')
        return render_template("success.html")

@app.route("/portfolio")
@login_required
def index():
    """Show portfolio of stocks"""
    id = session["user_id"]

    # query database for relevant data
    rows = db.execute("SELECT symbol, currency, SUM(amount) AS amount FROM transactions WHERE user_id = :id GROUP BY symbol ORDER BY symbol", id=id)
    cash = db.execute("SELECT cash from users WHERE id = :id", id=id)
    cash = cash[0]["cash"]
    total = cash

    # removing rows where net sum of currency equals zero
    rows = [row for row in rows if not (row['amount'] == 0)]

    # removing deposit transactions (currency is dollar)
    rows = [row for row in rows if not (row['symbol'] == "USD")]

    # iterating to get value of all currencies and portfolio networth
    for row in rows:
        row["rate"] = (lookup(row["symbol"]))["rate"]
        row["dollar_price"] = (row["amount"] / row["rate"] )
        total += row["dollar_price"]
        row["dollar_price"] = usd(row["dollar_price"])
        amount = row["amount"]
        row["amount"] =  f"{amount:,.2f} " + row["symbol"]

    # getting symbols of currencies user has in portfolio
    symbols = db.execute("SELECT symbol, SUM(amount) AS amount FROM transactions WHERE user_id = :id GROUP BY symbol", id = session["user_id"])

    # removing rows where net sum of currency equals zero
    symbols = [symbol for symbol in symbols if not (symbol['amount'] == 0)]

    # removing deposit transactions (currency is dollar)
    symbols = [symbol for symbol in symbols if not (symbol['symbol'] == "USD")]

    return render_template("index.html", rows=rows, cash=usd(cash), total=usd(total), symbols=symbols)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy currency"""
    if request.method == "GET":
        currencies = sorted(list(symbols_dict.keys()))
        cash = db.execute("SELECT cash from users WHERE id = :id", id=session["user_id"])
        cash = cash[0]["cash"]
        return render_template("buy.html", currencies=currencies, cash=cash)

    else:
        # extracting symbol and currency data from form
        symbol = (request.form.get("symbol")).upper()
        amount = int(request.form.get("amount"))

        # getting the current exchange rate and handling invalid symbols
        try:
            quote = lookup(symbol)
            rate = quote["rate"]
            currency_amount = rate * amount
            currency_amount = float(np.round(currency_amount, 2))

        except TypeError:
            return apology("Invalid symbol")

        # getting user cash balance from database
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        cash = rows[0]["cash"]

        # if user balace is not enough to buy currency
        if amount > cash:
            flash(u'Insufficient Funds!', 'alert-danger')
            return render_template("buy.html", currencies=currencies)

        # if balance is sufficient
        else:
            balance = cash - amount
            now = datetime.now()
            date = now.strftime("%Y-%m-%d %H:%M:%S")

            # recording current transaction in database
            db.execute("INSERT INTO transactions (user_id,symbol,currency,amount,rate,dollar_price,date,type) VALUES(:user_id,:symbol,:currency,:currency_amount,:rate,:amount,:date,:type)",
                    user_id=session["user_id"],symbol=symbol,currency=symbols_dict[symbol],currency_amount=currency_amount,rate=rate,amount=amount,date=date,type="Buy")

            # updating user new cash balance in database
            db.execute("UPDATE users SET cash = :balance WHERE id = :id",balance=balance, id=session["user_id"])

            # sending flash message and redirecting
            flash(u'Bought!', 'alert-primary')
            return redirect("/portfolio")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # getting user transaction history from database
    rows = db.execute("SELECT symbol, currency, amount, rate, date, type FROM transactions WHERE user_id = :id ORDER BY date DESC", id=session["user_id"])

    # formatting the prices in usd
    for row in rows:
        amount = row["amount"]
        row["amount"] =  str(amount) + " " + row["symbol"]

    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash(u'Please input username!', 'alert-danger')
            return redirect("/")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash(u'Please provide password!', 'alert-danger')
            return redirect("/")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash(u'Invalid username and/or password!', 'alert-danger')
            return redirect("/")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to portfolio page
        return redirect("/portfolio")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("home.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/rates", methods=["GET", "POST"])
@login_required
def rates():
    """Get current rate."""
    if request.method == "GET":
        currencies = sorted(list(symbols_dict.keys()))
        return render_template("rates.html", currencies=currencies)
    else:
        # extracting symbol from form
        symbol = (request.form.get("symbol")).upper()

        # getting current price of company shares
        quote = lookup(symbol)

        # if the symbol doesnt return any quote
        if not quote:
            flash(u'Invalid symbol!', 'alert-danger')
            return render_template("quote.html")

        # symbol returns current share price
        else:
            rate = quote["rate"]
            return render_template("quoted.html", rate=rate, symbol=symbol)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        # extracting data from form
        username = request.form.get("username")

        # checking if username already exists in database
        rows = db.execute("SELECT username FROM users WHERE username = :username", username=username)

        # if username already exists
        if rows:
            flash(u'Username already exists!', 'alert-danger')
            return redirect("/")

        # if username not in database
        else:
            password = request.form.get("password")

            # check if password countaing at least a number and a letter
            valid = bool(re.match('^(?=.*[0-9]$)(?=.*[a-zA-Z])', password))

            # check if password up to 7 characters
            min_len = 7
            if (len(password) < min_len):
                valid = False

            # if password is not valid, alert user
            if not valid:
                flash(u'Password must be at least 7 characters and must contain a letter and a number!', 'alert-danger')
                return redirect("/")

            # if password is valid add hash password to database
            flash(u'Registration succesful. You can now login!', 'alert-success')
            password = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash) VALUES(:username, :password)", username=username, password=password)
            return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":

        # getting symbols of currencies user has in portfolio
        rows = db.execute("SELECT symbol, SUM(amount) AS amount FROM transactions WHERE user_id = :id GROUP BY symbol", id = session["user_id"])

        # removing rows where net sum of currency equals zero
        rows = [row for row in rows if not (row['amount'] == 0)]

        # removing deposit transactions (currency is dollar)
        rows = [row for row in rows if not (row['symbol'] == "USD")]

        return render_template("sell.html", rows=rows)

    else:
        # extracting data from form
        symbol = (request.form.get("symbol")).upper()
        amount = float(request.form.get("amount"))

        # checking database for amount of the currency currently owned by user
        own_amount = db.execute("SELECT SUM(amount) AS amount FROM transactions WHERE symbol = :symbol AND user_id = :id", symbol=symbol, id=session["user_id"])
        own_amount = own_amount[0]["amount"]

        # if amount to be sold is greater than amount in portfolio
        if amount > own_amount:
            flash(u'You do not have up to that amount in your portfolio!', 'alert-danger')
            return render_template("sell.html", rows=rows)

        # if shares owned is sufficient
        else:
            # check current exchange rate of currency
            quote = lookup(symbol)
            rate = quote["rate"]

            # getting users current cash balance
            cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
            cash = cash[0]["cash"]

            # adding sold currency amount to users cash balance
            dollar = float(np.round(amount / rate, 2))
            balance = cash + dollar

            # recording current transaction in database
            now = datetime.now()
            date = now.strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO transactions (user_id,symbol,currency,amount,rate,dollar_price,date,type) VALUES(:user_id,:symbol,:currency,:amount,:rate,:dollar,:date,:type)",
                    user_id=session["user_id"],symbol=symbol,currency=symbols_dict[symbol],amount=-(amount),rate=rate,dollar=dollar,date=date,type="Sell")

            # updating users cash balance in database
            db.execute("UPDATE users SET cash = :balance WHERE id = :id",balance=balance, id=session["user_id"])

            # sending flash message and redirecting
            flash(u'Sold!', 'alert-warning')
            return redirect("/portfolio")


@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():
    """To change password"""

    if request.method == "GET":
        return render_template("changepassword.html")

    else:
        # extracting data from form
        old_password = request.form.get("old_password")

        # extracting user password from database
        rows = db.execute("SELECT hash FROM users WHERE id = :id", id=session["user_id"])

        # checking if user old password is correct
        if not (check_password_hash(rows[0]["hash"], old_password)):
            flash(u'Incorrect Password!', 'alert-danger')
            return redirect("/changepassword")

        else:
            new_password = request.form.get("new_password")

            # checking if old password and new password are the same
            if (old_password == new_password):
                flash(u'New password must be different!', 'alert-danger')
                return redirect("/changepassword")
            else:
                # check if new password contains at least a number and a letter
                valid = bool(re.match('^(?=.*[0-9]$)(?=.*[a-zA-Z])', new_password))

                # check if password up to 7 characters
                min_len = 7
                if (len(new_password) < min_len):
                    valid = False

                # if password is not valid, alert user
                if not valid:
                    flash(u'Password must be at least 7 characters and must contain a letter and a number!', 'alert-danger')
                    return redirect("/register")

                # updating database with new password
                password = generate_password_hash(new_password)
                db.execute("UPDATE users SET hash = :password WHERE id = :id",password=password, id=session["user_id"])

                # send flash message and redirect
                flash(u'Password succesfully updated!', 'alert-success')
                return redirect("/changepassword")


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """To deposit funds"""
    if request.method == "GET":
        return render_template("deposit.html")

    else:
        # extracting data from form
        amount = request.form.get("amount")

        # changing amount to int neglecting the dollar sign
        amount = int(amount[1:])

        # extracting user balance from database
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        balance = rows[0]["cash"]

         # recording current transaction in database
        now = datetime.now()
        date = now.strftime("%Y-%m-%d %H:%M:%S")
        db.execute("INSERT INTO transactions (user_id,symbol,currency,amount,rate,dollar_price,date,type) VALUES(:user_id,:symbol,:currency,:currency_amount,:rate,:amount,:date,:type)",
                user_id=session["user_id"],symbol="USD",currency="US Dollars",currency_amount=amount,rate="NULL",amount=amount,date=date,type="Deposit")

        # calculating new balance
        new_balance = balance + amount

        # updating user new cash balance in database
        db.execute("UPDATE users SET cash = :new_balance WHERE id = :id",new_balance=new_balance, id=session["user_id"])

        # sending flash message and redirecting
        message = "Deposit received Old balance: " + str(usd(balance)) + " New balance: " + str(usd(new_balance))
        flash(message, 'alert-success')
        return redirect("/portfolio")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
