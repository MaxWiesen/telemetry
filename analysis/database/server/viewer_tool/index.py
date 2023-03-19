import time

from flask import Flask, render_template, url_for, request, redirect

from analysis.database.server.one_time_injection import Injector
from analysis.database.sql_utils.db_handler import DBHandler

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/new_drive_day/', methods=['GET'])
def new_drive_day():
    if request.method == 'GET':
        day_id = Injector.create_drive_day(**request.args)
        return redirect(url_for('.new_event', day_id=day_id, method='new'))
    else:
        return 'How did you even get here?'


@app.route('/new_event/', methods=['GET'])
def new_event():
    cnx = DBHandler().connect()
    try:
        cur = cnx.cursor()
        cur.execute(f'SELECT day_id WHERE day_id = {request.args["day_id"]}')
        row = cur.fetchone()
        if not row and request.args['method'] == 'existing':
            return 'Drive Day ID not found in database. Try again.' + render_template('index.html')
        elif not row and request.args['method'] == 'new':
            return 'Error: Attempt to create new drive day failed. ID not found after creation. Inform developer.'
    except Exception as e:
        raise e
    finally:
        DBHandler.kill(cnx)
    return render_template('input_screen.html')

# @app.route('/create_event/', methods=['POST'])
# def create_event():


# @app.route('/dev/', methods=['GET', 'POST'])
# def dev_index():
#     if request.method == 'POST':
#         inputs = request.form
#         print(inputs)
#         return 'On Dev'
#     else:
#         return render_template('dev.html')


if __name__ == '__main__':
    app.run()