from flask import Flask
from backend.database import db #step3
app = None

def create_app():
    app = Flask(__name__)
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///management.sqlite3' #step3
    db.init_app(app) #step3
    app.app_context().push()
    return app

app = create_app()
from backend.controllers import * #step2
from backend.models import * #step4
 
if __name__ == '__main__':
# IN VIVA THIS NEEDS TO BE EXECUTED FIRST
    #db.create_all()
    #admin1 = User(username="admin123", email="admin@user.com", password_hash="1234", role="Admin")
    #db.session.add(admin1)
    #db.session.commit()
    app.run()


