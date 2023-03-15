from flask import Flask, render_template, request

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        inputs = request.form
        print(inputs)
        return 'Data injected'
    else:
        return render_template('index.html')

@app.route('/dev/', methods=['GET', 'POST'])
def dev_index():
    if request.method == 'POST':
        inputs = request.form
        print(inputs)
        return 'On Dev'
    else:
        return render_template('dev.html')


if __name__ == '__main__':
    app.run(debug=True)