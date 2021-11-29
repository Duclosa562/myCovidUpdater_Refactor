from googleapiclient.discovery import build
import os

#sample
# https://www.googleapis.com/customsearch/v1?key={YOUR_API_KEY}&cx={CUSTOM_SEARCH_ENGINE_ID}&q={KEYWORD}

# example of a request with some specific information
 #format the request
    # res = service.cse().list(
       #  q='butterfly',
        # cx='*******', #ID FOR MY CUSTOM SEARCH ENGINE
        # searchType='image',
        # num=3,
        # imgType='clipart',
        # fileType='png',
        # safe= 'on'
    # ).execute()

# API key env, must also be set on hosting machine
cse_id = os.environ.get("cse_id")
dev_key = os.environ.get("dev_key")
 
# the build function (below) formats the URL with the specific fields fed to google_img_search
# list of args for custom search can be found here
#
# https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
#

"""
Description: A function to query the google CSE API to get image data, returns a list of urls
"""
def google_img_search(search_term, cse_id, **kwargs):
    print("dev_key: {}", dev_key )
    service = build("customsearch", "v1", developerKey=dev_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    # return only the part of the json with key items which is where the urls are located
    return res['items']
