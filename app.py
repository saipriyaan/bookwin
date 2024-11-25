from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify,abort,session
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
import os
from flask import Flask, render_template
from pdf2image import convert_from_path
import pytz
timezone = pytz.timezone('US/Eastern')


app = Flask(__name__)
import uuid
app.secret_key = 'your_secret_key'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# MongoDB Atlas Connection
client = MongoClient("mongodb+srv://sai:8778386853@cluster0.9vhjs.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['drawing_business']
book_purchases_collection = db['book_purchases'] 
users_collection = db['users']
orders_collection = db['orders']
chats_collection = db['chats']
payment_success_collection=db['payment']
tokens_collection = db['tokens']
tokens=db['google_drive_token']
queries_collection = db['queries'] 

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = "serviceemailshop@gmail.com"
app.config['MAIL_PASSWORD'] = "ukdqyqjvqepfeuad"
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)
from google.oauth2.credentials import Credentials
# Google OAuth and Drive API Configuration
CLIENT_SECRETS_FILE = 'gdrive.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v3'

from flask_login import current_user

@app.route('/')
def index():
    client_logged_in = current_user.is_authenticated  # Check if user is logged in
    return render_template('purchase_book.html', client_logged_in=client_logged_in)
@app.route('/guide')
def guide():
    client_logged_in = current_user.is_authenticated  # Check if user is logged in
    return render_template('gui.html', client_logged_in=client_logged_in)
@app.route('/bookg')
def bookg():
    client_logged_in = current_user.is_authenticated  # Check if user is logged in
    return render_template('bookg.html', client_logged_in=client_logged_in)

@app.route('/broker_form', methods=['GET', 'POST'])
def broker_form():
    if request.method == 'POST':
        broker_id = request.form.get('brokerId')
        if broker_id:
            session['broker_id'] = broker_id
            # Render a template that contains a form to redirect as a POST
            return render_template('redirect_form.html')
        else:
            # Render the form template for the "no broker ID" case
            return render_template('redirect_form.html')
    return render_template('broker_form.html')

@app.route('/salerepcheck', methods=['GET', 'POST'])
@login_required
def salerepcheck():
    client_logged_in = current_user.is_authenticated  # Check if user is logged in
    return render_template('brokerid.html', client_logged_in=client_logged_in)


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
        hashed_password = password 

        # Check if the username (email) already exists
        existing_user = users_collection.find_one({"username": username})
        
        if existing_user:
            flash('An account with this email already exists. Please log in or use a different email.', 'danger')
            return redirect(url_for('signup'))

        
        users_collection.insert_one({"username": username, "password": hashed_password, "role": "client"})
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')




@app.route('/contact', methods=['GET', 'POST'])
def contact():
    management_team = [
        {"name": "Sherwood Ballard",'telephone':'1-800-389-0917' ,"email": "dreamkidsbiz@gmail.com", "position": "Manager"},
        {"name": "Sai Priyan J K", "email": "", "position": "Technical Lead"},
   
    ]

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # Save form data to the new queries collection
        query = {
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "date_submitted": datetime.now(timezone)  # Store the timestamp of submission
        }

        queries_collection.insert_one(query)  # Insert the form data into the queries collection

        flash('Your query has been submitted successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html', management_team=management_team)
# Sales Rep Collection
sales_rep_col = db['sales_bookreps']
payment_logs_col = db['payment_logs']

@app.route('/sales_rep_signup', methods=['GET', 'POST'])
def sales_rep_signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        ph = request.form['phone']
        com = request.form['com']
        
        # Generate a unique rep code
        rep_code = str(uuid.uuid4())[:8]
        
        # Check if email already exists
        if sales_rep_col.find_one({'email': email}):
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('sales_rep_signup'))
        
        # Create a new sales rep
        new_rep = {
            'name': name,
            'email': email,
            'password': password,
            'phone':ph,
            
            'com':com,
            'rep_code': rep_code,
            'balance': 0.0
        }
        
        sales_rep_col.insert_one(new_rep)
        flash('Sales rep account created successfully! Your rep code is: ' + rep_code, 'success')
        return redirect(url_for('sales_rep_login'))
    
    return render_template('sales_rep_signup.html')

@app.route('/sale',methods=['GET','POST'])
def sale():
    return render_template("promotion.html")

