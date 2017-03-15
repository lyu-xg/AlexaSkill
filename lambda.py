# Author: Xueguang Lu
# Nearby Places Alexa skill support script
from __future__ import print_function
from urllib2 import Request, urlopen, URLError
import json
import datetime as dt
import urllib

# --------------- Helpers for calling API layer ----------------------

gmaps_key = 'AIzaSyC6J06KCLzmvuoab3ve5asK0ygAOvF2wVc'

def getLatLug(address):
    address = address.replace(' ','+')
    link = 'https://maps.googleapis.com/maps/api/geocode/json?address={}&key={}'.format(address,gmaps_key)
    request = Request(link)

    try:
        response = urlopen(request)
        content = json.loads(response.read())
        lat = content['results'][0]['geometry']['location']['lat']
        lng = content['results'][0]['geometry']['location']['lng']
        return (lat,lng)
    except URLError, e:
        print('No GeoCode. Got an error code:', e)
        return None,None

def getNearestLocation(lat,lon,placeId,keyword):
    payload={'location': str(lat) + ','+ str(lon) , 'radius' : 20000 , 'keyword' : keyword, 'key' : gmaps_key}
    r = requests.get('https://maps.googleapis.com/maps/api/place/nearbysearch/json',  params=payload)
    json_results = r.json()
    print(json_results)
    success = True
    add ='null'
    if(json_results['status'] != 'OK'):
        success = False
    else:
        add = json_results['results'][0]['vicinity']
        placeid = json_results['results'][0]['place_id']
        if placeId:
            return placeid
    return success,add

def getOpenHours(lat,lon,day,keyword):
    placeId = getNearestLocation(lat,lon,True,keyword)
    payload={'placeid': placeId , 'key' : gmaps_key}
    r = requests.get('https://maps.googleapis.com/maps/api/place/details/json',  params=payload)
    json_results = r.json()
    print(json_results)
    success = True
    add ='null'
    if(json_results['status'] != 'OK'):
        success = False
    else:
        today = ' '.join(json_results['result']['opening_hours']['weekday_text'][day-1].split(":")[1:]).replace(u'\u2013','-')
        tomorrow = ' '.join(json_results['result']['opening_hours']['weekday_text'][(day) % 7].split(":")[1:]).replace(u'\u2013','-')
        current =   json_results['result']['opening_hours']['open_now']
        success = True
        add = {'today':today,'tomorrow':tomorrow,'current':current}
    return success,add


def getHour(location,day):
    lat,lng = location
    print(location,day)
    url = BackEndURL + '/openHours'
    post_fields = {"latitude": lat, "longitude": lng, "day": day}
    link = url +'?' + urllib.urlencode(post_fields)
    try:
        request = Request(link)
        response = urlopen(request)
        content = json.loads(response.read())
        return content['openHours']
    except URLError, e:
        print('Unable to get Hours, Got an error code: ', e)


# -------------------- Response Builders -----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    #sendToApp(output)
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


def build_my_response(session_attributes, card_title, output, reprompt_text):
    return build_response(session_attributes, build_speechlet_response(
        card_title,output,reprompt_text,False))

def parsehour(hour):
    result = ''
    hour = hour.split('-')
    for i in hour:
        i = i.strip().split(' ')
        for n in i:
            if n != '00':
                result+= n+' '
        result+='to '
    return result[:-4]

# --------------- Functions that control the skill's basic behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "How can I help you?" 
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "You can ask about your balance, make transfers," \
                    " make appointments, inquire nearest branch information, etc. " 
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for using Bank Buddy, " \
                    "Have a nice day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


# -------------- Attribute helpers -------------------

def add_location_to_attributes(session,lat,lng):
    session['attributes']['Location'] = (lat,lng)

def log_intent_to_attributes(session,intent_name):
    if session.get('attributes', {}): 
        if "IntentLog" in session.get('attributes', {}):
            session['attributes']['IntentLog'].append(intent_name)
        else:
            session['attributes']['IntentLog'] = [intent_name]
    else:
        session['attributes'] = {'IntentLog':[intent_name]}
        
def add_date_time_to_attributes(session,datetime):
    session['attributes']['datetime'] = datetime

def add_weekday_to_attributes(session,weekday):
    session['attributes']['weekday'] = weekday

# -------------- Costom Intent Handlers -----------------

