# Copyright 2015 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import uuid,os

from flask import Flask, jsonify, request


#Square Modules
import squareconnect
from squareconnect.rest import ApiException
from squareconnect.apis.transaction_api import TransactionApi

app = Flask(__name__)


# The access token to use in all Connect API requests. Use your *sandbox* access
# token if you're just testing things out.
access_token = 'sandbox-sq0atb-vwQUCVDYaJrgubwxf5VnkQ'

# The ID of the business location to associate processed payments with.
# See [Retrieve your business's locations]
# (https://docs.connect.squareup.com/articles/getting-started/#retrievemerchantprofile)
# for an easy way to get your business's location IDs.
# If you're testing things out, use a sandbox location ID.
location_id = 'CBASEMe2x6MwoifEPrKa8Toz5gk'


@app.route('/')
def Welcome():
    return app.send_static_file('index.html')

@app.route('/placeOrder', methods = ['POST'])
def placeOrder():
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



port = os.getenv('PORT', '8000')
if __name__ == "__main__":
	app.run(host='127.0.0.1', port=int(port))
