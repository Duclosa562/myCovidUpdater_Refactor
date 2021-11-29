import re
from app import app
from flask import request
from dateutil.parser import parse as parse_date
import requests
import os
import json

# Get env var for API token
# Note this must also be set in the env of the hosting machine
bearer_token = os.environ.get("BEARER_TOKEN")
MAX_ITER = 100

#build request URL for twitter api
def get_user_id_by_user_name(user_name):
    url = get_api_url_by_method("user_name").format(user_name)
    return make_get_request(url)

"""
Definition: A function that will get a user's timeline data within a range of time and filter the results 
            based on a user defined filter

Params: user_id, twitter user id
        filter_by, string keywords to search for 
        start/end, MM-DD-YY unformatted time range

Returns: twitter data object or if a problem default to last 10 tweets from the user
"""
def get_user_timeline_by_user_id(user_id, filter_by="", start="", end=""):
    # build url to get user timeline by user id
    url = get_api_url_by_method("timeline").format(user_id)
    print("URL: {url}".format(url=url))
    tweet_data = []
    params = {}
    # start and end define a range of tweets 
    if start:
        params["start_time"] = parse_date(start).isoformat() +"Z"
    if end:
        params["end_time"] = parse_date(end).isoformat() + "Z"
    if filter_by:
        # make request to get twitter user timeline, possibly in range if range exists (params)
        response_data = make_get_request(url, params)
        counter = 0
        # parse raw twitter data in range
        while can_iterate(counter, tweet_data, response_data, start, end):
            counter+=1
            list_data = response_data["data"]
            print(list_data)
            # filters response from twitter api that matches what we specify in filter_by
            # eg : if filter_by = covid, get all the tweets within response_data with the word covid in it (retweets excluded)
            tweet_data += [tweet_obj for tweet_obj in list_data if filter_by.lower() in tweet_obj["text"].lower() and "RT" not in tweet_obj["text"]]
            # pagination limit (10), so if more data get next 10 
            if "next_token" in response_data["meta"]: 
                next_token = response_data["meta"]["next_token"]
                response_data = make_get_request(url, { **params, **{
                    "pagination_token" : next_token
                }})
                
            else :
                break

        return {
            "data": tweet_data
        }

    else :
        # no range and no filter, last 10 tweets returned (default twitter) 
        return make_get_request(url, params)

"""
Description: A function to check if there are more tweets to parse in the user defined
             time range. Tops out at 100 total tweets.
"""
def can_iterate(iterations, total_data, response_data, start="", end=""):
 
    can_iter = iterations < MAX_ITER and len(total_data) < 100 and "data" in response_data
    # if can_iter is true and there is a range
    if can_iter and start and end:
        # get list of tweets
        data = response_data["data"]
        # get data timestamps (year mo day) and check if there is more in the data list
        first_created_at = parse_date(data[0]["created_at"][:10])
        last_created_at =  parse_date(data[-1]["created_at"][:10])
        # parse_date, turns a string into python date time object
        formatted_start = parse_date(start)
        formatted_end = parse_date(end)
        # check if the first entry matches the query date and t/f 
        return last_created_at >= formatted_start and first_created_at <= formatted_end
    else:
        return can_iter

"""
Description: Returns proper url for twitter endpoints based on what kind of querying method
             is being used.
"""
def get_api_url_by_method(method):
    # get userID by username API
    if (method == "user_name"):
        return "https://api.twitter.com/2/users/by/username/{}"
    # get user timeline by user id
    if (method == "timeline"):
        return "https://api.twitter.com/2/users/{}/tweets"
    return -1

"""
Description: Can be called to give default params for twitter time-based query
"""
def get_params():
    return {"tweet.fields": "created_at"}

"""
    Method required by bearer token authentication.
"""
def bearer_oauth(r):
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2UserTweetsPython"
    return r

"""
Description: A method to actually make the request to the twitter API to get tweet data
"""
def make_get_request(url, params=None): 
    # get created at field from twitter
    default_params = {"tweet.fields": "created_at" }
    # z = {**x, **y} => z is a union of maps of x and y 
    response = requests.request("GET", url, auth=bearer_oauth, params= {**default_params, **params} if params is not None else default_params)
    # print(response.status_code)
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    return response.json()


"""
Description: A testing function to check twitter calls
"""
@app.route('/test', methods=['GET'])
def test():
    # request from flask not python, parsing the url
    user_name = request.args.get('username')
    user_id = request.args.get('id')
    filter_by = request.args.get('filter_by')
    start = request.args.get('start')
    end = request.args.get('end')
    if (not user_id):
        response = get_user_id_by_user_name(user_name)
        if "data" not in response:
            return {
                "error": f"Invalid user name : {user_name}"
            }
        # get id and then return timeline data 
        id = response["data"]["id"]
        return get_user_timeline_by_user_id(id, filter_by, start, end)
    # error
    return -1

