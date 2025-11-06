from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import argparse
import os
from models import init_db, get_db, close_db
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'hotel.db')


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login', next=request.url))
        return fn(*args, **kwargs)
    return wrapper


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin_user = os.environ.get('ADMIN_USER', 'admin')
        admin_pass = os.environ.get('ADMIN_PASS', 'admin')
        if username == admin_user and password == admin_pass:
            session['admin'] = True
            flash('Logged in as admin', 'success')
            next_url = request.args.get('next') or url_for('admin_rooms')
            return redirect(next_url)
        else:
            flash('Invalid credentials', 'danger')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Logged out', 'success')
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_index():
    return redirect(url_for('admin_rooms'))


@app.route('/admin/rooms')
@admin_required
def admin_rooms():
    db = get_db()
    # pagination and search for rooms
    page = int(request.args.get('page', 1))
    per_page = 10
    q = request.args.get('q', '').strip()
    params = []
    where = ''
    if q:
        where = "WHERE number LIKE ? OR type LIKE ?"
        likeq = f"%{q}%"
        params.extend([likeq, likeq])

    count_sql = f"SELECT COUNT(*) FROM rooms {where}"
    cur = db.execute(count_sql, params)
    total = cur.fetchone()[0]
    offset = (page - 1) * per_page
    sql = f"SELECT * FROM rooms {where} ORDER BY id DESC LIMIT ? OFFSET ?"
    cur = db.execute(sql, params + [per_page, offset])
    rooms = cur.fetchall()
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template('admin/rooms_list.html', rooms=rooms, page=page, total_pages=total_pages, q=q)


@app.route('/admin/rooms/new', methods=['GET', 'POST'])
@admin_required
def admin_new_room():
    if request.method == 'POST':
        number = request.form.get('number')
        type_ = request.form.get('type')
        price = request.form.get('price')
        available = 1 if request.form.get('available') == 'on' else 0
        db = get_db()
        db.execute('INSERT INTO rooms (number, type, price, available) VALUES (?, ?, ?, ?)', (number, type_, price, available))
        db.commit()
        flash('Room added', 'success')
        return redirect(url_for('admin_rooms'))
    return render_template('admin/room_form.html', action='New', room=None)


