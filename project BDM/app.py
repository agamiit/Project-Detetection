from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash




app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///transactions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model for authentication
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"

# Transaction model for storing transaction data
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(50), nullable=False)
    receiver_id = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    is_fraud = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Transaction {self.transaction_id}>"
    


# Mock ML model for fraud detection
def mock_ml_model(features):
    # Simulate ML model prediction
    # Return True if fraud, False otherwise
    return features['sender_balance_diff'] > 5000 or features['receiver_balance_diff'] > 5000

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        # Fetch the 5 most recent transactions
        recent_transactions = Transaction.query.order_by(Transaction.id.desc()).limit(5).all()
        return render_template('dashboard.html', transactions=recent_transactions)
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('signup.html', error="Email already registered.")

        # Hash the password and save the user
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Authenticate user
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('enter_details'))
        return render_template('login.html', error="Invalid email or password.")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/enter-details', methods=['GET', 'POST'])
def enter_details():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        sender_id = request.form['sender_id']
        receiver_id = request.form['receiver_id']
        transaction_id = request.form['transaction_id']
        amount = float(request.form['amount'])

        # Fetch sender and receiver balances from the database
        sender_transactions = Transaction.query.filter_by(sender_id=sender_id).all()
        receiver_transactions = Transaction.query.filter_by(receiver_id=receiver_id).all()

        sender_old_balance = sum(t.amount for t in sender_transactions)
        receiver_old_balance = sum(t.amount for t in receiver_transactions)

        sender_new_balance = sender_old_balance - amount
        receiver_new_balance = receiver_old_balance + amount

        sender_balance_diff = abs(sender_new_balance - sender_old_balance)
        receiver_balance_diff = abs(receiver_new_balance - receiver_old_balance)

        # Prepare features for ML model
        features = {
            'sender_old_balance': sender_old_balance,
            'receiver_old_balance': receiver_old_balance,
            'sender_new_balance': sender_new_balance,
            'receiver_new_balance': receiver_new_balance,
            'sender_balance_diff': sender_balance_diff,
            'receiver_balance_diff': receiver_balance_diff,
        }

        # Predict fraud using the ML model
        is_fraud = mock_ml_model(features)

        # Save transaction to the database
        new_transaction = Transaction(
            sender_id=sender_id,
            receiver_id=receiver_id,
            transaction_id=transaction_id,
            amount=amount,
            transaction_type=request.form['transaction_type'],
            is_fraud=is_fraud
        )
        db.session.add(new_transaction)
        db.session.commit()

        # Render result page
        return render_template('transaction_result.html', features=features, is_fraud=is_fraud)
    return render_template('enter_details.html')

@app.route('/fetch-transaction', methods=['GET', 'POST'])
def fetch_transaction():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        sender_id = request.form.get('sender_id')
        receiver_id = request.form.get('receiver_id')
        transaction_id = request.form.get('transaction_id')
        amount = request.form.get('amount')

        # Build query dynamically based on input
        query = Transaction.query
        if sender_id:
            query = query.filter_by(sender_id=sender_id)
        if receiver_id:
            query = query.filter_by(receiver_id=receiver_id)
        if transaction_id:
            query = query.filter_by(transaction_id=transaction_id)
        if amount:
            query = query.filter_by(amount=float(amount))

        # Execute query
        results = query.all()

        if results:
            return render_template('fetch_transaction.html', transactions=results)
        else:
            return render_template('fetch_transaction.html', error="No matching transactions found.")
    return render_template('fetch_transaction.html')

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))   
    return render_template('index.html')



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)