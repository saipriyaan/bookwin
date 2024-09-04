from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify,abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId
import io
from datetime import datetime
import os
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from googleapiclient.http import MediaIoBaseUpload
from flask_mail import Mail, Message
from io import BytesIO
from werkzeug.utils import secure_filename
import requests

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
tokens_collection = db['tokens']
tokens=db['google_drive_token']

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = "expenditure.cob@gmail.com"
app.config['MAIL_PASSWORD'] = "hrhdkdiwwzungmjz"
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)
from google.oauth2.credentials import Credentials
# Google OAuth and Drive API Configuration
CLIENT_SECRETS_FILE = 'gdrive.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v3'



@app.route('/')
def index():
    return render_template('index.html')
def get_credentials():
    credentials_data = tokens.find_one({"client_secret": "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"})
    print(credentials_data,'the files is ')
    if credentials_data:
        
        credentials = Credentials(
        token=credentials_data['token'],
        refresh_token=credentials_data['refresh_token'],
        token_uri=credentials_data['token_uri'],
        client_id=credentials_data['client_id'],
        client_secret=credentials_data['client_secret'],
        scopes=credentials_data['scopes']
    )
        # credentials = google.oauth2.credentials.Credentials(**token_data["token"])
        # flash('Please authorize the application through the provided link.', 'success')
    else:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
        flow.redirect_uri = url_for('oauth2callback', _external=True)
        authorization_url, _ = flow.authorization_url(access_type='offline')
        flash('Please authorize the application through the provided link.', 'danger')
        return redirect(authorization_url)
    return credentials

@app.route('/oauth2callback')
def oauth2callback():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    authorization_response = request.url

    flow.fetch_token(authorization_response=request.url)
    

    credentials = flow.credentials
    tokens_collection.update_one(
        {"_id": "google_drive_token"},
        {"$set": {"token": credentials_to_dict(credentials)}},
        upsert=True
    )

    print('Authorization successful.', 'success')
    return redirect(url_for('index'))

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

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
        username = request.form['username'].lower()
        password = request.form['password']
        hashed_password =  password
        users_collection.insert_one({"username": username, "password": hashed_password, "role": "client"})
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        user = users_collection.find_one({"username": username})
        if user and user['password']== password:
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

import googleapiclient.discovery
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO

API_SERVICE_NAME = 'drive'
API_VERSION = 'v3'

import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO

def upload_to_gdrive(file_data, filename, credentials):
    service = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    # Define the folder ID
    folder_id = '18iUVN-ad3GUVHmawPn7xIuHB7_ZkpSs4'

    # File metadata including the parent folder ID
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }

    # Upload the file
    media = MediaIoBaseUpload(BytesIO(file_data), mimetype='image/jpeg', resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # Get the file ID
    file_id = file.get('id')

    # Set the file permissions to public
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    service.permissions().create(fileId=file_id, body=permission).execute()

    return file_id


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

        credentials = get_credentials()
        if hd_picture and hd_picture.content_length <= 5 * 1024 * 1024:
            hd_picture_id = upload_to_gdrive(hd_picture.read(), secure_filename(hd_picture.filename), credentials)
            animal_picture_id = None
            if animal_picture:
                animal_picture_id = upload_to_gdrive(animal_picture.read(), secure_filename(animal_picture.filename), credentials)
            order_data = {
                "hd_picture_id": hd_picture_id,
                "animal_picture_id": animal_picture_id,
                "gender": gender,
                "username": current_user.username,
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
    if status in ['pending', 'in_progress', 'approval', 'payment_pending', 'completed']:
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": status}}
        )
        flash('Order status updated.', 'success')
    else:
        flash('Invalid status update.', 'danger')
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
        credentials = get_credentials()
        image_id = upload_to_gdrive(new_image.read(), secure_filename(new_image.filename), credentials)
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"hd_picture_id": image_id}}
        )
        flash('Image reuploaded successfully.', 'success')
    else:
        flash('Image must be less than 5 MB!', 'danger')
    return redirect(url_for('admin_facilitator_dashboard'))

@app.route('/view_order/<order_id>')
@login_required
def view_order(order_id):
    order = orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('index'))

    return render_template('view_order.html', order=order)

