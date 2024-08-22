from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# MongoDB Atlas Connection
client = MongoClient("mongodb+srv://sai:8778386853@cluster0.9vhjs.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['drawing_business']
users_collection = db['users']
orders_collection = db['orders']
chats_collection = db['chats']

class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        return User(str(user["_id"]), user["username"], user["role"])
    return None

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = password
        users_collection.insert_one({"username": username, "password": hashed_password, "role": "client"})
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({"username": username})
        if user and user['password']==password:
            user_obj = User(str(user["_id"]), user['username'], user['role'])
            login_user(user_obj)
            flash('Logged in successfully.', 'success')
            if user_obj.role == 'client':
                return redirect(url_for('client_dashboard'))
            else:
                return redirect(url_for('admin_facilitator_dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/client_dashboard')
@login_required
def client_dashboard():
    if current_user.role != 'client':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    orders = list(orders_collection.find({"uploaded_by": ObjectId(current_user.id)}))
    return render_template('client_dashboard.html', orders=orders)

@app.route('/admin_facilitator_dashboard')
@login_required
def admin_facilitator_dashboard():
    if current_user.role not in ['administrator', 'facilitator']:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    orders = orders_collection.find()
    return render_template('admin_facilitator_dashboard.html', orders=orders)

@app.route('/place_order', methods=['GET', 'POST'])
@login_required
def place_order():
    if current_user.role != 'client':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        hd_picture = request.files['hd_picture']
        animal_picture = request.files['animal_picture'] if 'animal_picture' in request.files else None
        gender = request.form['gender']
        name = request.form['name']
        message_to_designer = request.form['message_to_designer']
        style = request.form['style']

        if hd_picture and hd_picture.content_length <= 5 * 1024 * 1024:
            order_data = {
                "hd_picture": hd_picture.read(),
                "pet_picture": animal_picture.read() if animal_picture else None,
                "gender": gender,
                "name": name,
                "message_to_designer": message_to_designer,
                "style": style,
                "status": "pending",
                "rejection_message": "",
                "uploaded_by": ObjectId(current_user.id)
            }
            order_id = orders_collection.insert_one(order_data).inserted_id
            flash('Order placed successfully.', 'success')
            return redirect(url_for('client_dashboard'))
        else:
            flash('Image must be less than 5 MB!', 'danger')
    
    return render_template('place_order.html')

@app.route('/update_order/<order_id>', methods=['POST'])
@login_required
def update_order(order_id):
    if current_user.role not in ['administrator', 'facilitator']:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    status = request.form['status']
    orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": status}}
    )
    flash('Order status updated.', 'success')
    return redirect(url_for('admin_facilitator_dashboard'))

@app.route('/reject_order/<order_id>', methods=['POST'])
@login_required
def reject_order(order_id):
    if current_user.role not in ['administrator', 'facilitator']:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    rejection_message = request.form['rejection_message']
    orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": "rejected", "rejection_message": rejection_message}}
    )
    flash('Order rejected.', 'success')
    return redirect(url_for('admin_facilitator_dashboard'))

@app.route('/reupload_image/<order_id>', methods=['POST'])
@login_required
def reupload_image(order_id):
    if current_user.role not in ['administrator', 'facilitator']:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    new_image = request.files['new_image']
    if new_image and new_image.content_length <= 5 * 1024 * 1024:
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"hd_picture": new_image.read(), "status": "pending", "rejection_message": ""}}
        )
        flash('Image reuploaded and order status set to pending.', 'success')
    else:
        flash('Image must be less than 5 MB!', 'danger')

    return redirect(url_for('admin_facilitator_dashboard'))

@app.route('/display_image/<order_id>/<image_type>')
@login_required
def display_image(order_id, image_type):
    order = orders_collection.find_one({"_id": ObjectId(order_id)})
    if order and image_type in order:
        return send_file(
            io.BytesIO(order[image_type]),
            mimetype='image/jpeg'
        )
    flash('Image not found.', 'danger')
    return redirect(url_for('index'))

@app.route('/chat/<order_id>', methods=['GET', 'POST'])
@login_required
def chat(order_id):
    if request.method == 'POST':
        message = request.form['message']
        if message:
            chat_data = {
                "order_id": ObjectId(order_id),
                "username": current_user.username,
                "message": message,
                "timestamp": datetime.now(),
                "user_id": ObjectId(current_user.id)
            }
            chats_collection.insert_one(chat_data)
            flash('Message sent.', 'success')
    
    # Fetch messages for the order
    chats = chats_collection.find({"order_id": ObjectId(order_id)}).sort("timestamp", 1)
    messages = []
    for chat in chats:
        messages.append({
            "username": chat["username"],
            "message": chat["message"],
            "timestamp": chat["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return render_template('chat.html', order_id=order_id, messages=messages)

@app.route('/fetch_messages/<order_id>', methods=['GET'])
@login_required
def fetch_messages(order_id):
    chats = chats_collection.find({"order_id": ObjectId(order_id)}).sort("timestamp", 1)
    messages = []
    for chat in chats:
        messages.append({
            "username": chat["username"],
            "message": chat["message"],
            "timestamp": chat["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({"messages": messages})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
