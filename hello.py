from rapidconnect import RapidConnect
from flask import request
rapid = RapidConnect('foodpool', '521832dd-f936-404c-a121-9ee6781cabea');
from flask import Flask
from flask import g
import cf_deployment_tracker
import sqlite3
import os

import uuid,os
from flask import Flask, jsonify, request

#Square Modules
import squareconnect
from squareconnect.rest import ApiException
from squareconnect.apis.transaction_api import TransactionApi

access_token = 'sandbox-sq0atb-vwQUCVDYaJrgubwxf5VnkQ'

location_id = 'CBASEMe2x6MwoifEPrKa8Toz5gk'

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
    return app.send_static_file('index.html')

@app.route('/processOrder', methods = ['POST'])
def processOrder():
    if request.method == 'POST':
        nonce = request.form['nonce']
        name  = request.form['username']
        order  = request.form['order']
        cost  = int(request.form['cost'])
        phoneNumber  = request.form['phoneNumber']
        userDetails = {'name':name, 'order':order, 'cost':cost, 'phoneNumber':phoneNumber}

        print(userDetails)

        success = processTransaction(nonce,cost)
        if success:

            db = get_db()
#            init_db()
            insert("Orders", ("name", "food_order", "total", "phone"), (userDetails["name"], userDetails["order"], userDetails["cost"], userDetails["phoneNumber"]))
            return app.send_static_file('thankYou.html')
        else:
            return app.send_static_file('index.html')
def processTransaction(nonce,cost):
        
    api_instance = TransactionApi()
    # Every payment you process with the SDK must have a unique idempotency key.
    # If you're unsure whether a particular payment succeeded, you can reattempt
    # it with the same idempotency key without worrying about double charging
    # the buyer.
    idempotency_key = str(uuid.uuid1())

    # Monetary amounts are specified in the smallest unit of the applicable currency.
    # This amount is in cents. It's also hard-coded for $1.00, which isn't very useful.
    amount = {'amount':cost, 'currency': 'USD'}
    body = {'idempotency_key': idempotency_key, 'card_nonce': nonce, 'amount_money': amount}

    # The SDK throws an exception if a Connect endpoint responds with anything besides
    # a 200-level HTTP code. This block catches any exceptions that occur from the request.
    try:
      # Charge
      api_response = api_instance.charge(access_token, location_id, body)
      res = api_response.transaction
      #Push to Db  #TODO
      return True
    except ApiException as e:
      res = "Exception when calling TransactionApi->charge: {}".format(e)
      print(res); #For Debuggig
      return False


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
    json = request.get_json()
    db = get_db()
    init_db()
    print json
    insert("Pools", ("restaurant", "return_time", "num_orders", "pickup_location", "has_arrived"), (json["restaurant"], json["return_time"], json["num_orders"], json["pickup_location"], False))
    return jsonify(**{"order_link": "https://foodpool.mybluemix.net/"})

@app.route('/GetConfirmedOrders')
def GetConfirmedOrders():
    res = query_db("Select * from Orders")
    res = [{"name": row[0], "food_order": row[1], "total": row[2], "phone": row[3]} for row in res]
    res = {"orders": res}
    print res
    return jsonify(**res)


@app.route('/PoolArrived', methods = ['POST'])
def PoolArrived():
    orders = query_db("select phone from Orders")
    print orders
    for order in orders:
        to = order[0]
        try:
            result = rapid.call('Twilio', 'sendSms', { 
                'accountSid': 'ACaf68211f718a1a979fe9666f2ba4e016',
                'accountToken': 'fbb7e37935978d397ba905b2ded0e08a',
                'from': '(415) 802-0448',
                'to': to,
                'applicationSid': '',
                'statusCallback': '',
                'messagingServiceSid': 'MGc057bf228a454e212e5b92af273d6adb',
                'body': 'Your order is ready!'
                #'maxPrice': '',
                #'provideFeedback': ''
            });
        except:
            pass
    return "Done"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
