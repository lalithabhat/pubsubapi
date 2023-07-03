"""
SalesforceListener.py

This is a subscriber client that listens for `/event/NewOrderConfirmation__e`
events published by the inventory app (`InventoryApp.py`). The `if __debug__`
conditionals are to slow down the speed of the app for demoing purposes.
"""

import os, sys, avro

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.abspath(os.path.join(dir_path, os.pardir))
sys.path.insert(0, parent_dir_path)

from util.ChangeEventHeaderUtility import process_bitmap
from datetime import datetime
import json
import logging
import requests
import time

from PubSub import PubSub
import sys


def process_confirmation(event, pubsub):
    """
    This is a callback that gets passed to the `PubSub.subscribe()` method. It
    decodes the payload of the received event and extracts the opportunity ID
    and estimated delivery date. Using those two pieces of information, it
    updates the relevant opportunity with its estimated delivery date using the
    REST API. When no events are received within a certain time period, the
    API's subscribe method sends keepalive messages and the latest replay ID
    through this callback.
    """

    if event.events:
        print("Number of events received in FetchResponse: ", len(event.events))
        # If all requested events are delivered, release the semaphore
        # so that a new FetchRequest gets sent by `PubSub.fetch_req_stream()`.
        if event.pending_num_requested == 0:
            pubsub.release_subscription_semaphore()

        for evt in event.events:
            # Get the event payload and schema, then decode the payload
            payload_bytes = evt.event.payload
            json_schema = pubsub.get_schema_json(evt.event.schema_id)
            decoded_event = pubsub.decode(json_schema, payload_bytes)
            # print(decoded_event)
        
            json_object =decoded_event
            print(json.dumps(json_object, indent = 3))
            #  A change event contains the ChangeEventHeader field. Check if received event is a change event. 
            if 'ChangeEventHeader' in decoded_event:
                # Decode the bitmap fields contained within the ChangeEventHeader. For example, decode the 'changedFields' field.
                # An example to process bitmap in 'changedFields'
                changed_fields = decoded_event['ChangeEventHeader']['changedFields']
                accountRecId = decoded_event['ChangeEventHeader']['recordIds'][0]
                accountName = decoded_event['Name']
                print("Change Type: " + decoded_event['ChangeEventHeader']['changeType'] + "Account Id:" +accountRecId )
                #print("=========== Changed Fields =============")
                print(process_bitmap(avro.schema.parse(json_schema), changed_fields))
                #print("=========================================")
            # print("> Received account change confirmation! Updating SLA exp date..." , evt)
            if __debug__:
                time.sleep(2)
            # Update the Desription field of the account with the SLA expiration date with a REST request
            today = datetime.now()

            print(today)
            # day = today.strftime("%d/%m/%Y")
            # res = requests.patch(pubsub.url + "/services/data/v" + pubsub.apiVersion + "/sobjects/Account/"
            #                      + accountRecId, json.dumps({"Site":"Test"}),
            #                      headers={"Authorization": "Bearer " + pubsub.session_id,
            #                               "Content-Type": "application/json",
            #                               "Sforce-Call-Options": "client=SalesforceListener"})
            # print("  Done!", res)
    else:
        print("[", time.strftime("%m-%d-%Y %H:%M%p"), "] The subscription is active.")

    # The replay_id is used to resubscribe after this position in the stream if the client disconnects.
    # Implement storage of replay for resubscribe!!!
    event.latest_replay_id

def run(argument_dict):
    sfdc_updater = PubSub(argument_dict)
    sfdc_updater.auth()

    # Subscribe to /event/AccountChangeEvent events
    sfdc_updater.subscribe('/data/AccountChangeEvent', "LATEST", "", 1, process_confirmation)


if __name__ == '__main__':
    argument_dict = sys.argv[1]
    argument_dict = dict( pair.split('=') for pair in argument_dict.split(' ') )
    print(argument_dict)
    logging.basicConfig()
    run(argument_dict)