@app.route('/download_image/<image_id>')
@login_required
def download_image(image_id):
    credentials = get_credentials()
    service = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    request = service.files().get_media(fileId=image_id)
    file_stream = io.BytesIO()
    downloader = googleapiclient.http.MediaIoBaseDownload(file_stream, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    file_stream.seek(0)
    return send_file(file_stream, as_attachment=True, download_name="downloaded_image.jpg")

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

            # Fetch the order document to get the uploaded_by ID
            order = orders_collection.find_one({"_id": ObjectId(order_id)})
            if order:
                client_email = order.get('username')  # Assuming this is the client email
                admin_email = 'expenditure.cob@gmail.com'
                uploaded_by_id = order.get('uploaded_by')
                
                # Convert uploaded_by_id to ObjectId if needed
                uploaded_by_id = ObjectId(uploaded_by_id) if isinstance(uploaded_by_id, str) else uploaded_by_id

                # Print debugging information
                print(f"Sender ID: {current_user.id}, Uploaded By ID: {uploaded_by_id}")
                
                # Send email notification to the client if the sender is not the client
                if current_user.id != uploaded_by_id:
                    if current_user.username != client_email:
                        msg = Message('New Message in Your Order Chat',
                                      sender='expenditure.cob@gmail.com',
                                      recipients=[client_email])
                        msg.body = f"New message from {current_user.username}:\n\n{message}"
                        mail.send(msg)
                        print(f"Sent email to client: {client_email}")

                # Send email notification to the admin
                if current_user.id != uploaded_by_id:
                    admin_msg = Message('New Message in Order Chat',
                                        sender='expenditure.cob@gmail.com',
                                        recipients=[admin_email])
                    admin_msg.body = f"New message in order {order_id} from {current_user.username}:\n\n{message}"
                    mail.send(admin_msg)
                    print(f"Sent email to admin: {admin_email}")
    
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



from flask_mail import Mail, Message

# Existing Flask-Mail configuration here

def send_email(subject, recipient, body):
    msg = Message(subject, recipients=[recipient], body=body, sender="expenditure.cob@gmail.com")
    try:
        mail.send(msg)
        print(f"Email sent to {recipient}")
    except Exception as e:
        print(f"Error sending email: {e}")

@app.route('/display_image/<order_id>/<image_type>')
def display_image(order_id, image_type):
    # Fetch document from MongoDB
    document = orders_collection.find_one({"_id": ObjectId(order_id)})

    if document is None:
        abort(404, description="Document not found")

    # Determine the image ID based on the type
    image_id = document.get(f"{image_type}_id")
    if not image_id:
        abort(404, description="Image not found")

    # Fetch the image from storage
    image_url = get_image_url_from_storage(image_id)
    
    try:
        # For Google Drive
        response = requests.get(image_url)
        if response.status_code == 200:
            return send_file(BytesIO(response.content), mimetype='image/jpeg')  # Adjust mimetype if needed
        else:
            abort(404, description="Image fetch failed")
    except Exception as e:
        abort(500, description=f"Error fetching image: {e}")

import paypalrestsdk

paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": "ASj-Xf_9xqfLfOg6tZywOl6lcta9dceYoiy51-yRaAF0ceyX-d4c8Sd5LTcQ_YKkQjwxNco4NmK176Nu",
    "client_secret": "EMtkLyRrkibEjQs3MEAYF7n22eon45Oqn9V6NCI7JmJ3eRAX4sA5I5DqSXsmuGCBPLcPVpU6JT5qUcgZ"
})


@app.route('/pay/<order_id>', methods=['GET'])
@login_required
def pay(order_id):
    order = orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('index'))

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": url_for('payment_success', order_id=order_id, _external=True),
            "cancel_url": url_for('payment_cancelled', _external=True)
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "Order Payment",
                    "sku": "item",
                    "price": 100,  # The amount should be in your order details
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {
                "total": 100,
                "currency": "USD"
            },
            "description": "Payment for order."
        }]
    })

    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                approval_url = link.href
                return redirect(approval_url)
    else:
        flash('Payment creation failed.', 'danger')
        return redirect(url_for('client_dashboard'))

@app.route('/payment_success', methods=['GET'])
@login_required
def payment_success():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    order_id = request.args.get('order_id')

    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": "completed"}}
        )
        flash('Payment successful and order completed.', 'success')
    else:
        flash('Payment execution failed.', 'danger')

    return redirect(url_for('client_dashboard'))

@app.route('/payment_cancelled', methods=['GET'])
def payment_cancelled():
    flash('Payment cancelled.', 'warning')
    return redirect(url_for('client_dashboard'))



def get_image_url_from_storage(image_id):
    # Construct the image URL (example for Google Drive)
    return f"https://drive.google.com/uc?id={image_id}"
if __name__ == '__main__':
    import os 
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True)
