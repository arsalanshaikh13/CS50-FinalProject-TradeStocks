import os
import re
from datetime import datetime
import json
from application import db
from application import app
from application.dbmodel import User, User_Profile, Transaction
from flask import  flash, url_for, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import BadRequest, default_exceptions, HTTPException, InternalServerError
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()
from application.helpers import apology, login_required, lookup, usd, is_blank

UPLOAD_FOLDER = 'application/static/assets/img/'
ALLOWED_EXTENSIONS = set([ 'png', 'jpg', 'jpeg', 'gif'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_ID = session['user_id']
    #Query the database to get the current state of the stocks in the portfolio to display on the dashboard
    transactions_db = Transaction.query.with_entities(Transaction.symbol, Transaction.company,Transaction.share_price, db.func.sum(Transaction.share_qty).label('sum_shares'), db.func.sum(Transaction.total_cost).label('sum_cost')).filter_by(user_id = session['user_id']).group_by('symbol').having(db.func.sum(Transaction.share_qty) > 0).all()

    if transactions_db == []:
        transactions_db = []
        transactions_db.append({'symbol': 'NA', 'company': 'Not Applicable   ', 'share_price': 0, 'sum_shares': 0, 'sum_cost': 0})
    else:
        transactions_db = transactions_db

    # in order to find the real time value of the stocks_price and shares_owned worth first create a separate list to store the latest value and latest price of the stocks
    total_shares_value = 0
    holdings = []
    invested_value = 0
    for row in transactions_db:
        quote_value = lookup(row['symbol'])
        if quote_value is None:
            latest_price = 0
        else:
            latest_price = quote_value['price']
        invested_value += row['sum_cost']

        latest_invest_value = row['sum_shares'] * latest_price

        # only printing the 2 words in the company name
        company = row['company'].split()[:2]
        company = company[0] + ' ' + company[1]
        profit = latest_invest_value - row['sum_cost']
        holdings.append({'symbol': row['symbol'], 'company': company, 'share_price': latest_price, 'shares_owned': row['sum_shares'],'invested_value': row['sum_cost'], 'latest_value': latest_invest_value, 'profit': profit})
        total_shares_value += latest_invest_value


    difference = float(round((total_shares_value - invested_value), 2))
    if invested_value != 0:
        percent = float(round(((difference/invested_value)*100), 2))
    else:
        percent = 0


    #sort holdings list in descending order
    hold = sorted(holdings,key=lambda e:e['latest_value'],reverse=True)
    hold1 = sorted(holdings,key=lambda e:e['shares_owned'],reverse=True)
    hold2 = sorted(holdings, key=lambda e:e['profit'], reverse=True)

    # Query to get current cash balance
    Curr_cash = User.query.with_entities(User.cash, User.name, User.email).filter_by(id=user_ID).first()

    curr_cash = float(round(Curr_cash.cash,2))
    total_investment_value = total_shares_value + curr_cash


    #data for chart
    qty = []
    cost = []
    company = []

    # to get latest value  for chart data use holdings
    for row in holdings:
        qty.append(row['shares_owned'])
        cost.append(float(round(row['latest_value'], 2)))
        company.append(row['company'])


    # # Query to get the profile picture of the user
    profile_details = User_Profile.query.with_entities(User_Profile.profile_picture).filter_by(user_id=session['user_id']).first()

    return render_template('index.html', hold=hold, hold1=hold1, email=Curr_cash.email, \
                            invested_value=invested_value, hold2=hold2,\
                            qty=json.dumps(qty), total_qty=json.dumps(sum(qty)), company=json.dumps(company), diff=abs(difference), \
                            cost=json.dumps(cost), total_cost=json.dumps(sum(cost)), holdings=holdings, image=profile_details.profile_picture, percent=percent, \
                            total_shares_value=total_shares_value, total_value=total_investment_value,\
                            curr_cash = curr_cash, name=Curr_cash.name,company_symbol=holdings)


@app.route('/register', methods=['GET','POST'])
def register():

    # user enter the app through filling the form using POST method
    if request.method == 'POST':
        #store the details inserted by the user in the variables
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email') #design an automatic mail sender on confirm registration
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        #if required fields are blank then apologize and and ask user to enter the details in the required field
        result_check = is_blank(name, 'name') or is_blank(username, 'username') or is_blank(email, 'email') or is_blank(password, 'password') or is_blank(confirmation, 'confirmation')
        if result_check:
            return result_check


        #choosing only id because it is been index so faster lookup and sufficient enough to check the condition
        check_user = User.query.with_entities(User.id).filter_by(username=username).first()
        if check_user is not None:
            flash('username already exists. Please provide unique username ')
            return render_template('register.html')

        check_email = User.query.with_entities(User.id).filter_by(email=email).first()
        if check_email is not None:
            flash('email id already exists. Please provide unique email id ')
            return render_template('register.html')


        #checking criteria for password strength server/backend side
        # password pattern regex
        reg_regular_expression = str("^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,20}$")
        pat_pattern = re.compile(reg_regular_expression)

        mat_match = pat_pattern.findall(password)

        #validating conditions
        if mat_match == []:
            flash("Password doesn't pass requirments")
            return render_template('register.html')


        #for checking criteria for password strength client/front_end side follow Khasa -passwordchecker.js

        # generate password hash
        hash_password = generate_password_hash(password)
        if password != confirmation:
            flash("passwords don't match")
            return render_template('register.html')

        # insert the details of the user into database
        try:
            insert_user = User(name=name, username=username, email=email, password_hash=hash_password)
            db.session.add(insert_user)
            flash('Registered Successfully')
        except Exception as e:
            print(e)
            flash(f"Error {e} in transaction")
            return render_template('register.html')

        db.session.commit()

        # add the user details in the User_Profile table
        try:
            new_profile = User_Profile(user_id=insert_user.id, fullname=insert_user.name)
            db.session.add(new_profile)
        except Exception as e:
            print(e)
            flash(f"Error {e} in transaction")
            return render_template('register.html')

        db.session.commit()

        # return the user to the login page
        return redirect(url_for('login'))

    else:
        return render_template('register.html')

@app.route('/login', methods= ['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        #if required fields are blank then apologize and and ask user to enter the details in the required field
        result_check = is_blank(username, 'username')  or is_blank(password, 'password')
        if result_check:
            return result_check


        #check if email already exist in the database
        check_user = User.query.with_entities(User.id, User.password_hash).filter_by(username=username).first()

        # if entered email address doesn't match the email addresses in the database apologize to user and ask to provide correct registered email address
        if check_user is None:
            flash('username does not exists. Please provide registered username')
            return render_template("index.html")

        # check the password provided by user matches the hashed password in the database
        if not check_password_hash(check_user.password_hash, password):
            flash('Invalid email/password')
            return render_template("index.html")

        #establish session id using the user id of the user
        session['user_id'] = check_user.id

        flash("Login successful")
        return redirect(url_for('index'))
    else:
        return render_template('index.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/quote", methods=[ "POST"])
@login_required
def quote():
    """Get stock quote."""

    #get the symbol inputed by user
    symboll = request.form.get("symbol")

    #check if user has input symbol in the form
    if not symboll:
        flash("Please enter symbol")
        return redirect('/')

    #lookup/find the quote for the symbol using lookup function
    quote_price = lookup(symboll)

    #check if user has input proper/correct symbol for searching its price
    if not quote_price:
        flash("Please insert correct symbol")
        return redirect('/')

    #send dicitonary as input for jinja code in quoted html
    return render_template('quoted.html', stock_spec = {'name': quote_price['name'], 'price': quote_price['price'], 'symbol': quote_price['symbol']}, usd_function = usd)

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # query the transaction table to get all the transactions stored in the database
    transactions_db = Transaction.query.filter_by(user_id=session['user_id']).all()
    user_details = User.query.with_entities(User.name, User.email).filter_by(id=session['user_id']).first()
    profile_details = User_Profile.query.with_entities(User_Profile.profile_picture, User_Profile.fullname).filter_by(user_id=session['user_id']).first()

    #make a list of distinct companies in order to show in sell modal
    company = []
    for row in transactions_db:
        # ensure that we are adding only distince symbols and also not adding cash symbol
        if row.symbol != 'CASH':
            company.append({'symbol':row.symbol, 'company': row.company})

    # https://stackoverflow.com/questions/11092511/list-of-unique-dictionaries
    company1 = list({row['symbol']:row for row in company}.values())

    return render_template('history.html', transactions_db=transactions_db,company_symbol=company1, image=profile_details.profile_picture, name=user_details.name, email=user_details.email)

@app.route("/buy", methods=["POST"])
@login_required
def buy():
    """Buy shares """

    symbol = request.form.get("symbol").upper()
    #this method takes care of blank and float as well as non-numeric character
    try:
        share_qty = int(request.form.get("shares"))
    except:
        flash("shares must be integers")
        return redirect('/')

    #ensure symbol and share_qty is not blank
    result_check = is_blank(symbol, 'symbol') or is_blank(share_qty, 'share_qty')
    if result_check:
        return result_check

    if share_qty < 0:
        flash("please enter positive share qty")
        return redirect('/')

    user_ID = session['user_id']

    #find the current cash balance of user
    current_cash = User.query.with_entities(User.cash).filter_by(id=user_ID).first()

    #find the transaction cost based on quote from lookup
    quote_price = lookup(symbol)
    if quote_price == None:
        flash("Please enter correct symbol")
        return redirect('/')

    #calculate transaction cost and check if it is less than cash available
    transaction_cost = quote_price['price'] * share_qty
    if current_cash.cash < transaction_cost:
        flash("You have Insufficient Balance")
        return redirect('/')
    # update the cash in users table
    update_cash = current_cash.cash - transaction_cost

    #insert the transaction details into transactions table
    try:
        update_trans = User.query.filter_by(id=user_ID).update(dict(cash=update_cash))
        new_transaction = Transaction(user_id=user_ID, symbol=symbol, company=quote_price['name'], \
                                        share_price=quote_price['price'],share_qty=share_qty,\
                                        total_cost=transaction_cost, transaction_type='BUY')
        db.session.add(new_transaction)
        flash("Shares have been Successfully Purchased!!")
    except Exception  as e:
        print(e)
        flash(f"Error {e} in transaction")
        return redirect('/')

    db.session.commit()
    return redirect('/')

@app.route('/sell', methods=[ 'POST'])
def sell():
    ''' Sell shares  '''
    try:
        symbol = request.form['symbol'].upper()
    except BadRequest as e:
        print(e)
        symbol = None
    try:
        share_qty = int(request.form.get("shares"))
    except:
        flash("shares must be positive numbers")
        return redirect('/')

    #ensure symbol and share_qty is not blank
    result_check = is_blank(symbol, 'symbol') or is_blank(share_qty, 'share_qty')
    if result_check:
        return result_check


    if share_qty < 0:
        flash("please enter positive share quantity")
        return redirect('/')

    user_ID = session['user_id']

    #find the transaction cost based on quote from lookup
    quote_price = lookup(symbol)
    if quote_price == None:
        flash("Please enter correct symbol")
        return redirect('/')

    # check for sufficient shares
    share_owned = Transaction.query.with_entities(Transaction.symbol, db.func.sum(Transaction.share_qty).label('sum_shares')).filter_by(user_id=user_ID).group_by('symbol').having(db.func.sum(Transaction.share_qty)>0).all()
    holding_sym = []
    for row in share_owned:
        holding_sym.append(row['symbol'])
        if row['symbol'] == quote_price['symbol']:
            if row['sum_shares'] < share_qty:
                flash("you have insufficient shares")
                return redirect('/')

    if symbol not in holding_sym:
        flash("symbol does not exist in your portfolio")
        return redirect('/')

    transaction_cost = quote_price['price'] * share_qty

    #find the current cash balance of user
    current_cash = User.query.with_entities(User.cash).filter_by(id=user_ID).first()

    # update the cash in users table
    update_cash = current_cash.cash + transaction_cost

    #insert the transaction details into transactions table
    try:
        update_trans = User.query.filter_by(id=user_ID).update(dict(cash=update_cash))
        new_transaction = Transaction(user_id=user_ID, symbol=symbol, company=quote_price['name'], \
                                        share_price=quote_price['price'],share_qty=share_qty * (-1),\
                                        total_cost=transaction_cost * (-1), transaction_type='SELL')
        db.session.add(new_transaction)
        flash("Shares have been successfully Sold!!")
    except Exception  as e:
        print(e)
        flash(f"Error {e} in transaction")
        return redirect('/')

    db.session.commit()
    return redirect('/')

@app.route('/money', methods=['POST'])
@login_required
def money():
    add = request.form.get('add')
    redeem = request.form.get('redeem')

    # find the current cash
    current_cash = User.query.with_entities(User.cash).filter_by(id=session['user_id']).first()
    current_cash = current_cash.cash
    # add the amount to current cash
    if add:
        try:
            add = int(add)
            update_cash = current_cash + add
            cash = add
            type = 'ADD CASH'
        except Exception as e:
            print(e)
            flash('Please enter positive number')
            return redirect('/')

    else:
        try:
            redeem = int(redeem)
            update_cash = current_cash - redeem
            cash = redeem
            type = 'REDEEM CASH'
        except Exception as e:
            print(e)
            flash('Please enter positive number')
            return redirect('/')

    try:
        update_trans = User.query.filter_by(id=session['user_id']).update(dict(cash=update_cash))
        new_transaction = Transaction(user_id=session['user_id'], symbol='CASH', company='CASH', \
                                        share_price=0,share_qty=0,\
                                        total_cost=cash, transaction_type=type)
        db.session.add(new_transaction)
    except Exception as e:
        print(e)
        flash('Error in transaction')
        return redirect('/')

    db.session.commit()
    flash('Account updated successfully')
    return redirect('/')


# def change passworrd profile
@app.route('/user_profile', methods=['GET','POST'])
@login_required
def user_profile():
    ''' display and update user profile '''
    user_details = User.query.filter_by(id=session['user_id'])
    profile_details = User_Profile.query.filter_by(user_id=session['user_id'])
    transaction_db = Transaction.query.with_entities(Transaction.symbol, Transaction.company).filter_by(user_id=session['user_id']).group_by('symbol')

    if request.method=='GET':
        user_details1 = user_details.first()
        profile_details1 = profile_details.first()
        transaction_details = transaction_db.all()
        if profile_details1.phone_number is not None:
            phone = str(profile_details1.phone_number).split('.')[0]
            phone ='(+91) ' + phone[:3]  + '-' + phone[3:6] + '-' + phone[6:]
        else:
            phone = None
        return render_template('users_profile.html', name=user_details1.name, email=user_details1.email,\
                                 username=user_details1.username, image=profile_details1.profile_picture, \
                                 birthdate= profile_details1.birthdate, company_symbol=transaction_details,\
                                 address=profile_details1.address, phone_number=phone)
    else:

        fullname = request.form.get('fullname')
        if fullname:
            update_name = user_details.update(dict(name=fullname))
            # db.session.commit()
        username = request.form.get('username')

        if username:
            update_name = user_details.update(dict(username=username))
            # db.session.commit()

        email = request.form.get('email')
        if email:
            update_name = user_details.update(dict(email=email))
            # db.session.commit()

        # query for the records of the user and user_profile
        user_details1 = user_details.first()
        profile_details1 = profile_details.first()

        address = request.form.get('address')
        if address:
            update_date = profile_details.update(dict(address=address))
            # db.session.commit

        phone_number = request.form.get('phone_number')
        if phone_number:
            update_date = profile_details.update(dict(phone_number=phone_number))
            # db.session.commit
        # get the birthdate and convert it into date format to store in the database
        birthdate = request.form.get('birthdate')
        # https://www.programiz.com/python-programming/examples/string-to-datetime
        # https://stackoverflow.com/questions/27800775/python-dateutil-parser-parse-parses-month-first-not-day
        if birthdate :
            #convert string birthdate into datetime tyoe to store in the database
            birthdate = datetime.strptime(birthdate, "%d-%m-%Y").date()
            # print('birth',birthdate, type(birthdate))
            update_date = profile_details.update(dict(birthdate=birthdate))
            # db.session.commit

        # get the uploaded profile picture file details in order to store it in the database
        # https://flask.palletsprojects.com/en/0.12.x/patterns/fileuploads/
        # https://stackoverflow.com/questions/55662935/how-to-upload-image-files-from-a-form-to-a-database-in-python-framework-flask
        # since user_profile.html has two forms directing to user_profile route the other form doesn't have file form due to which the app route throws bad request error while trying to change password so catch the error and set file to empty string
        try:
            file = request.files['file']
        except BadRequest as e:
            print(e)
            print('request form10',request.form)
            file = ""
        # save the file in the directory and update the database
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            image_url = file.filename
            update_profile = profile_details.update(dict(profile_picture=image_url))
            # db.session.commit()

        #Change password
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirmation = request.form.get('confirmation')
        print('1',old_password, new_password, confirmation)


        if old_password:
            # check for old password in the database

            if not check_password_hash(user_details1.password_hash,old_password):
                flash('Please enter correct old password')
                return redirect("/user_profile")

            # regex check
            #checking criteria for password strength server/backend side
            # password pattern regex
            reg_regular_expression = str("^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,20}$")
            pat_pattern = re.compile(reg_regular_expression)

            mat_match = pat_pattern.findall(new_password)

            #validating conditions
            if mat_match == []:
                flash("Password doesn't pass requirments")
                return redirect("/user_profile")


            #for checking criteria for password strength client/front_end side follow Khasa -passwordchecker.js
            # generate password hash
            hash_password = generate_password_hash(new_password)
            # change password in database by inserting the new updated hashed password
            if new_password != confirmation:
                flash("passwords don't match")
                return redirect("/user_profile")

            update_password = user_details.update(dict(password_hash=hash_password))

        db.session.commit()
        flash("Profile Updated Successfully")
        return redirect('/user_profile')


@app.route("/delete_picture", methods=['GET', 'POST'])
@login_required
def delete_picture():
    profile_details = User_Profile.query.filter_by(user_id=session['user_id'])
    profile_details2 = profile_details.first()

    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], profile_details2.profile_picture))

    profile_details1 = profile_details.update(dict(profile_picture=None))
    db.session.commit()
    flash("Picture has been Deleted Sucessfully!!!")
    return redirect('/user_profile')


# https://flask.palletsprojects.com/en/2.1.x/errorhandling/
def errorhandler(e):
    """Handle error"""
    print('found error', e.code, e.name)
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    # return blank html when page not found, helpful in finding quote as it returns first blank page and then quote page inside the modal
    if e.code == 404:
        return render_template('blank.html')
    return apology(e.name, e.code)

# https://werkzeug.palletsprojects.com/en/2.1.x/exceptions/
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

