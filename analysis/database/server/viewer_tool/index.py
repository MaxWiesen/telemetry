from flask import Flask, render_template, request, redirect
from analysis.database.server.one_time_injection import Injector

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/new_drive_day/', methods=['GET'])
def new_drive_day():
    if request.method == 'GET':
        Injector.create_drive_day(**request.args)
        return redirect('/new_event/')
    else:
        return 'How did you even get here?'


@app.route('/new_event/', methods=['GET', 'POST'])
def new_event():

    # TODO: Check if drive_day_id exists in DB
    return render_template('input_screen.html')

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