@app.route('/admin/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_room(room_id):
    db = get_db()
    if request.method == 'POST':
        number = request.form.get('number')
        type_ = request.form.get('type')
        price = request.form.get('price')
        available = 1 if request.form.get('available') == 'on' else 0
        db.execute('UPDATE rooms SET number=?, type=?, price=?, available=? WHERE id=?', (number, type_, price, available, room_id))
        db.commit()
        flash('Room updated', 'success')
        return redirect(url_for('admin_rooms'))
    cur = db.execute('SELECT * FROM rooms WHERE id = ?', (room_id,))
    room = cur.fetchone()
    if not room:
        flash('Room not found', 'danger')
        return redirect(url_for('admin_rooms'))
    return render_template('admin/room_form.html', action='Edit', room=room)


@app.route('/admin/rooms/<int:room_id>/delete', methods=['POST'])
@admin_required
def admin_delete_room(room_id):
    db = get_db()
    db.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
    db.commit()
    flash('Room deleted', 'success')
    return redirect(url_for('admin_rooms'))


@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    db = get_db()
    # pagination and search
    page = int(request.args.get('page', 1))
    per_page = 10
    q = request.args.get('q', '').strip()
    params = []
    where = ''
    if q:
        where = "WHERE b.customer_name LIKE ? OR r.number LIKE ?"
        likeq = f"%{q}%"
        params.extend([likeq, likeq])

    # total count
    count_sql = f"SELECT COUNT(*) FROM bookings b JOIN rooms r ON b.room_id = r.id {where}"
    cur = db.execute(count_sql, params)
    total = cur.fetchone()[0]

    offset = (page - 1) * per_page
    sql = f"SELECT b.id, b.customer_name, b.checkin, b.checkout, b.room_id, b.status, r.number as room_number FROM bookings b JOIN rooms r ON b.room_id = r.id {where} ORDER BY b.id DESC LIMIT ? OFFSET ?"
    params_with_limit = params + [per_page, offset]
    cur = db.execute(sql, params_with_limit)
    bookings = cur.fetchall()
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template('admin/bookings_list.html', bookings=bookings, page=page, total_pages=total_pages, q=q)


@app.route('/admin/bookings/<int:booking_id>/delete', methods=['POST'])
@admin_required
def admin_delete_booking(booking_id):
    db = get_db()
    # find booking to get room id
    cur = db.execute('SELECT room_id FROM bookings WHERE id = ?', (booking_id,))
    row = cur.fetchone()
    if row:
        room_id = row['room_id']
        db.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
        # mark room available again
        db.execute('UPDATE rooms SET available = 1 WHERE id = ?', (room_id,))
        db.commit()
        flash('Booking cancelled and room freed', 'success')
    else:
        flash('Booking not found', 'danger')
    return redirect(url_for('admin_bookings'))


@app.route('/admin/bookings/<int:booking_id>', methods=['GET', 'POST'])
@admin_required
def admin_booking_detail(booking_id):
    db = get_db()
    cur = db.execute('SELECT b.*, r.number as room_number FROM bookings b JOIN rooms r ON b.room_id = r.id WHERE b.id = ?', (booking_id,))
    booking = cur.fetchone()
    if not booking:
        flash('Booking not found', 'danger')
        return redirect(url_for('admin_bookings'))
    if request.method == 'POST':
        new_status = request.form.get('status')
        # update booking status
        db.execute('UPDATE bookings SET status = ? WHERE id = ?', (new_status, booking_id))
        # adjust room availability based on status
        room_id = booking['room_id']
        if new_status == 'cancelled' or new_status == 'checked-out':
            db.execute('UPDATE rooms SET available = 1 WHERE id = ?', (room_id,))
        elif new_status in ('booked', 'checked-in'):
            db.execute('UPDATE rooms SET available = 0 WHERE id = ?', (room_id,))
        db.commit()
        flash('Booking updated', 'success')
        return redirect(url_for('admin_booking_detail', booking_id=booking_id))
    return render_template('admin/booking_detail.html', booking=booking)



@app.route('/')
def index():
    db = get_db()
    cur = db.execute('SELECT * FROM rooms')
    rooms = cur.fetchall()
    return render_template('index.html', rooms=rooms)


@app.route('/rooms')
def rooms():
    db = get_db()
    cur = db.execute('SELECT * FROM rooms')
    rooms = cur.fetchall()
    return render_template('rooms.html', rooms=rooms)


@app.route('/book', methods=['POST'])
def book():
    name = request.form.get('name')
    room_id = request.form.get('room_id')
    checkin = request.form.get('checkin')
    checkout = request.form.get('checkout')
    db = get_db()
    # basic server-side validation
    if not (name and room_id and checkin and checkout):
        flash('Please provide name, check-in and check-out dates.', 'danger')
        return redirect(url_for('index'))

    # validate date format and ordering (expect YYYY-MM-DD)
    try:
        ci = datetime.strptime(checkin, '%Y-%m-%d').date()
        co = datetime.strptime(checkout, '%Y-%m-%d').date()
    except ValueError:
        flash('Dates must be in YYYY-MM-DD format.', 'danger')
        return redirect(url_for('index'))

    if ci >= co:
        flash('Check-out must be after check-in.', 'danger')
        return redirect(url_for('index'))

    # ensure room exists and is available
    cur = db.execute('SELECT available FROM rooms WHERE id = ?', (room_id,))
    row = cur.fetchone()
    if not row:
        flash('Selected room does not exist.', 'danger')
        return redirect(url_for('index'))
    if row['available'] == 0:
        flash('Selected room is not available.', 'warning')
        return redirect(url_for('index'))

    # create booking with default status 'booked'
    db.execute('INSERT INTO bookings (customer_name, room_id, checkin, checkout, status) VALUES (?, ?, ?, ?, ?)',
               (name, room_id, checkin, checkout, 'booked'))
    db.execute('UPDATE rooms SET available = 0 WHERE id = ?', (room_id,))
    db.commit()
    # flash a confirmation message to show after redirect
    flash(f'Room {room_id} booked successfully for {name} ({checkin} → {checkout})', 'success')
    return redirect(url_for('index'))


@app.route('/bookings')
def bookings():
    db = get_db()
    cur = db.execute('SELECT b.id, b.customer_name, b.checkin, b.checkout, r.number as room_number FROM bookings b JOIN rooms r ON b.room_id = r.id')
    bookings = cur.fetchall()
    return render_template('bookings.html', bookings=bookings)


@app.teardown_appcontext
def teardown(exception):
    close_db()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--init-db', action='store_true', help='Initialize the database')
    args = parser.parse_args()
    if args.init_db:
        init_db(app)
        print('Initialized the database at', app.config['DATABASE'])
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    main()
