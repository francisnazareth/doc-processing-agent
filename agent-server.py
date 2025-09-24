from flask import Flask, render_template, request, redirect, session
app = Flask(__name__)

@app.route('/')
def view_form():
    return render_template('hello.html')

@app.route('/handle_post', methods=['POST'])
def handle_post():
    qidFile = request.files['QID']

    if qidFile:
        print(f"Received file: {qidFile.filename}")
        qidFile.save(f"./uploads/{qidFile.filename}")

    username = request.form.get('username')
    password = request.form.get('password')
    return render_template('thanks.html', filename=qidFile.filename)

if __name__ == '__main__':
    app.run()