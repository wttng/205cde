from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from data import Products
from functools import wraps
import json
app = Flask(__name__)
app.secret_key = 'development key'

# Config SQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'tal'
app.config['MYSQL_PASSWORD'] = 'php2020'
app.config['MYSQL_DB'] = 'myapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Init MYSQL
mysql = MySQL(app)

Products = Products()

# Validate form data from Register form
class RegisterForm(Form):
    name = StringField('Name', [validators.length(min=1, max=50)])
    username  = StringField('Username', [validators.length(min=4, max=25)])
    email  = StringField('Email', [validators.email()])
    password  = PasswordField('Password', [validators.DataRequired(), validators.
    	EqualTo('confirm', message = 'Password do not match')])
    confirm  = PasswordField('Confirm Password')

# Validate form data from Message form
class MsgForm(Form):
	name = StringField('Name', [validators.length(min=1, max=50)])
	email  = StringField('Email', [validators.email()])
	comment = TextAreaField('Comment', [validators.length(min=1, max=70)] )

# Validate form data from Order form
class OrderForm(Form):
	name = StringField('Name', [validators.length(min=1, max=50)])
	email  = StringField('Email', [validators.email()])

# Check if user logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Please login to continue', 'danger')
			return redirect(url_for('login'))
	return wrap

# Home page
@app.route('/')
def index():
	return render_template('home.html')

# Store information with a message section
@app.route('/about', methods=['GET', 'POST'])
def about():

	form = MsgForm(request.form)
	if request.method == 'POST' and form.validate():
		#return render_template('about.html')
		name = form.name.data
		email = form.email.data
		comment = form.comment.data

		# create cursor
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO message(name, email, comment) VALUES (%s, %s, %s)",
		 (name, email, comment))

		# commit to DB
		mysql.connection.commit()

		# close connection
		cur.close()

		flash("Your message have been sent successfully. Thanks!", 'success')
		return redirect(url_for('about'))
	return render_template('about.html', form = form)

# Catalog for the products
@app.route('/products')
def products():
	return render_template('products.html', products = Products)

# Ordering page
@app.route('/product/<string:id>/', methods=['GET','POST'])
@is_logged_in
def product(id):

	cur = mysql.connection.cursor()

	# fetch and store specific products record to app
	result = cur.execute("SELECT * FROM products WHERE id = %s", [id])
	product = cur.fetchone()

	form = OrderForm(request.form)

	# store form data in variables 
	if request.method == 'POST' and form.validate():
		product_ordered = product["name"]
		product_type = product['type']
		quantity = request.form['choice']
		price = float(product["price"]) * float(quantity)
		pickupdate = request.form['pickupdate']
		username = session['username']
		name = form.name.data
		email = form.email.data
		
		# insert order details to DB
		cur.execute("INSERT INTO orders(product,type, quantity, price, pickupdate, username, name, email ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
		 (product_ordered, product_type, quantity, price, pickupdate, username, name, email))

		# commit to DB
		mysql.connection.commit()

		#close connection
		cur.close()

		flash("Your order has been made", 'success')
		return redirect(url_for('products'))

	return render_template('product.html', form = form, product = product, id = id )

# User register
@app.route('/register', methods=['GET', 'POST'])
def register():

	form = RegisterForm(request.form)

	if request.method == 'POST' and form.validate():
		#return render_template('register.html')
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		# create cursor
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO users(name, email, username, password) VALUES (%s, %s, %s, %s)",
		 (name, email, username, password))

		# commit to DB
		mysql.connection.commit()

		# close connection
		cur.close()

		flash("You are now registered and can log in", 'success')
		return redirect(url_for('index'))
	return render_template('register.html', form = form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':

		# get form fields
		username = request.form['username']
		password_candidate = request.form['password']

		# create cursor
		cur = mysql.connection.cursor()

		# find and get user by username
		if (username == "admin") and (password_candidate=="admin"):
			session['logged_in'] = True
			session['username'] = username
			flash('Hello admin!','success')
			return redirect(url_for('index'))
		else:
			result = cur.execute("SELECT * FROM users WHERE username = %s", [username])
			if result > 0:
				data = cur.fetchone()
				password = data['password']

				# compare password
				if sha256_crypt.verify(password_candidate, password):
					app.logger.info('PASSWORD MATCHED')
					session['logged_in'] = True
					session['username'] = username

					flash('You are now logged in', 'success')
					return redirect(url_for('index'))
				else:
					error = 'Invalid login'
					return render_template('login.html', error = error)
				cur.close()
			else:
				error = 'Username not found'
				return render_template('login.html', error = error)
	return render_template('login.html')

# User logout
@app.route('/logout')
def logout():
	#clear session data
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))

# Comment board for admin
@app.route('/commentboard')
@is_logged_in
def commentboard():
	cur = mysql.connection.cursor()
	#fetch all data from table message in DB
	result = cur.execute("SELECT * FROM message")
	messages = cur.fetchall()
	if result > 0:
		return render_template('commentboard.html', messages = messages)
	else:
		msg = "No Orders Found"
		return render_template('commentboard.html', msg = msg)

# Show order records
@app.route('/orderhistory')
@is_logged_in
def orderhistory():

	cur = mysql.connection.cursor()

	#fetch details based on username
	if session['username'] == 'admin':
		result = cur.execute("SELECT * FROM orders")
	else:
		result = cur.execute("SELECT * FROM orders WHERE username = %s", (session['username'],))
	orders = cur.fetchall()
	if result > 0:
		return render_template('orderhistory.html', orders = orders)
	else:
		msg = "No Orders Found"
		return render_template('orderhistory.html', msg = msg)

# Edit order details
@app.route('/edit_order/<string:id>/', methods=['GET','POST'])
@is_logged_in
def edit_order(id):

	cur = mysql.connection.cursor()
	cur.execute("SELECT * FROM orders WHERE order_id = %s", [id])
	order = cur.fetchone()
	cur.close()

	form = OrderForm(request.form)

	# store DB data in local variables
	product_ordered = order['product']
	quantity = order['quantity']
	price = order['price']
	pickupdate = order['pickupdate']
	form.name.data = order['name']
	form.email.data = order['email']
	orderID = order['order_id']

	cur = mysql.connection.cursor()
	# fetch specified product details
	cur.execute("SELECT * FROM products WHERE name = %s", [product_ordered])
	product = cur.fetchone()
	cur.close()

	# update details locally
	if request.method == 'POST' and form.validate():
		product_ordered = product["name"]
		quantity = request.form['choice']
		price = float(product["price"]) * float(quantity)
		pickupdate = request.form['pickupdate']
		username = session['username']
		name = request.form['name']
		email = request.form['email']

		cur = mysql.connection.cursor()

		# update details in DB
		cur.execute("UPDATE orders SET quantity=%s, price=%s, pickupdate=%s, name=%s, email=%s WHERE order_id = %s",
			(quantity, price, pickupdate, name, email, id))

		mysql.connection.commit()

		# close connection
		cur.close()

		flash("Order updated", 'success')
		return redirect(url_for("orderhistory"))
	return render_template("edit_order.html", form=form, product= product)

# Delete order
@app.route('/delete_order/<string:id>', methods=['POST'])
@is_logged_in
def delete_order(id):
	cur = mysql.connection.cursor()
	# delete specified record
	cur.execute("DELETE FROM orders WHERE order_id =%s", [id])
	mysql.connection.commit()
	cur.close()
	flash("Order deleted successfully!","success")
	return redirect(url_for("orderhistory"))


if __name__ == "__main__":
	app.debug = True
	app.run()