@app.route('/about',methods=['GET','POST'])
def about():
    return render_template("about.html")
@app.route('/sales_rep_login', methods=['GET', 'POST'])
def sales_rep_login():

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        rep = sales_rep_col.find_one({'email': email})
        
        if rep and rep['password']== password:
            session['rep_id'] = str(rep['_id'])
            print(str(rep['_id']))
            session['rep_code'] = rep['rep_code']
            return redirect(url_for('sales_rep_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    
    return render_template('sales_rep_login.html')

@app.route('/admin/sales_reps', methods=['GET'])
@login_required
def admin_sales_reps():
    if current_user.role != 'administrator':
        return redirect(url_for('index'))
    
    sales_reps = sales_rep_col.find()
    return render_template('admin_sales_reps.html', sales_reps=sales_reps)

@app.route('/admin/sales_rep/<rep_id>', methods=['GET', 'POST'])
@login_required
def admin_sales_rep_detail(rep_id):
    if current_user.role != "administrator":
        return redirect(url_for('index'))

    sales_rep = sales_rep_col.find_one({"_id": ObjectId(rep_id)})
    payment_logs = payment_logs_col.find({"rep_code": ObjectId(rep_id)})
    
    


    if request.method == 'POST':
        adjustment_amount = float(request.form['adjustment_amount'])
        adjustment_amount = -adjustment_amount
        sales_rep_col.update_one(
            {"_id": ObjectId(rep_id)},
            {"$inc": {"balance": adjustment_amount}}
        )
        
        # Log the adjustment
        payment_logs_col.insert_one({
            "rep_code": ObjectId(rep_id),
            "amount": adjustment_amount,
            "payment_id":"Cleared",
            "admin": current_user.username,
            "timestamp": datetime.now(timezone)
        })
        
        flash("Balance updated successfully", "success")
        return redirect(url_for('admin_sales_rep_detail', rep_id=rep_id))
    
    return render_template('admin_sales_rep_detail.html', sales_rep=sales_rep, logs=list(payment_logs))




@app.route('/sales_rep_dashboard')

def sales_rep_dashboard():
    if 'rep_id' not in session:
        flash('Please log in to access the dashboard.', 'danger')
        return redirect(url_for('sales_rep_login'))
    print(session['rep_id'])
    
    rep = sales_rep_col.find_one({'_id':  ObjectId(session['rep_id'])})
    payment_logs =list( payment_logs_col.find({'rep_code': ObjectId(session['rep_id'])}))
    print(rep)
    
    return render_template('sales_rep_dashboard.html', rep=rep, logs=payment_logs)
@app.route('/purchase', methods=['GET', 'POST'])
@login_required
def purchase_boo():
    
    purchase_record = book_purchases_collection.find_one({"user_id": current_user.id})

    if purchase_record and purchase_record.get('has_purchased_book'):
        # If the user has already purchased the book, redirect them to the view page
        unique_link = purchase_record.get('book_link')
        return redirect(url_for('view_book', unique_link=unique_link))

    # If the user hasn't purchased the book yet and makes a POST request, process payment
    if request.method == 'POST':
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": url_for('paymentbook_success', _external=True),
                "cancel_url": url_for('paymentbook_cancel', _external=True)
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "E-book",
                        "sku": "001",
                        "price": "30.00",
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": "30.00",
                    "currency": "USD"
                },
                "description": "Purchase of PDF book."
            }]
        })

        if payment.create():
            session['payment_id'] = payment.id
            for link in payment['links']:
                if link['rel'] == 'approval_url':
                    approval_url = str(link['href'])
                    return redirect(approval_url)
        else:
            flash('An error occurred with PayPal payment.', 'danger')
            return redirect(url_for('purchase_boo'))

    return render_template('purchase_book.html', has_purchased=False)


@app.route('/purchase_boo_check')
@login_required
def purchase_boo_check():
    purchase_record = book_purchases_collection.find_one({"user_id": current_user.id})

    if purchase_record and purchase_record.get('has_purchased_book'):
        unique_link = purchase_record.get('book_link')
        return render_template('purchase_book.html', has_purchased=True, unique_link=unique_link)

    return render_template('purchase_book.html', has_purchased=False)
from flask_login import current_user

