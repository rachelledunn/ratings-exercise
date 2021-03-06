"""Movie Ratings."""

from jinja2 import StrictUndefined

from flask import Flask, render_template, redirect, request, flash, session
from flask_debugtoolbar import DebugToolbarExtension

from model import User, Rating, Movie, connect_to_db, db


app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "ABC"

# Normally, if you use an undefined variable in Jinja2, it fails silently.
# This is horrible. Fix this so that, instead, it raises an error.
app.jinja_env.undefined = StrictUndefined


@app.route('/')
def index():
    """Homepage."""

    return render_template("homepage.html")


@app.route("/users")
def user_list():
    """Show list of users.""" 

    users = User.query.order_by(User.user_id.desc()).all()
    return render_template("user_list.html", users=users)


@app.route("/users/<int:user_id>")
def user_page(user_id):
    """Show more information about a single user.""" 
    
    user = User.query.get(user_id)

    return render_template("user_page.html", user=user)


@app.route('/movies')
def movie_list():
    """Show list of all movies in database"""

    # movies = Movie.query.order_by(Movie.title.asc()).all()
    movies = Movie.query.limit(50).all()

    return render_template("movies.html", movies=movies)


@app.route("/movies/<int:movie_id>", methods=['POST', 'GET'])
def movie_page(movie_id):
    """Show more information about a single user.""" 
    
    movie = Movie.query.get(movie_id)
    existing_rating = None 
    prediction = None
    rating_scores = [r.score for r in movie.ratings]
    avg_rating = float(sum(rating_scores)) / len(rating_scores)

    # print "current session: ", session['email']

    if "email" in session: #if logged in
        user_email = session['email']
        user = User.query.filter_by(email=user_email).first()
        if user:
            existing_rating = Rating.query.filter_by(movie_id=movie_id, user_id=user.user_id).first()
            print "Existing rating: ", existing_rating
    
        if existing_rating: #if user logged in and has rated movie

            if request.method == "POST": #if user hits submit 
                print "user exists, rating exists, post request: ", prediction    

                selected_rating = request.form['user_rating']
                update_rating = Rating.query.filter_by(movie_id=movie_id, user_id=user.user_id).first()
                update_rating.score = int(selected_rating)
                db.session.commit()

            else: # if they are on page and has rated movie (for debugging)
                print "user exists, rating exists, get request: ", prediction    


        elif user: # if user is logged in but has not rated movie
            if request.method == "POST": #if user hits submit (prediction goes away)    
                prediction = None
                selected_rating = request.form['user_rating']
                selected_rating = Rating(movie_id = movie_id, user_id= user.user_id, score=int(selected_rating))
                db.session.add(selected_rating)
                db.session.commit()
            else:
                print "A user when no rating exists: ", user
                prediction = user.predict_rating(movie) #prediction made until they submit (see if above)
                print "A prediction if no rating exists: ", prediction
    else:
        flash('You need to log in before rating!')
        redirect('/login')



    if prediction != None:
        # User hasn't scored; use our prediction if we made one
        users_cur_rating = prediction

    elif existing_rating:
        # User has already scored for real; use that
        users_cur_rating = existing_rating.score

    else:
        # User hasn't scored, and we couldn't get a prediction
        users_cur_rating = None

    # Get the eye's rating, either by predicting or using real rating

    the_eye = User.query.filter_by(email="the-eye@of-judgment.com").one()
    eye_rating = Rating.query.filter_by(
        user_id=the_eye.user_id, movie_id=movie.movie_id).first()

    if eye_rating is None:
        eye_rating = the_eye.predict_rating(movie)

    else:
        eye_rating = eye_rating.score

    if eye_rating and users_cur_rating:
        difference = abs(eye_rating - users_cur_rating)

    else:
        # We couldn't get an eye rating, so we'll skip difference
        difference = None

    BERATEMENT_MESSAGES = [
        "I suppose you don't have such bad taste after all.",
        "I regret every decision that I've ever made that has brought me" +
            " to listen to your opinion.",
        "Words fail me, as your taste in movies has clearly failed you.",
        "That movie is great. For a clown to watch. Idiot.",
        "Words cannot express the awfulness of your taste."
    ]

    if difference is not None:
        beratement = BERATEMENT_MESSAGES[int(difference)]

    else:
        beratement = None


    return render_template("movie_page.html", movie = movie, 
                                            user_rating = existing_rating, 
                                            average = avg_rating, 
                                            prediction = prediction, 
                                            beratement = beratement,
                                            eye_rating = eye_rating
                                            )



###########################
#SIGN UP/ LOGIN/ SIGN OUT 
###########################


@app.route("/signup")
def user_signup():
    """Sign up a new user."""

    return render_template("/signup.html")


@app.route("/signup-process", methods=['POST'])
def process_signup():
    """Route to process login for users."""

    entered_email = request.form['email']
    entered_pw = request.form['password']
    entered_pw2 = request.form['password2']
    
    user = User.query.filter_by(email=entered_email).first()

    if request.method == "POST":
        if user == None: # is not in User Table?
            print user 
            if entered_pw != entered_pw2:  #validate passwords
                flash("Your passwords did not match")
                return redirect("/signup")
            else:
            #update password into database
                new_user = User(password = entered_pw, email= entered_email) #???
                db.session.add(new_user)
                db.session.commit()
                print 'creating new user in Database.'
                print new_user, new_user.user_id
                session['email'] = entered_email
                flash("You are signed up %s!" % entered_email) 
                return redirect("/")
        else: 
            flash("You have already signed up with that email")
            return redirect('/login')


###################################

@app.route("/login")
def user_login():
    """Login page with form for users."""

    return render_template("login.html")


@app.route("/login-process", methods=['POST'])
def process_login():
    """Route to process login for users."""

    entered_email = request.form['email']
    entered_pw = request.form['password']
    
    user = User.query.filter_by(email=entered_email).one()

    if entered_pw == user.password:
        session['email'] = request.form['email']
        flash('You successfully logged in as %s!' % session['email'])
        return redirect("/users/%s" % user.user_id)
    else:
        flash("That is not the correct password!")
        return redirect('/login')

###################################

@app.route("/logout")
def process_logout():
    """Route to process logout for users."""

    session.pop('email')
    flash('You successfully logged out!')
    print session
    return redirect("/")



##################################


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the point
    # that we invoke the DebugToolbarExtension
    app.debug = True
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run()