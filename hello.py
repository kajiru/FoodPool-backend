import sqlite3
from flask import Flask
from flask import g
import cf_deployment_tracker
import os

# Emit Bluemix deployment event
cf_deployment_tracker.track()

app = Flask(__name__)

# On Bluemix, get the port number from the environment variable VCAP_APP_PORT
# When running this app on the local machine, default the port to 8080
port = int(os.getenv('VCAP_APP_PORT', 8080))

DATABASE = './database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/')
def hello_world():
    return 'Hello World! I am running on port ' + str(port)

@app.route('/placeOrder')
def placeOrder():
    return return app.send_static_file('/placeOrder/index.html')

def insert(table, fields=(), values=()):
    db = getattr(g, '_database', None)
    cur = db.cursor()
    query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        table,
        ', '.join(fields),
        ', '.join(['?'] * len(values))
    )
    cur.execute(query, values)
    db.commit()
    id = cur.lastrowid
    cur.close()
    return id

@app.route('/CreatePool', methods = ['POST'])
def CreatePool():
    db = get_db()
    insert("Pools", ("restaurant", "return_time", "num_orders", "pickup_location", "has_arrived"), ("in n out", "1478939164", "5", "room 383", False))
    return "Pool Created"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
