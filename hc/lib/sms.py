from twilio.rest import Client
import os

account = os.getenv('twilio_account')
token = os.getenv('twilio_token')
client = Client(account, token)


def send_sms(to, sms_body, sender=os.getenv('twilio_phone')):

    return client.messages.create(to=to, from_=sender,
                                  body=sms_body)
