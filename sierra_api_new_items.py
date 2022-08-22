#!/usr/bin/env python3

# POSSIBLE ENHANCEMENTS
# TODO: alternative to ISBN for DVDs? different 020 tag?
# TODO: Create a media element in each entry to hold the cover image
# TODO: make the sierraQuery variable a list ["newfiction","newadultnf",etc] and loop through that list to
#   create feeds for mutliple genres/material types/etc. in a single python script

# import the required libraries
import os
# from dotenv import load_dotenv
import base64
import requests
import json
from datetime import datetime, timedelta
from feedgen.feed import FeedGenerator

# GLOBAL VARIABLES
api_key = '[YOUR API KEY]'
api_secret = '[YOUR API_SECRET]'

# enter your Sierra server base url below, e.g. https://webpac.sutherlandshire.nsw.gov.au
sierraBase = '[YOUR SIERRA DOMAIN]'
sierraRest = sierraBase + ":443/iii/sierra-api/v6"

# TODO Ideally you should store the key + secret in .env variable so they aren't in the code
# the following 3 lines do that but you first need to install the dotenv python module and uncomment the dotenv import statement above
# load_dotenv()
# api_key = os.environ['API_KEY']
# api_secret = os.environ['API_SECRET']

# substitute different json queries here for different lists
sierraQuery = "newadultnf"
# set the number of days to include in the rss feed i.e. new adult nf added in the last 14 days
numberOfDays = 14
# set the name of the feed file and location for it to be saved, based on the query filename
feedFile = "../public_html/feeds/" + sierraQuery + ".xml"
# generate the current date
now = datetime.now()
# instantiate an empty list to hold the list of matching bib numbers
bibIds = []

# TODO this function handles the OAUTH flow for a Client Credentials Grant and retuns the auth token for subsequent API calls


def getToken(key, secret):
    # base64 encode the key + secret string
    authStr = key + ":" + secret
    authStr_bytes = authStr.encode("ascii")
    base64_bytes = base64.b64encode(authStr_bytes)
    base64Str = base64_bytes.decode("ascii")
    authorisationStr = "Basic " + base64Str

    # request the toke from the API
    tokenUri = sierraRest + "/token/"
    basicAuth = {
        "Authorization": authorisationStr
    }
    result = requests.post(tokenUri, headers=basicAuth)

    # store the token from the response
    tokenResponse = result.json()
    # print(json.dumps(tokenResponse, indent=2))

    # return the authorisation header for subsequest API calls
    try:
        token = tokenResponse['access_token']
        tokenType = tokenResponse['token_type']
        authHeader = tokenType + " " + token
        return authHeader
    except:
        print("an error occurred requesting the oauth token")
    # End getToken()


# TODO: this funtion creates the json for the bibs request from a saved text file
# Copy the JSON from a saved search in Create Lists, then
# Edit the JSON text to replace the start date with a the variable "queryDate"
def generateJSON(queryName, period):
    fromDate = now - timedelta(days=period)
    queryDate = fromDate.strftime("%d-%m-%Y")
    queryFile = queryName + ".txt"

    with open(queryFile, 'r') as file:
        queryFile_read = file.read()
        # replace the variable in the txt file with the from date based on the numberOfDays global variable
        queryStr = queryFile_read.replace('queryDate', queryDate)

    query_json = json.loads(queryStr)

    print(sierraQuery + " added since " + queryDate)
    return query_json
    # End generateJSON()


