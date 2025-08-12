import os, traceback
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from models import db, Quiz, Question, Result
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# SQLite DB file inside project dir
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'quiz.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# ---------------- Student routes ----------------
@app.route('/')
def home():
    active = Quiz.query.filter_by(active=True).first()
    return render_template('index.html', active=active)

@app.route('/welcome', methods=['GET', 'POST'])
def welcome():
    active = Quiz.query.filter_by(active=True).first()
    if not active:
        flash("No active quiz right now. Please contact admin.", "warning")
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form.get('username', '').strip()
        if not name:
            flash("Enter a name to continue.", "warning")
            return redirect(url_for('welcome'))
        session['username'] = name
        session['quiz_id'] = active.id
        return redirect(url_for('quiz'))
    return render_template('welcome.html', quiz=active)

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    try:
        quiz_id = session.get('quiz_id')
        username = session.get('username')
        active = Quiz.query.filter_by(active=True).first()
        if not active or not quiz_id or active.id != quiz_id or not username:
            flash("Please enter name and start the active quiz.", "warning")
            return redirect(url_for('home'))

        quiz = Quiz.query.get_or_404(quiz_id)
        questions = quiz.questions

        if not questions or len(questions) == 0:
            flash("No questions available in the active quiz. Please contact admin.", "warning")
            return redirect(url_for('home'))

        if request.method == 'POST':
            answers = request.get_json() or {}
            score = 0
            total = len(questions)
            for q in questions:
                sel = answers.get(str(q.id))
                if sel and sel == q.correct_option:
                    score += 1
            # store result
            res = Result(quiz_id=quiz.id, username=username, score=score, total=total, timestamp=datetime.utcnow())
            db.session.add(res)
            db.session.commit()
            return jsonify({"status": "ok", "score": score, "total": total})

        # Convert question objects to plain dicts for JSON serialization in template
        question_dicts = []
        for q in questions:
            question_dicts.append({
                "id": q.id,
                "text": q.text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_option": q.correct_option
            })

        return render_template('quiz.html', quiz=quiz, questions=question_dicts)
    except Exception:
        traceback.print_exc()
        flash("An internal error occurred. Check server logs.", "error")
        return redirect(url_for('home'))

@app.route('/result')
def result():
    username = session.get('username')
    quiz_id = session.get('quiz_id')
    if not username or not quiz_id:
        return redirect(url_for('home'))
    res = Result.query.filter_by(username=username, quiz_id=quiz_id).order_by(Result.id.desc()).first()
    return render_template('result.html', result=res)

@app.route('/winner-board')
def winner_board():
    active = Quiz.query.filter_by(active=True).first()
    if not active:
        flash("No active quiz currently.", "warning")
        return redirect(url_for('home'))
    top = Result.query.filter_by(quiz_id=active.id).order_by(Result.score.desc(), Result.timestamp.asc()).limit(10).all()
    return render_template('winner_board.html', top_results=top, quiz=active)


# ---------------- Admin routes ----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Incorrect password"
    return render_template('admin_login.html', error=error)

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()
    active = Quiz.query.filter_by(active=True).first()
    return render_template('admin_dashboard.html', quizzes=quizzes, active=active)

@app.route('/admin/create-quiz', methods=['GET', 'POST'])
def create_quiz():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        title = request.form.get('title') or f"Quiz {datetime.utcnow().isoformat()}"
        try:
            time_per_question = int(request.form.get('time_per_question', 20))
        except ValueError:
            time_per_question = 20
        # deactivate others
        Quiz.query.update({Quiz.active: False})
        newq = Quiz(title=title, time_per_question=time_per_question, active=True)
        db.session.add(newq)
        db.session.commit()
        # clear any previous results for this new quiz (fresh start)
        Result.query.filter_by(quiz_id=newq.id).delete()
        db.session.commit()
        flash("Quiz created and set active.", "success")
        return redirect(url_for('admin_dashboard'))
    return render_template('add_question.html', create_quiz=True)

@app.route('/admin/set-active/<int:quiz_id>', methods=['POST', 'GET'])
def set_active(quiz_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    Quiz.query.update({Quiz.active: False})
    q = Quiz.query.get_or_404(quiz_id)
    q.active = True
    db.session.commit()
    # clear results for this quiz so winner board resets
    Result.query.filter_by(quiz_id=q.id).delete()
    db.session.commit()
    flash(f"Quiz '{q.title}' is now active (results cleared).", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-quiz/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    q = Quiz.query.get_or_404(quiz_id)
    db.session.delete(q)
    db.session.commit()
    flash("Quiz deleted.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/quiz/<int:quiz_id>/add-question', methods=['GET', 'POST'])
def admin_add_question(quiz_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        a = request.form.get('option_a', '').strip()
        b = request.form.get('option_b', '').strip()
        c = request.form.get('option_c', '').strip()
        d = request.form.get('option_d', '').strip()
        correct = request.form.get('correct_option', '').strip()
        if not (text and a and b and correct):
            flash("Question, option A, option B and correct option are required.", "warning")
            return redirect(url_for('admin_add_question', quiz_id=quiz.id))
        q = Question(quiz_id=quiz.id, text=text, option_a=a, option_b=b, option_c=c or None, option_d=d or None, correct_option=correct)
        db.session.add(q)
        db.session.commit()
        flash("Question added.", "success")
        return redirect(url_for('admin_dashboard'))
    return render_template('add_question.html', quiz=quiz)

@app.route('/admin/question/<int:q_id>/edit', methods=['GET', 'POST'])
def admin_edit_question(q_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    q = Question.query.get_or_404(q_id)
    if request.method == 'POST':
        q.text = request.form.get('text', q.text)
        q.option_a = request.form.get('option_a', q.option_a)
        q.option_b = request.form.get('option_b', q.option_b)
        q.option_c = request.form.get('option_c', q.option_c)
        q.option_d = request.form.get('option_d', q.option_d)
        q.correct_option = request.form.get('correct_option', q.correct_option)
        db.session.commit()
        flash("Question updated.", "success")
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_question.html', question=q)

@app.route('/admin/question/<int:q_id>/delete', methods=['POST'])
def admin_delete_question(q_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    q = Question.query.get_or_404(q_id)
    db.session.delete(q)
    db.session.commit()
    flash("Question deleted.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clear-results/<int:quiz_id>', methods=['POST'])
def admin_clear_results(quiz_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    Result.query.filter_by(quiz_id=quiz_id).delete()
    db.session.commit()
    flash("Results cleared for this quiz.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

# Generic error handler to log tracebacks
@app.errorhandler(500)
def handle_500(e):
    traceback.print_exc()
    return render_template('error.html', message="Internal Server Error - check server logs."), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)

