from flask import request
from flask import Response
import os
from flask import Flask, render_template
app = Flask(__name__)
import time
import twitter_api
import imgScraperService
from googleapiclient.errors import HttpError
app = Flask(__name__) 
import requests
import json

# Google API key for custom search API
cse_id = os.environ.get("cse_id")

# globals to store user input data from html forms and the output tweet digest information 
usrInputData = {}
tweetDigest = {}

"""
Route Handler to render the homepage
"""
@app.route('/')
def index():
   return render_template('index.html')

"""
Route handler to render the source page on GET 
"""
@app.route('/sourceSelection',  methods=['GET'])
def sourceSelection():
    if request.method =="GET":
        return render_template('source_selection.html')
    else: 
        return 400 # might need to change this back 

"""
Route handler to process html form submission from the source selection page
"""
@app.route('/sourceSelection',  methods=['POST'])
def handlePostSelection():
    # get data from request and add it to userInputData
    reqData = request.form
    usrInputData["Source"] = reqData["Source"]
    # render the time selection page to get next bit of user data
    return render_template('timeSelection.html')

"""
Route handler to render time selection page
"""
@app.route('/timeSelection',  methods=['GET'])
def timeSelection():
    return render_template('timeSelection.html')

"""
Route handler to process html form submissions from the time selection page
"""
@app.route('/timeSelection',  methods=['POST'])
def handlePostTime():
    # get the user input range data and format it before putting it in the global
    reqData = request.form
    dateStart = reqData["year1"] + "-" + reqData["Month1"] +  "-" + reqData["day1"] 
    dateEnd = reqData["year2"] + "-" + reqData["Month2"] +  "-" + reqData["day2"] 
    usrInputData.update(reqData)
    usrInputData["dateStart"] = dateStart
    usrInputData["dateEnd"] = dateEnd
    # call the digest function which will generate the user digest
    return digest()

"""
Description: A function that takes the time range and source selection information from 
             the user input globals and interacts with the twitter API to build a digest
             of tweets that relate to the keyword "COVID"
"""
def digest():
    #print("in here")
    reqData = request.form
    usrInputData.update(reqData)
    tweetsAndTimes = {}
    # make sure there is a source
    if "Source" in usrInputData.keys():
        # get the account data for the user
        idRespJSON = twitter_api.get_user_id_by_user_name(usrInputData["Source"])
        # get the part of the API response that contains the user id
        idIterate = idRespJSON['data']
        if "id" in idIterate:
            # if there is an id field then get it and use it to get tweet data based on user input params and keyword COVID
            twitterId = idIterate["id"]
            tweetJson = twitter_api.get_user_timeline_by_user_id(twitterId, "COVID", usrInputData["dateStart"], usrInputData["dateEnd"] )
            tweetParse = tweetJson["data"]
            # iterate through the list of tweets and build the digest and save it to a global
            for item in tweetParse:
                currTweet = item["text"]
                currTweetTime = item["created_at"]
                tweetsAndTimes[currTweetTime] = currTweet
        tweetDigest.update(tweetsAndTimes)
    # render the digest page with the newly created digest
    return render_template('digest.html', tweetsAndTimes=tweetsAndTimes)

"""
Route handler to process incoming requests to my Google Image Scraper MicroService
"""
@app.route('/imgScraper',  methods=['POST'])
def imgScraper():
    print("cse id: {}", cse_id )
    responseDat = {}
    linkCount = 0
    #get POST req data from client
    reqData = request.json
    print(reqData)
    # validate request data to make sure the client has entered all required fields in request json
    if "q" not in reqData:
        return {
            "message":"Invalid or absent q field in request."
        }, 400
    if "imgSize" not in reqData:
        return {
            "message":"Invalid or absent imgSize field in request."
        }, 400
    if "fileType" not in reqData:
        return {
            "message":"Invalid or absent fileType field in request."
        }, 400
    if "num" not in reqData:
        return {
            "message":"Invalid or absent num field in request."
        }, 400    
    if "imgType" not in reqData:
        return {
            "message":"Invalid or absent imgType field in request."
        }, 400
    # make request to google CSE API for images if request has populated fields
    if request.method == "POST":
        try:
            results = imgScraperService.google_img_search(reqData["q"], cse_id,
                    imgSize = reqData["imgSize"], fileType = reqData["fileType"], num = reqData["num"],
                    safe="active", searchType="image", imgType=reqData["imgType"])
            print(results)
        except HttpError as e:
            return Response(f'Google API Error: {e.status_code} : {e.reason}', status=400, mimetype='application/json')
    else:
        return Response("", status=400, mimetype='application/json')
    # format output as a json of image urls
    print(results)
    responseDat["Image URLs for query"] = reqData["q"]
    for result in results:
        print("formatting output")
        print(result)
        # get link only from google response and place links in imgScraper Response for client
        responseDat[str(linkCount)] = result.get('link')
        linkCount = linkCount + 1
    return responseDat

"""
Route handler to render the share data page
"""
@app.route('/share',  methods=['GET'])
def sharePage():
    return render_template('share.html')

"""
Route handler for my app to interact with an external microService

function output format:

          {     "to" : [csv email addr list]
           "subject" : subject line string
              "text" : email body text
          }
"""
@app.route('/share',  methods=['POST'])
def emailOut():
    msRequestDat = {}
    msurl = "https://cs361microservice.wm.r.appspot.com/email"
    #get email data json from html form 
    emailData = request.form
    # build outgoing json
    toList = "{email1}, {email2}, {email3}".format(email1=emailData["email1"], email2=emailData["email2"], email3=emailData["email3"])
    msRequestDat["to"] = toList
    subjectLine = "Hey!, its {iden}, here is a digest of useful COVID19 information from myCovidUpdater. Check it out!".format(iden=emailData["iden"])
    msRequestDat["subject"] = subjectLine
    #format the email body
    text = "\n" + "Tweets from {source} from {start} to {end} relating to the keyword COVID19\n".format(source=usrInputData["Source"], start = (usrInputData["year1"] + "-" + usrInputData["Month1"]), end = 
    (usrInputData["year2"] + "-" + usrInputData["Month2"]))
    for tweet in tweetDigest:
        getTweet = tweetDigest[tweet]
        # check if the substring "\n\n" appears in the tweet and change it to "\n" for formatting reasons
        getTweetFormatted = getTweet.replace("\n\n", "\n")
        tempText = "TIME: {tweet}\nTWEET: {getTweet}".format(tweet=tweet, getTweet=getTweetFormatted)
        tempText = tempText + "\n\n"
        text = text + tempText
    msRequestDat["text"] = text
    # set request header and post data to ms endpoint and convert payload to json
    reqDat = json.dumps(msRequestDat)
    headers = {'Content-Type' : 'application/json'}
    r = requests.post(url = msurl, headers=headers, data=reqDat)
    # render a success template
    return render_template('emailOutSuccess.html')

if __name__ =='__main__':
    app.run()