def main():

    # get Oauth token for Sierra API
    oauthToken = getToken(api_key, api_secret)

    # instatiate an empty feed using feedgen
    # see the Python feedgan module documentation for more information on what these lines do
    # https://feedgen.kiesow.be/index.html
    fg = FeedGenerator()
    # the canonical URL for the feed
    fg.id('[YOUR WEB SERVER]' + sierraQuery + '.xml')
    fg.title('New items...')
    fg.description(
        'A list of new titles recently added to the collection of...')
    fg.link(href='[YOUR WEB SERVER]' + sierraQuery +
            '.xml', rel='self', type='application/rss+xml')
    fg.link(
        href='[LINK TO WEBSITE VERSION OF THIS LIST OF NEW TITLES]]', rel='alternate')
    fg.language('en')

    # make a GET request to the Sierra API for New Fiction in the last period
    url = sierraRest + "/bibs/query?offset=0&limit=500"
    auth = {
        "Authorization": oauthToken
    }
    query = generateJSON(sierraQuery, numberOfDays)
    queryResponse = requests.post(url, headers=auth, json=query)
    # parse the json response into a python object
    bibList = queryResponse.json()
    # DEBUG uncomment the next line to print the json response if you want to see the raw response from the API call
    # print(json.dumps(bibList, indent=2))

    # collect the Bib IDs into the bibIds list ready to make a 2nd query for the title, author and description, etc.
    if (bibList['total'] > 0):
        for entry in bibList['entries']:
            string = entry['link']

            bibNumber = string.lstrip(sierraRest + '/bibs/')
            bibIds.append(bibNumber)
    else:
        print('no bib records returned.')

    print('number of bib records found: ', end='')
    print(len(bibIds))
    # DEBUG uncomment the next line to see the returned Bib IDs, stripped out from the list of API URLs
    # print(bibList)

    # TODO: concatenate the list of Bib ID numbers into a comma separated string to append to the API request
    if (len(bibIds) > 0):
        separator = ","
        strBibIds = (separator.join(bibIds))
        # print(f"list of bib IDs is: {strBibIds}")

        # TODO: make a second request to the Sierra API for the Bib record details for each Bib ID
        urlBibs = sierraRest + "/bibs/"
        params = {"id": strBibIds,
                  "fields": "catalogDate,marc",
                  "limit": "500"}
        reqBibs = requests.get(urlBibs, headers=auth, params=params)
        bibsResponse = reqBibs.json()

        # DEBUG
        # the next line prints the url for the API Call
        # print(reqBibs.url)

        # next line prints the response code from the API server, which should be success : 200
        # print(reqBibs)

        # the next line prints the formatted JSON reponse from the API call
        # print(json.dumps(bibsResponse, indent=2))

        # TODO: Loop through the response and store the 245, 520 and 20 marc tag data in variables
        if (bibsResponse['total'] > 0):
            # each entry represents a bib record in the json response
            for entry in bibsResponse['entries']:
                # set values for the feed item
                entryId = entry['id']
                # Link to webpac based on bib ID
                # adjust BibUri variable to use any other catalogue, e.g. Encore, Vega that can use a Bib ID as the identifier
                bibUri = sierraBase + '/record=b' + entryId
                # set the feed link
                entryLink = {'href': bibUri}
                # set a default description for the feed item in case there are no 520 tags in the marc record
                entryContent = 'no description provided'
                # set a default value for the feed guid in case there are no ISBNs in the marc record
                entryISBN = bibUri
                # Instantiate an empty list to hold all the ISBNs (020 tags) in the marc record
                isbnList = []
                # set the pubDate for the feed item
                catalogDate = entry['catalogDate']
                strDate = catalogDate + ' 00:00:00 +1000'
                entryDate = datetime.strptime(strDate, '%Y-%m-%d %H:%M:%S %z')

                # create a new feed entry
                fe = fg.add_entry()
                fe.link(entryLink)
                fe.published(entryDate)
                # use these to create atom feeds
                # fe.updated(entryDate)
                # fe.id(bibUri)

                # entryMarc returns a list of dictionaries for each marc tag (field)
                entryMarc = entry['marc']['fields']
                # loop through the list of marc fields
                for field in entryMarc:
                    if '245' in field:
                        # create an empty list to hold the subfields (title, author)
                        titleList = []
                        # tag245 is a list of dictionaries holding the subfields for the marc 245 tag
                        tag245 = field.get('245')['subfields']
                        # loop through the list (of dictionaries)
                        for dict_subfield in tag245:
                            # loop through each subfield dict
                            for key in dict_subfield:
                                # append the value for each dict key to the titleList
                                titleList.append(dict_subfield[key])
                        # join the values from titleList to create a string
                        entryTitle = ' '.join(titleList)

                    if '520' in field:
                        entryNotes = field.get('520')['subfields'][0]['a']
                        # Alternative for multiple subfields
                        # tag520 = field.get('520')['subfields']
                        # print (tag520)
                        # notesList = []
                        # for dict_subfield in tag520:
                        #     for key in dict_subfield:
                        #         notesList.append(dict_subfield[key])
                        # entryNotes = '/n'.join(notesList)

                    if '020' in field:
                        # tag020 is a list of dictionaries holding the subfields for the marc 020 tag
                        tag020 = field.get('020')['subfields']
                        # loop through the 020 tags
                        for subfield in tag020:
                            # ignore 020 fields that don't have subfield 'a'
                            if 'a' in subfield:
                                # get the subfield 'a' value, i.e. the ISBN string
                                strISBN = subfield.get('a')
                                # append it to isbnList
                                isbnList.append(strISBN)
                        # print(isbnList)
                        # get the first ISBN in list, usually the 13 digit ISBN
                        tagISBN = isbnList[0]
                        # split the string at the first space to remove any text like 'hardback'
                        # leaving the stright 13 digits that can be used to generate cover images
                        entryISBN = tagISBN.split()[0]

                # prepare the content string
                entryContent = '<p><img src="[YOUR ISBN BASED COVER IMAGE SERVICE]' + entryISBN + 'border="0" alt="cover image" /></p><p>' + \
                    entryNotes + '</p>'
                # add the title to the feed entry
                fe.title(entryTitle)
                # add the description to the entry
                fe.content(entryContent)
                # create the guid for the entry
                fe.guid(entryISBN)

            # TODO: Generate the RSS feed using the marc data stored in the variables above
            rssFeed = fg.rss_str(pretty=True)
            # alternative for Atom feeds
            # atomFeed  = fg.atom_str(pretty=True)

            # TODO: delete the existing feed file if it exists
            try:
                os.remove(feedFile)
                print(feedFile + " has been deleted.")
            except OSError as error:
                print("There was an error deleteing the previous feed.")

            # TODO: save the new feed
            try:
                # Write the RSS feed to a file
                fg.rss_file(feedFile)
                print("New version of " + sierraQuery + ".xml has been saved")
            except OSError as error:
                print("There was an error creatng the feed")

            # Atom feed alternative
            # fg.atom_file('feedFile')
            # print(rssFeed.decode("utf-8"))
            # print(atomFeed.decode("utf-8"))

    # if the query returns 0 new bib records do nothing
    else:
        print("no bib records returned. leave feed file alone")


if __name__ == "__main__":
    main()

# CRONTAB entry   0 2 * * * /usr/bin/python3 /users/boycetrus/desktop/repos/python-experiments/sierra_api_new_fiction_v2.py /users/boycetrus/desktop/repos/python-experiments/newfiction.log
