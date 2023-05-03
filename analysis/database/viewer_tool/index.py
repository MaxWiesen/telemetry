from flask import Flask, render_template, url_for, request, redirect

from analysis.database.server.one_time_injection import Injector
from analysis.database.sql_utils.db_handler import DBHandler

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/new_drive_day/', methods=['GET'])
def new_drive_day():
    day_id = Injector.create_from_table(table='drive_day', user='electric', data=request.args)
    return redirect(url_for('.new_event', day_id=day_id, method='new'))


@app.route('/new_event/', methods=['GET'])
def new_event():
    with DBHandler().connect(user='electric') as cnx:
        day_id = request.form.get('day_id', request.args['day_id'])
        with cnx.cursor() as cur:
            cur.execute(f'SELECT day_id FROM drive_day WHERE day_id = {day_id}')
            row = cur.fetchone()
    if not row and request.args['method'] == 'existing':
        return 'Drive Day ID not found in database. Try again.' + render_template('index.html')
    elif not row and request.args['method'] == 'new':
        return 'Error: Attempt to create new drive day failed. ID not found after creation. Inform developer.'
    return render_template('input_screen.html', day_id=day_id)


@app.route('/create_event/', methods=['POST'])
def create_event():
    event_id = Injector.create_from_table(table='event', user='electric', data=request.form)
    return render_template('event_tracker.html')

@app.route('/start_event/', methods=['POST'])
def start_event():
    status = Injector.inject(table='event', user='electric')

if __name__ == '__main__':
    app.run(debug=True)