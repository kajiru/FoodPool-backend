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
    create_index()
    return app.send_static_file('index.html')

@app.route('/processOrder', methods = ['POST'])
def processOrder():
    if request.method == 'POST':
        nonce = request.form['nonce']
        name  = request.form['username']
        order  = request.form['meal']
        cost  = int(float(request.form['cost'][1:]) * 100)
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
    orders = query_db("select phone, name from Orders")
    location = query_db("select pickup_location from Pools")[0][0]
    print orders
    for order in orders:
        to = order[0]
        name = order[1]
        try:
            result = rapid.call('Twilio', 'sendSms', {
                'accountSid': 'ACaf68211f718a1a979fe9666f2ba4e016',
                'accountToken': 'fbb7e37935978d397ba905b2ded0e08a',
                'from': '(415) 802-0448',
                'to': to,
                'applicationSid': '',
                'statusCallback': '',
                'messagingServiceSid': 'MGc057bf228a454e212e5b92af273d6adb',
                'body': 'Hi ' + name + ', your order has been delivered: you can pick it up at ' + location
                #'maxPrice': '',
                #'provideFeedback': ''
            });
        except:
            pass
    return "Done"

def create_index():
    restaurant = query_db("select restaurant from Pools")[0][0]

    meals = {"In-N-Out": """
      <option value="Hamburger with Onion" > Hamburger with Onion - $5.25</option>
      <option value="Cheeseburger with Onion"> Cheeseburger with Onion - $5.55</option>
      <option value="Double-Double with Onion"> Double-Double with Onion - $6.60</option>
    """,
    "Chipotle": """
      <option value="Chicken Burrito Bowl" > Chicken Burrito Bowl - $7.15</option>
      <option value="Steak Burrito Bowl"> Steak Burrito Bowl - $8.25</option>
      <option value="Veggie Burrito "> Veggie Burrito - $7.15</option>
    """}
    meal = ""
    try:
        meal = meals[restaurant]
    except:
        meal = meals["Chipotle"]

    index = """<html>
    <head>
      <title>Payment Form</title>
      <link rel="stylesheet" href="static/bootstrap.css" />
      <script type="text/javascript" src="https://js.squareup.com/v2/paymentform"></script>
      <script>
        var sqPaymentForm = new SqPaymentForm({

          // Replace this value with your application\'s ID (available from the merchant dashboard).
          // If you\'re just testing things out, replace this with your _Sandbox_ application ID,
          // which is also available there.
          applicationId: \'sandbox-sq0idp-R21hfTdwB0CPoGpL5JdsyQ\',
          inputClass: \'sq-input\',
          cardNumber: {
            elementId: \'sq-card-number\',
            placeholder: "0000 0000 0000 0000"
          },
          cvv: {
            elementId: \'sq-cvv\',
            placeholder: \'CVV\'
          },
          expirationDate: {
            elementId: \'sq-expiration-date\',
            placeholder: \'MM/YY\'
          },
          postalCode: {
            elementId: \'sq-postal-code\',
            placeholder: \'Postal Code\'
          },
          inputStyles: [

            // Because this object provides no value for mediaMaxWidth or mediaMinWidth,
            // these styles apply for screens of all sizes, unless overridden by another
            // input style below.
            {
              fontSize: \'14px\',
              padding: \'3px\'
            },

            // These styles are applied to inputs ONLY when the screen width is 400px
            // or smaller. Note that because it doesn\'t specify a value for padding,
            // the padding value in the previous object is preserved.
            {
              mediaMaxWidth: \'400px\',
              fontSize: \'18px\',
            }
          ],
          callbacks: {
            cardNonceResponseReceived: function(errors, nonce, cardData) {
              if (errors) {
                var errorDiv = document.getElementById(\'errors\');
                errorDiv.innerHTML = "";
                errors.forEach(function(error) {
                  var p = document.createElement(\'p\');
                  p.innerHTML = error.message;
                  errorDiv.appendChild(p);
                });
              } else {
                // This alert is for debugging purposes only.
                //alert(\'Nonce received! \' + nonce + \' \' + JSON.stringify(cardData));

                // Assign the value of the nonce to a hidden form element
                var nonceField = document.getElementById(\'card-nonce\');
                nonceField.value = nonce;
                // Submit the form
                document.getElementById(\'form\').submit();
              }
            },
            unsupportedBrowserDetected: function() {
              // Alert the buyer that their browser is not supported
            }
          }
        });
        function submitButtonClick(event) {
          event.preventDefault();
          //validateUserInfo();
          sqPaymentForm.requestCardNonce();
        }


        //alert(restaurantMenu.options[restaurantMenu.selectedIndex ].value);


        function validateUserInfo(){
          //TODO: Actually check various constrains
          var name = document.querySelector(\'input[name="name"]\').value;
          var order = document.querySelector(\'input[name="order"]\').value;
          var cost = document.querySelector(\'input[name="cost"]\').value;
          var phone = document.querySelector(\'input[name="phoneNumber"]\').value;
        }

      </script>
      <style type="text/css">
        .sq-input {
          border: 1px solid #CCCCCC;
          margin-bottom: 10px;
          padding: 1px;
        }
        .sq-input--focus {
          outline-width: 5px;
          outline-color: #70ACE9;
          outline-offset: -1px;
          outline-style: auto;
        }
        .sq-input--error {
          outline-width: 5px;
          outline-color: #FF9393;
          outline-offset: 0px;
          outline-style: auto;
        }

        .text-left {
      text-align: left;
    }

    .text-right {
      text-align: right;
    }

    .text-center {
      text-align: center;
    }

      </style>
    </head>
    <body>

      <h1 class="text-center">Place Your Order</h1>

      <form class="form-horizontal" id="form" novalidate action="/processOrder" method="post">

        <div class="form-group">
          <label for="name" class="col-sm-2 control-label">Name</label>
         <div class="col-sm-8">
              <input type="text" class="form-control" id="name" name="username" placeholder="Name">
         </div>
      </div>

        <div class="form-group">
          <label for="meals" class="col-sm-2 control-label">Meal</label>
          <div class="col-sm-8">
            <select id="mealsList" name="meal">""" + meal + """
            </select>
          </div>
        </div>

        <div class="form-group">
          <label for="cost" class="col-sm-2 control-label">Total Cost</label>
         <div class="col-sm-8">
              <input type="text" class="form-control" id="cost" name="cost" placeholder="$0.00" value="$9.15">
         </div>
      </div>

        <div class="form-group">
          <label for="phoneNumber" class="col-sm-2 control-label">Phone Number</label>
         <div class="col-sm-8">
              <input type="text" class="form-control" id="phoneNumber" name="phoneNumber" placeholder="650 000 0000">
         </div>
       </div>

       <div class="form-group">
         <label for="phoneNumber" class="col-sm-2 control-label"></label>
         <div class="col-sm-8"> <hr></div>
      </div>


        <div class="form-group">
         <label for="sq-card-number" class="col-sm-2 control-label"> Credit Card</label>
         <div id="sq-card-number" class="col-sm-8"> </div>
        </div>

        <div class="form-group">
          <label for="sq-cvv" class="col-sm-2 control-label">CVV</label>
         <div id="sq-cvv" class="col-sm-8">
         </div>
        </div>

        <div class="form-group">
          <label for="sq-expiration-date" class="col-sm-2 control-label">Expiration Date</label>
         <div id="sq-expiration-date" class="col-sm-8">
         </div>
        </div>

        <div class="form-group">
          <label for="sq-postal-code" class="col-sm-2 control-label">Postal Code</label>
         <div id="sq-postal-code" class="col-sm-8">
         </div>
        </div>
        <input type="hidden" id="card-nonce" name="nonce">

        <div class="form-group">
          <div class="col-sm-offset-5 ">
            <input type="submit" onclick="submitButtonClick(event)" id="card-nonce-submit">
            <!-- <button type="submit" onclick="submitButtonClick(event)" id="card-nonce-submit" class="btn btn-default">Submit</button> -->
        </div>
      </div>
      </form>

      <div id="errors">
      </div>

      <script>

        var mealsList = document.getElementById(\'mealsList\');
          mealsList.addEventListener(\'change\', event =>{
            event.preventDefault();
            mealsList = document.querySelector(\'#mealsList\');
            var totalCostDiv = document.querySelector(\'input[name="cost"]\');
            var meal = mealsList.options[mealsList.selectedIndex].text
            console.log(meal)
            var priceStr = meal.substring(meal.length - 4);
            totalCostDiv.value = \'$\' + (parseFloat(priceStr) + 2);
        });

      function tag(name, attrs, contents) {
        const element = document.createElement(name)
        for (const name in attrs) {
          element.setAttribute(name, attrs[name])
        }

        // If contents is a single string or HTMLElement, make it an array of one
        // element; this guarantees that contents is an array below.
        if (!(contents instanceof Array)) {
          contents = [contents]
        }

        contents.forEach(piece => {
          if (piece instanceof HTMLElement) {
            element.appendChild(piece)
          } else {
            // must create a text node for a raw string
            element.appendChild(document.createTextNode(piece))
          }
      })
        return element
      }
      </script>
        <script type="text/javascript" src="static/jquery-3.1.1.min.js"></script>
        <script type="text/javascript" src="static/bootstrap.min.js"></script>
    </body>
    </html>"""
    f = open("static/index.html", "w")
    f.write(index)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
