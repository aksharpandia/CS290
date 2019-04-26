from flask import Flask, jsonify, request
from urllib.request import urlopen
import webbrowser
import requests
import json
from collections import OrderedDict
from airtable import Airtable

app = Flask(__name__)
API_KEY = "Hello, WORLD!"

# coding: utf8

#setting up YouTube API
BASE_URL = "https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=" 
DEV_KEY = "AIzaSyCfFutfYpT8vdCDjSgAtdCghZ63XlaKQXc"

#appropriate API keys for Airtable and setting up Airtable API
base_key = 'app0XNaBgemw6bER3'
TopChannelsTable = "TopChannels"
VideoStatsTable = "ChannelStats"


airtable = Airtable(base_key, TopChannelsTable, api_key='keyPegKDh6x2kRqV0')
airtable2 = Airtable(base_key, VideoStatsTable, api_key='keyPegKDh6x2kRqV0')

#create
@app.route('/ivi/create/<search_term>/<int:max_results>/', methods=['POST'])
def create(search_term, max_results):
	#checking if search term has already been done. if so, tell it entry has already been created
	search_term_record = airtable.search('keyword',search_term)
	if search_term_record:
		return "This entry has already been created! Run an update on the term to change it"

	#creating dictionaries to store channel titles and using requestions library to retreieve list of top videos for a given search and then
	#counting the number of videos corresponding to each channel
	video_dict = {}
	create_dict = {}
	main_url = BASE_URL + str(max_results) + '&relevanceLanguage=en' + '&q=' + search_term + '&type=video&key=' + DEV_KEY
	response = requests.get(main_url)
	json_data = response.json()
	#finds the key for the next page
	nextPageToken = (json_data["nextPageToken"])
	for video in json_data["items"]: 
		channelTitle = video["snippet"]["channelTitle"]
		channelId = video["snippet"]["channelId"]
		if channelTitle not in create_dict:
			create_dict[channelTitle]=[]
			create_dict[channelTitle].append(channelId)
			create_dict[channelTitle].append(1)
		else:
			create_dict[channelTitle][1] += 1
	#goes through next page to get more videos and adds to counts for each channel
	for i in range(0,1):
		next_page_url = BASE_URL + (str(max_results)) + '&relevanceLanguage=en' + "&regionCode=US" + '&q=' + search_term + '&type=video&key=' + DEV_KEY + "&pageToken="+nextPageToken
		resp = requests.get(next_page_url)
		json_data = resp.json()
		for video in json_data["items"]: 
			channelTitle = video["snippet"]["channelTitle"]
			channelId = video["snippet"]["channelId"]
			if channelTitle not in create_dict:
				create_dict[channelTitle]=[]
				create_dict[channelTitle].append(channelId)
				create_dict[channelTitle].append(1)
                #create_dict[channelTitle] = 1
			else:
				create_dict[channelTitle][1] += 1
	#sorts the channels from most frequent to least
	sorted_dict =  dict(OrderedDict(sorted(create_dict.items(), key=lambda x: x[1][1], reverse=True)))

	#for each channel in the list, goes through each of the channel's videos and collects relevant stats
	for name in sorted_dict.keys():
		channel_ID = sorted_dict[name][0]
		twenty_most_recent_uploads_url = 'https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=' + channel_ID + '&maxResults=2&order=date&type=video&key=' + DEV_KEY
		get_id_resp = requests.get(twenty_most_recent_uploads_url)
		videos_data = get_id_resp.json()
		for video in videos_data["items"]:
			curr_video_id = video['id']['videoId']
			video_data_url = "https://www.googleapis.com/youtube/v3/videos?part=statistics&id=" + curr_video_id + '&key=' + DEV_KEY
			video_data_resp = requests.get(video_data_url)
			data_for_video = video_data_resp.json()
			for vid in data_for_video["items"]:
				likes = int(vid['statistics']['likeCount'])
				dislikes = int(vid['statistics']['dislikeCount'])
				views = int(vid['statistics']['viewCount'])
				comments = int(vid['statistics']['commentCount'])
				if name not in video_dict:
					video_dict[name] = []
					video_dict[name].append(likes)
					video_dict[name].append(dislikes)
					video_dict[name].append(comments)
					video_dict[name].append(views)
				else:
					video_dict[name][0]+=likes
					video_dict[name][1]+=dislikes
					video_dict[name][2]+=comments
					video_dict[name][3]+=views

	sorted_dict_string = json.dumps(video_dict)
	search_term_no_spaces = search_term.replace('_', " ")
	#inserts channels and stats into DB
	temp = airtable.insert({'keyword':search_term_no_spaces,'channels':sorted_dict_string})
	for channel in video_dict.keys():
		channel_likes = video_dict[channel][0]
		channel_dislikes = video_dict[channel][1]
		channel_comments = video_dict[channel][2]
		channel_views = video_dict[channel][3]
		recordChannelStats = airtable2.search('ChannelName',channel)
		if not recordChannelStats:
			airtable2.insert({'ChannelName':channel, 'Likes':channel_likes, 'Dislikes':channel_dislikes, 'Comments':channel_comments, 'Views':channel_views})
		else:
			continue
			#record_id_channelStats = recordChannelStats[0]['id']
	return sorted_dict_string

#retrieve
@app.route('/ivi/retrieve/<search_term_retrieve>/', methods = ['GET'])
def retrieve(search_term_retrieve):
	#corrects space issues
	search_term_retrieve_noSpaces = search_term_retrieve.replace('_', " ")
	#finds record in DB and replaces
	record = airtable.search('keyword',search_term_retrieve_noSpaces)
	#record_id = resp[0]['id']
	return record[0]['fields']['channels']

