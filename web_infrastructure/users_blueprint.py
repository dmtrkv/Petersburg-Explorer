import logging

from flask import Blueprint, render_template, redirect, session
from flask_login import login_user, logout_user, login_required, current_user

from data import db_session
from data.game_session import GameSession
from data.user import User
from email_scripts.code_generator import generate_code
from email_scripts.mail_sender import send_email
from forms.email_verification import EmailVerificationForm
from forms.login import LoginForm
from forms.register import RegisterForm
from forms.search import SearchForm

logging.basicConfig(level=logging.INFO, filename='logs.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

blueprint = Blueprint('users_blueprint', __name__, template_folder='templates')


@blueprint.route("/signup", methods=['GET', 'POST'])
def register():
    try:
        form = RegisterForm()
        if form.validate_on_submit():
            if len(form.name.data) < 3:
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message=f"Слишком короткое имя пользователя ({len(form.name.data)} < 3)")
            if len(form.name.data) > 9:
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message=f"Слишком длиное имя пользователя ({len(form.name.data)} > 9)")
            if form.password.data != form.password_again.data:
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Пароли не совпадают")
            db_sess = db_session.create_session()
            if db_sess.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Такой пользователь уже есть")

            verification_code = generate_code()

            session['Verification Code'] = verification_code
            session['User Email'] = form.email.data
            session['User Nickname'] = form.name.data
            session['User Password'] = form.password.data

            if send_email(session['User Email'], verification_code):
                # logging.info('EMAIL LETTER WAS SENT. REDIRECTED TO EMAIL VERIFICATION HANDLER')
                return redirect('/email_verification')

            else:
                return render_template('register.html',
                                       title='Регистрация',
                                       form=form,
                                       message="К сожалению, письмо не было отправлено. Попробуйте еще раз")

        return render_template('register.html', title='Регистрация', form=form)

    except Exception:
        return render_template('error.html')


@blueprint.route('/email_verification', methods=['GET', 'POST'])
def email_verification():
    try:
        form = EmailVerificationForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            if session['Verification Code'] == form.code.data:
                user = User(
                    name=session['User Nickname'],
                    lower_name=session['User Nickname'].lower(),
                    email=session['User Email']
                )
                user.set_password(session['User Password'])
                db_sess.add(user)
                db_sess.commit()

                logging.info('ADDED A NEW USER: name={}, email={}'.format(
                    user.name, user.email))

                return redirect('/login')

            else:
                return render_template('email_verification.html', title='Подтверждение', form=form,
                                       message='Неверный код подтверждения')

        return render_template('email_verification.html', title='Подтверждение', form=form)

    except Exception:
        logging.fatal("ERROR OCCURED DURING VERIFICATING USER'S EMAIL")
        return render_template('error.html')


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    try:
        form = LoginForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            user = db_sess.query(User).filter(
                User.email == form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/")

            return render_template('login.html',
                                   message="Неправильный логин или пароль",
                                   form=form)
        return render_template('login.html', title='Авторизация', form=form)

    except Exception:
        logging.fatal('ERROR OCCURED DURING LOGINING')
        return render_template('error.html')


@blueprint.route('/profile')
@login_required
def profile():
    try:
        return redirect('/users/{}'.format(current_user.name))

    except Exception as e:
        print(e)
        logging.fatal("ERROR OCCURED DURINGG SHOWING USER'S (id = {}) PROFILE".format(
            current_user.id))
        return render_template('error.html')


@blueprint.route('/delete_history')
@login_required
def delete_history():
    try:
        db_sess = db_session.create_session()

        game_sessions = db_sess.query(GameSession).filter(
            (GameSession.user_id == current_user.id))
        for sess in game_sessions:
            db_sess.delete(sess)
        db_sess.commit()
        return redirect('/profile')

    except Exception:
        logging.fatal("ERROR OCCURED DURINGG SHOWING USER'S (id = {}) PROFILE".format(
            current_user.id))
        return render_template('error.html')


@blueprint.route('/logout')
@login_required
def logout():
    try:
        logout_user()
        return redirect("/")

    except Exception:
        return render_template('error.html')


@blueprint.route('/users/<username>')
def view_user(username):
    try:
        db_sess = db_session.create_session()

        user = db_sess.query(User).filter(
            (User.name == username)).first()
        game_sessions = db_sess.query(GameSession).filter(
            (GameSession.user_id == user.id))

        return render_template("profile.html", game_sessions=reversed(list(game_sessions)), user=user)

    except Exception as e:
        print(e)
        logging.fatal("ERROR OCCURED DURINGG SHOWING USER'S (id = {}) PROFILE".format(
            current_user.id))
        return render_template('error.html')


@blueprint.route('/search', methods=['POST'])
def search():
    try:
        form = SearchForm()

        if form.validate_on_submit:
            searched = form.searched.data

            return redirect('/search/{}'.format(searched))
        else:
            pass

    except Exception as e:
        print(e)
        logging.fatal("ERROR OCCURED DURINGG SEARCHING USER'S (NAME = {}) PROFILE".format(
            searched))
        return render_template('error.html')


@blueprint.route('/search/<searched>', methods=['GET'])
def view_searched(searched):
    try:
        if searched:
            db_sess = db_session.create_session()
            users = db_sess.query(User).filter(
                User.lower_name.like('%' + searched.lower() + '%'))
            users = users.order_by(User.name).all()
        else:
            users = []
        return render_template('search.html', searched=searched, users=users)
    except Exception as e:
        print(e)
        logging.fatal("ERROR OCCURED DURINGG SEARCHING USER'S (NAME = {}) PROFILE".format(
            searched))
        return render_template('error.html')
