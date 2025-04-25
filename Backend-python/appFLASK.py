# Import necessary modules for Flask, MySQL, and CORS
from flask import Flask, request, jsonify, session
import mysql.connector
from mysql.connector import Error
from flask_cors import CORS

# Initialize the Flask app and enable CORS for all routes
app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])

# Set a secret key for managing sessions
app.secret_key = 'supersecretkey123!'

# Configuration for connecting to the MySQL database
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '7MDAHfa6mah()',
    'database': 'user_system'
}

# Function to connect to the database
def get_db():
    return mysql.connector.connect(**db_config)

# Function to update drivers' availability
def update_driver_availability(conn):
    try:
        cursor = conn.cursor()
        # Mark drivers as available if they don't have any pending orders
        cursor.execute("""
            UPDATE DeliveryPersonnel dp
            SET dp.status = 'Available'
            WHERE NOT EXISTS (
                SELECT 1 FROM Orders o
                WHERE o.delivery_person_id = dp.delivery_id AND o.delivery_status = 'Pending'
            )
        """)
        conn.commit()
        cursor.close()
    except Error as e:
        print("Driver update error:", str(e))

# User registration endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Insert a new user into the users table
        cursor.execute("""
            INSERT INTO users (name, address, phone, email, password, role)
            VALUES (%s, %s, %s, %s, %s, 'user')
        """, (data['name'], data['address'], data['phone'], data['email'], data['password']))
        conn.commit()
        return jsonify({'message': 'Registered successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# User login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    # Special login for admin
    if email == 'admin@a.a' and password == '123':
        session.clear()
        session['admin'] = True
        return jsonify({'message': 'Admin login successful', 'role': 'admin'}), 200

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        # Fetch user info from the database
        cursor.execute("SELECT * FROM users WHERE email = %s AND is_deleted = FALSE", (email,))
        user = cursor.fetchone()

        # Check if user exists and password matches
        if user and user['password'] == password:
            session.clear()
            session['email'] = user['email']
            session['name'] = user['name']
            session['role'] = user['role']
            session['user_id'] = user['customer_id']
            if user['role'] == 'restaurant_admin':
                session['restaurant_id'] = user.get('restaurant_id')
            return jsonify({
                'message': 'Login successful',
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'restaurant_id': user.get('restaurant_id')
            }), 200
        else:
            return jsonify({'error': 'Invalid email or password'}), 401
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Log the user out and clear the session
@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'}), 200

# Fetch session user information
@app.route('/session-user', methods=['GET'])
def session_user():
    if session.get('admin'):
        return jsonify({'email': 'admin@a.a', 'name': 'Admin', 'role': 'admin'}), 200
    elif 'email' in session:
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s AND is_deleted = FALSE", (session['email'],))
            user = cursor.fetchone()
            if not user:
                session.clear()
                return jsonify({'error': 'User not found or deleted'}), 401

            response = {
                'email': user['email'],
                'name': user['name'],
                'role': user['role']
            }
            if user['role'] == 'restaurant_admin':
                response['restaurant_id'] = user.get('restaurant_id')
            return jsonify(response), 200

        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({'error': 'No user logged in'}), 401

# Add a new restaurant (admin only)
@app.route('/admin/add-restaurant', methods=['POST'])
def add_restaurant():
    data = request.get_json()
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Restaurants (name, cuisine_type, address)
            VALUES (%s, %s, %s)
        """, (data['name'], data['cuisine_type'], data['address']))
        conn.commit()
        return jsonify({'message': 'Restaurant added successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Delete a restaurant (admin only)
@app.route('/admin/delete-restaurant', methods=['POST'])
def delete_restaurant():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    restaurant_id = data.get('restaurant_id')

    if not restaurant_id:
        return jsonify({'error': 'Restaurant ID is required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Restaurants WHERE restaurant_id = %s", (restaurant_id,))
        conn.commit()
        return jsonify({'message': 'Restaurant deleted'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Return all restaurants to display
@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Restaurants")
        return jsonify({'restaurants': cursor.fetchall()}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Return menu items for a specific restaurant
@app.route('/menus/<int:restaurant_id>', methods=['GET'])
def get_menu(restaurant_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM Menus
            WHERE restaurant_id = %s
              AND availability = 'In Stock'
              AND is_deleted = FALSE
        """, (restaurant_id,))
        return jsonify({'menu': cursor.fetchall()}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Add a new menu item
@app.route('/admin/add-menu-item', methods=['POST'])
def add_menu_item():
    data = request.get_json()
    restaurant_id = data.get('restaurant_id')
    dish_name = data.get('dish_name')
    description = data.get('description')
    price = data.get('price')
    availability = data.get('availability')

    if not all([restaurant_id, dish_name, price, availability]):
        return jsonify({'error': 'Missing fields'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Menus (restaurant_id, dish_name, description, price, availability)
            VALUES (%s, %s, %s, %s, %s)
        """, (restaurant_id, dish_name, description, price, availability))
        conn.commit()
        return jsonify({'message': 'Menu item added successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
# Add a new delivery personnel (admin only)
@app.route('/admin/add-delivery-personnel', methods=['POST'])
def add_delivery_personnel():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone')

    if not name or not phone:
        return jsonify({'error': 'Name and phone are required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO DeliveryPersonnel (name, phone) VALUES (%s, %s)", (name, phone))
        conn.commit()
        return jsonify({'message': 'Delivery personnel added'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Delete a delivery personnel (admin only)
@app.route('/admin/delete-delivery-personnel', methods=['POST'])
def delete_delivery_personnel():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    phone = data.get('phone')
    if not phone:
        return jsonify({'error': 'Phone number required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM DeliveryPersonnel WHERE phone = %s", (phone,))
        conn.commit()
        return jsonify({'message': 'Delivery personnel deleted'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Get orders for a specific restaurant (restaurant admin only)
@app.route('/restaurant/orders', methods=['GET'])
def get_restaurant_orders():
    if 'role' not in session or session['role'] != 'restaurant_admin':
        return jsonify({'error': 'Unauthorized'}), 403

    restaurant_id = session.get('restaurant_id')
    if not restaurant_id:
        return jsonify({'error': 'Restaurant ID not found in session'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Fetch orders linked to the admin's restaurant
        cursor.execute("""
            SELECT o.order_id, o.order_date, o.delivery_status, o.total_amount,
                   u.name AS customer_name, d.name AS delivery_person
            FROM Orders o
            JOIN users u ON o.customer_id = u.customer_id
            LEFT JOIN DeliveryPersonnel d ON o.delivery_person_id = d.delivery_id
            JOIN Order_Items oi ON o.order_id = oi.order_id
            JOIN Menus m ON oi.menu_id = m.menu_id
            WHERE m.restaurant_id = %s
            GROUP BY o.order_id
            ORDER BY o.order_date DESC
        """, (restaurant_id,))
        orders = cursor.fetchall()

        return jsonify({'orders': orders}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Cancel a specific order (user only)
@app.route('/cancel-order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401

        # Check if the order belongs to the current user
        cursor.execute("SELECT * FROM Orders WHERE order_id = %s AND customer_id = %s", (order_id, session['user_id']))
        order = cursor.fetchone()
        if not order:
            return jsonify({'error': 'Unauthorized'}), 403

        # Cancel the order
        cursor.execute("UPDATE Orders SET delivery_status = 'Cancelled' WHERE order_id = %s", (order_id,))
        conn.commit()
        update_driver_availability(conn)
        return jsonify({'message': 'Order cancelled'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Manually reset driver availability status
@app.route('/reset-drivers', methods=['POST'])
def reset_drivers():
    try:
        conn = get_db()
        update_driver_availability(conn)
        conn.close()
        return jsonify({'message': 'Drivers refreshed'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500

# Mark an order as delivered (restaurant admin only)
@app.route('/restaurant/mark-ready/<int:order_id>', methods=['POST'])
def mark_order_ready(order_id):
    if 'role' not in session or session['role'] != 'restaurant_admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Update order status to Delivered
        cursor.execute("UPDATE Orders SET delivery_status = 'Delivered' WHERE order_id = %s", (order_id,))
        conn.commit()

        # Update driver status again
        update_driver_availability(conn)
        return jsonify({'message': 'Order marked as Delivered'}), 200

    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Get ratings for a specific restaurant
@app.route('/ratings/<int:restaurant_id>', methods=['GET'])
def get_ratings(restaurant_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT r.rating, r.comment, r.created_at, u.name AS user_name
            FROM Ratings r
            JOIN users u ON r.user_id = u.customer_id
            WHERE r.restaurant_id = %s
            ORDER BY r.created_at DESC
        """, (restaurant_id,))

        ratings = cursor.fetchall()
        return jsonify({'ratings': ratings}), 200

    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Submit a new rating for a delivered order
@app.route('/rate-order', methods=['POST'])
def rate_order():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    order_id = data.get('order_id')
    rating = data.get('rating')
    comment = data.get('comment')

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get the restaurant for the given order
        cursor.execute("""
            SELECT m.restaurant_id
            FROM Order_Items oi
            JOIN Menus m ON oi.menu_id = m.menu_id
            WHERE oi.order_id = %s
            LIMIT 1
        """, (order_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({'error': 'Invalid order'}), 400

        restaurant_id = row['restaurant_id']
        user_id = session['user_id']

        # Check if this order has already been rated
        cursor.execute("SELECT * FROM Ratings WHERE order_id = %s", (order_id,))
        if cursor.fetchone():
            return jsonify({'error': 'You already rated this order'}), 400

        # Insert the new rating
        cursor.execute("""
            INSERT INTO Ratings (restaurant_id, user_id, rating, comment, order_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (restaurant_id, user_id, rating, comment, order_id))

        conn.commit()
        return jsonify({'message': 'Thanks for your rating!'}), 200

    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Soft delete a user (admin only)
@app.route('/admin/delete-user', methods=['POST'])
def delete_user():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Perform a soft delete by marking as deleted
        cursor.execute("UPDATE users SET is_deleted = TRUE WHERE email = %s", (email,))
        conn.commit()

        return jsonify({'message': 'User marked as deleted'}), 200

    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Update restaurant info (admin only)
@app.route('/admin/update-restaurant', methods=['POST'])
def update_restaurant():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    restaurant_id = data.get('restaurant_id')
    name = data.get('name')
    cuisine_type = data.get('cuisine_type')
    address = data.get('address')

    if not restaurant_id:
        return jsonify({'error': 'Restaurant ID is required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        # Update the restaurant's details
        cursor.execute("""
            UPDATE Restaurants
            SET name = %s, cuisine_type = %s, address = %s
            WHERE restaurant_id = %s
        """, (name, cuisine_type, address, restaurant_id))
        conn.commit()
        return jsonify({'message': 'Restaurant updated successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
# Submit a rating for a restaurant (requires user to be logged in)
@app.route('/submit-rating', methods=['POST'])
def submit_rating():
    data = request.get_json()

    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Insert the submitted rating into the Ratings table
        cursor.execute("""
            INSERT INTO Ratings (order_id, restaurant_id, user_id, rating, comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['order_id'],
            data['restaurant_id'],
            session['user_id'],
            data['rating'],
            data.get('comment', '')  # default to empty comment if not provided
        ))
        conn.commit()
        return jsonify({'message': 'Rating submitted'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Update the profile of the currently logged-in user
@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Update name, address, and phone for the logged-in user
        cursor.execute("""
            UPDATE users
            SET name = %s, address = %s, phone = %s
            WHERE customer_id = %s
        """, (data['name'], data['address'], data['phone'], session['user_id']))
        conn.commit()
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Get the current logged-in user's profile information
@app.route('/get-user', methods=['GET'])
def get_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Fetch name, address, phone, and email from users table
        cursor.execute("SELECT name, address, phone, email FROM users WHERE customer_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        return jsonify({'user': user}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Assign an existing user as a restaurant admin (admin only)
@app.route('/admin/assign-restaurant-admin', methods=['POST'])
def assign_restaurant_admin():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    email = data.get('email')
    restaurant_id = data.get('restaurant_id')

    if not email or not restaurant_id:
        return jsonify({'error': 'Email and restaurant ID required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if the user exists and is not deleted
        cursor.execute("SELECT * FROM users WHERE email = %s AND is_deleted = FALSE", (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Set role to 'restaurant_admin' and assign the restaurant ID
        cursor.execute("""
            UPDATE users
            SET role = 'restaurant_admin', restaurant_id = %s
            WHERE email = %s
        """, (restaurant_id, email))
        conn.commit()

        return jsonify({'message': 'User assigned as restaurant admin'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Start the Flask development server
if __name__ == '__main__':
    app.run(debug=True)