@app.route('/book_sales')
@login_required
def booksale():

    if current_user.role != 'administrator':
        flash('You are not authorized to view this page.', 'danger')
        return redirect(url_for('index'))
    
     # Fetch all purchases
    all_purchases = book_purchases_collection.find()
    purchase_count = book_purchases_collection.count_documents({})

    return render_template('salebook.html', purchases=all_purchases, purchase_count=purchase_count)

from flask_mail import Message
from datetime import datetime
import uuid


@app.route('/paymentbook_cancel')
@login_required
def paymentbook_cancel():
    flash('Payment was cancelled.', 'warning')
    return redirect(url_for('purchase_boo'))

# View book route
@app.route('/view_book/<unique_link>')
@login_required
def view_book(unique_link):
    purchase_record = book_purchases_collection.find_one({"user_id": current_user.id})

    if purchase_record and purchase_record.get('has_purchased_book') and purchase_record.get('book_link') == unique_link:
        return render_template('view_pdf.html')  
    else:
        flash('You do not have access to view this book.', 'danger')
        return redirect(url_for('purchase_boo'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        user = users_collection.find_one({"username": username})
        
        # Check if user exists and password is correct
        if user and user['password'] == password:
            user_obj = User(str(user["_id"]), user['username'], user['role'])
            login_user(user_obj)
            flash('Logged in successfully.', 'success')

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)

            # Redirect based on user role
            if user_obj.role == 'client':
                return redirect(url_for('purchase_boo'))
            else:
                return redirect(url_for('admin_facilitator_dashboard'))

        flash('Invalid username or password.', 'danger')

    # Render login page
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
    return redirect(url_for('admin_sales_reps'))

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

@app.route('/styles')
def styles():
    client_logged_in = current_user.is_authenticated
    
    
    return render_template('style.html', client_logged_in=client_logged_in) # Check if user is logged in



from flask import render_template_string

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
        style2 = request.form['style2']

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
                "style2": style2,
                "status": "pending",
                "rejection_message": "",
                "uploaded_by": ObjectId(current_user.id)
            }
            order_id = orders_collection.insert_one(order_data).inserted_id

            # Send confirmation email
            email_html = render_template_string('''
                <!-- HTML Template from above -->
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Order Confirmation</title>
                </head>
                <body style="font-family: Arial, sans-serif; background-color: #f7f7f7; margin: 0; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); padding: 20px;">
                        <h2 style="color: #4caf50; text-align: center;">Order Confirmation</h2>
                        <p>Dear Customer,</p>
                        <p>Thank you for placing your order with us. Here are the details of your order:</p>
                        <table style="width: 90%; border-collapse: collapse; margin: 20px 0;">
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;">Order ID:</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{{ order_id }}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;">Name:</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{{ name }}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;">Gender:</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{{ gender }}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;">Style 1:</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{{ style }}</td>
                            </tr>
                                                <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;">Style 2:</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{{ style2 }}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;">Message to Designer:</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{{ message_to_designer }}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;">Status:</td>
                                <td style="padding: 10px; border: 1px solid #ddd; color: #2196f3;">Pending</td>
                            </tr>
                        </table>
                        <p>Your order is being processed. You will receive updates on the progress of your order soon.</p>
                        <p>If you have any questions, feel free to send a message in chat  .</p>
                        <p style="text-align: center; margin-top: 30px;">Thank you for choosing our service!</p>
                        <p style="text-align: center; color: #999;">Deam Photo AI &copy; 2024  All rights reserved.</p>
                    </div>
                </body>
                </html>
            ''', order_id=order_id, name=name, gender=gender, style2=style2, style=style, message_to_designer=message_to_designer)

            msg = Message('Order Confirmation - Your Order with Us',
                          sender='dreamphotostudioai@gmail.com',
                          recipients=[current_user.username])
            msg.html = email_html
            mail.send(msg)
            msg = Message('New Order',
                          sender='dreamphotostudioai@gmail.com',
                          recipients=["","dreamkidsbiz@gmail.com"])
            msg.html = email_html
            mail.send(msg)


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
@app.route('/upload_picture/<order_id>', methods=['POST'])
@login_required
def upload_picture(order_id):
    if current_user.role not in ['administrator', 'facilitator']:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    # Determine if uploading a sample or final picture
    upload_type = request.form.get('upload_type')  # 'sample' or 'final'

    picture_file = request.files.get('picture_file')
    picture_link = request.form.get('picture_link')

    if picture_file and picture_file.content_length <= 5 * 1024 * 1024:
        credentials = get_credentials()
        image_id = upload_to_gdrive(picture_file.read(), secure_filename(picture_file.filename), credentials)
        picture_data = {"image_id": image_id, "type": "image"}
    elif picture_link:
        picture_data = {"link": picture_link, "type": "link"}
    else:
        flash('Invalid picture file or link.', 'danger')
        return redirect(url_for('admin_facilitator_dashboard'))

    # Update the order with the uploaded picture
    if upload_type == 'sample':
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"sample_picture": picture_data}}
        )
    elif upload_type == 'final':
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"final_picture": picture_data}}
        )
    
    flash(f'{upload_type.capitalize()} picture uploaded successfully.', 'success')
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
                "timestamp": datetime.now(timezone),
                "user_id": ObjectId(current_user.id)
            }
            chats_collection.insert_one(chat_data)
            flash('Message sent.', 'success')

            # Fetch the order document to get the uploaded_by ID
            order = orders_collection.find_one({"_id": ObjectId(order_id)})
            if order:
                client_email = order.get('username')  # Assuming this is the client email
                admin_email = ''
                uploaded_by_id = order.get('uploaded_by')
                
                # Convert uploaded_by_id to ObjectId if needed
                uploaded_by_id = ObjectId(uploaded_by_id) if isinstance(uploaded_by_id, str) else uploaded_by_id

                # Print debugging information
                print(f"Sender ID: {current_user.id}, Uploaded By ID: {uploaded_by_id}")
                
                # Send email notification to the client if the sender is not the client
                if current_user.id != uploaded_by_id:
                    if current_user.username != client_email:
                        msg = Message('New Message in Your Order Chat',
                                      sender='dreamphotostudioai@gmail.com',
                                      recipients=[client_email])
                        msg.body = f"New message from {current_user.username}:\n\n{message}"
                        mail.send(msg)
                        print(f"Sent email to client: {client_email}")

                # Send email notification to the admin
                if current_user.id != uploaded_by_id:
                    admin_msg = Message('New Message in Order Chat',
                                        sender='dreamphotostudioai@gmail.com',
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
    msg = Message(subject, recipients=[recipient], body=body, sender="dreamphotostudioai@gmail.com")
    try:
        mail.send(msg)
        print(f"Email sent to {recipient}")
    except Exception as e:
        print(f"Error sending email: {e}")

@app.route('/display_image/<order_id>/<image_type>')
def display_image(order_id, image_type):
    print(image_type)
    # Fetch document from MongoDB
    document = orders_collection.find_one({"_id": ObjectId(order_id)})

    if document is None:
        abort(404, description="Document not found")
    if image_type=="sample_picture":
        image_id = document.get(f"{image_type}").get('image_id')
        print('the image is sample')
    elif image_type=="final_picture":
        image_id = document.get(f"{image_type}").get('image_id')
        print('the image is final')
    else:
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
    "mode": "live",  # Change to "live" for production
    "client_id": "AcqD8TXVqVin_YoXJiC_h7O1_vldBycYnIopIsersWz_RZX9X3TpUytPP-fEtCv9c5UAM0j6or0YZkpl",
    "client_secret": "EGs-EylBXYPUMn7xDFF4W12g_R4YeHmDcsXP6ZIloI4cR3YI2GqT5W_VKHdm59MVRtdsuaMrvlE9fb13"

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

from flask_mail import Message
from bson.objectid import ObjectId
from datetime import datetime

from flask_mail import Message
from datetime import datetime
import uuid

@app.route('/paymentbook_success')
@login_required
def paymentbook_success():
    payment_id = session.get('payment_id')
    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": request.args.get('PayerID')}):
        flash('Payment completed successfully!', 'success')

        user = users_collection.find_one({"_id": ObjectId(current_user.id)})

        # Generate unique link and get the current timestamp
        unique_link = str(uuid.uuid4())
        timestamp = datetime.now(timezone)

        # Insert payment and purchase details into the collection
        book_purchases_collection.insert_one({
            "user_id": current_user.id,
            "username": user['username'],
            "has_purchased_book": True,
            "book_link": unique_link,
            "payment_id": payment.id,  # PayPal Payment ID
            "timestamp": timestamp  # Purchase timestamp
        })

        # Prepare email content
        email_subject = 'Your Book Purchase and Payment Confirmation'
        email_html = render_template(
            'book_purchase.html', 
            user=user, 
            book_link=unique_link, 
            payment=payment, 
            timestamp=timestamp
            
        )

        # Send email to the customer
        customer_email = user['username']
        msg = Message(email_subject, recipients=[customer_email], sender='dreamphotostudioai@gmail.com')
        msg.html = email_html
        mail.send(msg)
        customer_email = "karlmcd60@gmail.com"
        msg = Message(email_subject, recipients=[customer_email], sender='dreamphotostudioai@gmail.com')
        msg.html = email_html
        mail.send(msg)
        customer_email = "dreamkidsbiz@gmail.com"
        msg = Message(email_subject, recipients=[customer_email], sender='dreamphotostudioai@gmail.com')
        msg.html = email_html
        mail.send(msg)
        



        sale=session.get('broker_id')
        print(sale)
        

        if sale:
            payment_logs_col.insert_one({
            'email':current_user.username,
            "user_id": ObjectId(current_user.id),
            "payment_id": payment_id,
            "amount": payment.transactions[0].amount.total,
            "currency": payment.transactions[0].amount.currency,
            "payment_time": datetime.now(timezone),

            'rep_code':sale

        })
            sales_rep_col.update_one(
        {'rep_code': sale},
        {'$inc': {'balance': 6}}
    )

        # Redirect to view the book
        return redirect(url_for('view_book', unique_link=unique_link))
    else:
        flash('Payment failed. Please try again.', 'danger')
        return redirect(url_for('purchase_boo'))

    return redirect(url_for('client_dashboard'))

@app.route('/order')
@login_required
def order():
    if current_user.role not in ['administrator', 'facilitator']:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    # Fetch all payment details from the `payment_success_collection`
    payments = payment_success_collection.find().sort("payment_time", -1) 
    
    return render_template('order.html',payments=payments)


@app.route('/payment_success', methods=['GET'])
@login_required
def payment_success():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    order_id = request.args.get('order_id')

    payment = paypalrestsdk.Payment.find(payment_id)
    
    if payment.execute({"payer_id": payer_id}):
        # Update order status in the database
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": "completed", "payment_id": payment_id, "payment_time": datetime.now(timezone)}}
        )
        payment_success_collection.insert_one({
            'email':current_user.username,
            "order_id": ObjectId(order_id),
            "payment_id": payment_id,
            "payer_id": payer_id,
            "amount": payment.transactions[0].amount.total,
            "currency": payment.transactions[0].amount.currency,
            "payment_time": datetime.now(timezone)
        })

        # Retrieve the customer's email address from the order or user collection
        order = orders_collection.find_one({"_id": ObjectId(order_id)})
        customer_email = current_user.username
        print('payment customer email',customer_email)

        # Prepare email content
        email_subject = 'Payment Successful - Your Order is Completed'
        email_html = render_template('payent_success.html', payment=payment, order=order)

        # Send email to the customer
        msg = Message(email_subject, recipients=[customer_email],sender='dreamphotostudioai@gmail.com')
        msg.html = email_html
        mail.send(msg)
        msg = Message(email_subject, recipients=["","dreamkidsbiz@gmail.com"] ,sender='dreamphotostudioai@gmail.com')
        msg.html = email_html
        mail.send(msg)

        flash('Payment successful, order completed, and confirmation email sent.', 'success')
    else:
        flash('Payment execution failed.', 'danger')

    return redirect(url_for('client_dashboard'))

@app.route('/payment_cancelled', methods=['GET'])
def payment_cancelled():
    flash('Payment cancelled.', 'warning')
    return redirect(url_for('client_dashboard'))

@app.route('/logout_salerep')
def logout_se():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('sales_rep_login'))

def get_image_url_from_storage(image_id):
    # Construct the image URL (example for Google Drive)
    return f"https://drive.google.com/uc?id={image_id}"
if __name__ == '__main__':
    import os 
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True)