#delete
@app.route('/ivi/delete/<search_term_delete>/', methods = ['DELETE'])
def delete(search_term_delete):
	#finds record and deletes, gives confirmation method
	search_term_delete_noSpaces = search_term_delete.replace('_', " ")
	record = airtable.search('keyword',search_term_delete_noSpaces)
	#record_channel_stats = airtable2.search('keyword', search_term_delete_noSpaces)
	record_id = record[0]['id']
	#record_id_channelStats = record[0]['id']
	record_deleted = airtable.delete(record_id)
	#record_deleted_channel_stats = airtable2.delete(record_id_channelStats)
	return 'Deleted ' + search_term_delete + '!'

#update
@app.route('/ivi/update/<search_term_update>/<int:max_results>/', methods=['PATCH'])
def update(search_term_update, max_results):
	#same procedure as creating, 
	search_term_update_noSpaces = search_term_update.replace('_', " ")
	record = airtable.search('keyword',search_term_update_noSpaces)
	record_id = record[0]['id']

	update_dict = {}
	main_url = BASE_URL + str(max_results) + '&relevanceLanguage=en' + '&q=' + search_term_update + '&type=video&key=' + DEV_KEY
	response = requests.get(main_url)
	json_data = response.json()
	nextPageToken = (json_data["nextPageToken"])
	for video in json_data["items"]: 
		channelTitle = video["snippet"]["channelTitle"]
		channelId = video["snippet"]["channelId"]
        #print(channelId)
		if channelTitle not in update_dict:
			update_dict[channelTitle]=[]
			update_dict[channelTitle].append(channelId)
			update_dict[channelTitle].append(1)
            #create_dict[channelTitle] = 1
		else:
            #create_dict[channelTitle] += 1
			update_dict[channelTitle][1] += 1
	for i in range(0,1):
		next_page_url = BASE_URL + (str(max_results)) + '&relevanceLanguage=en' + "&regionCode=US" + '&q=' + search_term_update + '&type=video&key=' + DEV_KEY + "&pageToken="+nextPageToken
		resp = requests.get(next_page_url)
		json_data = resp.json()
		for video in json_data["items"]: 
			channelTitle = video["snippet"]["channelTitle"]
			if channelTitle not in update_dict:
				update_dict[channelTitle]=[]
				update_dict[channelTitle].append(channelId)
				update_dict[channelTitle].append(1)
                #create_dict[channelTitle] = 1
			else:
				update_dict[channelTitle][1] += 1
	sorted_dict =  dict(OrderedDict(sorted(update_dict.items(), key=lambda x: x[1][1], reverse=True)))
	sorted_dict_string = json.dumps(sorted_dict)

	video_dict_ChannelStats = {}
	for name in sorted_dict.keys():
		channel_ID = sorted_dict[name][0]
		twenty_most_recent_uploads_url = 'https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=' + channel_ID + '&maxResults=2&order=date&type=video&key=' + DEV_KEY
		get_id_resp = requests.get(twenty_most_recent_uploads_url)
		videos_data = get_id_resp.json()
		for video in videos_data["items"]:
			curr_video_id = video['id']['videoId']
			video_data_url = "https://www.googleapis.com/youtube/v3/videos?part=statistics&id=" + curr_video_id + '&key=' + DEV_KEY
			video_data_resp = requests.get(video_data_url)
			data_for_video = video_data_resp.json()
			for vid in data_for_video["items"]:
				likes = int(vid['statistics']['likeCount'])
				dislikes = int(vid['statistics']['dislikeCount'])
				views = int(vid['statistics']['viewCount'])
				comments = int(vid['statistics']['commentCount'])
				if name not in video_dict:
					video_dict_ChannelStats[name] = []
					video_dict_ChannelStats[name].append(likes)
					video_dict_ChannelStats[name].append(dislikes)
					video_dict_ChannelStats[name].append(comments)
					video_dict_ChannelStats[name].append(views)
				else:
					video_dict_ChannelStats[name][0]+=likes
					video_dict_ChannelStats[name][1]+=dislikes
					video_dict_ChannelStats[name][2]+=comments
					video_dict_ChannelStats[name][3]+=views
	#here's the real magic, if a channel already is present in the stats table, then skips over that channel, otherwise just inserts any new channels

	#into the stats database
	for channel in video_dict.keys():
		channel_likes = video_dict_ChannelStats[channel][0]
		channel_dislikes = video_dict_ChannelStats[channel][1]
		channel_comments = video_dict_ChannelStats[channel][2]
		channel_views = video_dict_ChannelStats[channel][3]
		recordChannelStats = airtable2.search('ChannelName', channel)
		if not recordChannelStats:
			airtable2.insert({'ChannelName':channel, 'Likes':channel_likes, 'Dislikes':channel_dislikes, 'Comments':channel_comments, 'Views':channel_views})
		else:
			record_id_channelStats = record[0]['id']
			fieldsChannelStats = {'Likes':channel_likes, 'Dislikes':channel_dislikes, 'Comments':channel_comments, 'Views':channel_views}
			airtable2.update(record_id_channelStats, fieldsChannelStats)

	search_term_update_noSpaces = search_term_update.replace('_', " ")
	record = airtable.search('keyword',search_term_update_noSpaces)
	record_id = record[0]['id']
	
	sorted_dict_string = json.dumps(video_dict_ChannelStats)
	fields = {'channels': sorted_dict_string}
	updated = airtable.update(record_id, fields)


	return 'Updated ' + search_term_update + ' to: ' + updated['fields']['channels']

if __name__ == '__main__':
	app.run(debug=True)