def get_nearest_place(intent,session):
    session_attributes = {}
    if session.get('attributes', {}):
        session_attributes = session['attributes']
    card_title = intent['name']
    address = ''
    if "value" in intent['slots']['Address']:
        address = intent['slots']['Address']['value']
    if "value" in intent['slots']['City']:
        address += intent['slots']['City']['value']
    if "value" in intent['slots']['State']:
        address += intent['slots']['State']['value']
    if "value" in intent['slots']['Places']:
        keyword = intent['slots']['Places']['value']
    if not keyword:
        speech_output = "You can say, for example, find me a bank."
        reprompt_text = speech_output
    elif address:
        lat,lng = getLatLug(address)
        status,nearest_place = getNearestLocation(lat,lng,False,keyword)
        if not status:
            speech_output = "There is currently no {} near you, we are working on it.".format(keyword)
        else:
            speech_output = "I found a "+keyword+" that is closest to you at "+nearest_place
        reprompt_text = "Is there anything else I can help you?"
        add_location_to_attributes(session,lat,lng)
    else:
        speech_output = "Please give me an address so that I can search nearest {} for you.".keyword
        reprompt_text = speech_output
    return build_my_response(session_attributes,card_title,speech_output,reprompt_text)


def address_only(intent,session):
    session_attributes = {}
    if session.get('attributes', {}):
        session_attributes = session['attributes']
    log = session['attributes']['IntentLog']
    address = ''
    if "value" in intent['slots']['Address']:
        address = intent['slots']['Address']['value']
    if "value" in intent['slots']['City']:
        address += ', '+intent['slots']['City']['value']
    if address:
        add_location_to_attributes(session,address)

    for i in xrange(len(log)):
        if log[len(log)-i-1] == "GetOpenHourIntent":
            return get_open_hour(intent, session)
    return get_welcome_response()



def get_open_hour(intent,session):
    session_attributes = {}
    if session.get('attributes', {}):
        session_attributes = session['attributes']
    date = time = day = location = None
    if 'datetime' in session_attributes:
        [date, time] = session_attributes['datetime']
    if 'weekday' in session_attributes:
        day = session_attributes['weekday']
    
    if 'Location' in session_attributes:
        location = session_attributes['Location']
   
    if 'Date' in intent['slots'] and 'value' in intent['slots']['Date']:
        date = Intent['slots']['Date']['value']
    elif not day:
        day = dt.datetime.today().weekday()
    if "Time" in intent['slots'] and 'value' in intent['slots']['Time']:
        time = Intent['slots']['Date']['value']
    if 'Day' in intent['slots'] and 'value' in intent['slots']['Day']:
        day = Intent['slots']['Day']['value']

    if date and not day:
        year, month, day = (int(x) for x in date.split('-'))   
        day = datetime.date(year, month, day).weekday()

    if date or time:
        add_date_time_to_attributes(session,[date,time])
    if day:
        add_weekday_to_attributes(session,day)

    if not location:
        speech_output = "Please give me an address so that I can search nearest branch for you."
        reprompt_text = speech_output
        return build_my_response(session_attributes,intent['name'],speech_output,reprompt_text)

    hours = getHour(location,day)
    current = 'open' if hours['current'] else 'closed'
    today = parsehour(hours['today'])
    tomorrow = parsehour(hours['tomorrow'])
    tomorrow = 'bank open tomorrow from '+tomorrow if tomorrow != 'Closed' else 'tomorrow will {}be Closed all day.'.format('also ' if today=='Closed' else '')
    today = 'it opens today from '+today if today != 'Closed' else 'it\'s Closed today all day'
    speech_output = "Bank is currently {}, {}, {}".format(current,today,tomorrow)
    return build_my_response(session_attributes,intent['name'],speech_output,speech_output)


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    log_intent_to_attributes(session,intent_name)


    if intent_name == "GetNearestPlaceIntent":
        return get_nearest_place(intent, session)
    elif intent_name == "AddressOnlyIntent":
        return address_only(intent,session)
    elif intent_name == "GetOpenHourIntent":
        return get_open_hour(intent, session)
    elif intent_name == "AMAZON.YesIntent":
        return yes_handler()
    elif intent_name == "AMAZON.NoIntent":
        return no_handler()
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    '''
    if (event['session']['application']['applicationId'] !=
         "amzn1.ask.skill.0fb6a300-ef40-4108-a5b8-aa7086bd3f48"):
        raise ValueError("Invalid Application ID")
    '''
    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

if __name__ == "__main__":
    print('start running')
