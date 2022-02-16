import os
import json
from dotenv import load_dotenv
from discord.ext.tasks import loop
from requests import get

class PetMonty():
	name = '!petmonty'

	desc = 'Give Monty a pet. He deserves it'

	synt = '!petmonty'

	looping = False

	group = 'members'

	admin = False
	
	cheer = -1
	
	cat = 'admin'
	
	is_service = False

	def checkCat(self, check_cat):
		if self.cat == check_cat:
			return True
		else:
			return False
	
	def checkBits(self, bits):
		return False
	
	async def runCheer(self, user, amount):
		return

	async def run(self, message, obj_list):
		# Create fresh stat file
		if not os.path.isfile('montystats.json'):
			# Create fresh json template
			data = {}
			data['name'] = 'Monty'
			data['pets'] = 0
			data['members'] = []
			with open('montystats.json', 'w') as f:
				json.dump(data, f)

		# Get json data
		f = open('montystats.json',)

		json_data = json.load(f)

		f.close()

		# Adjust number of pets by 1
		json_data['pets'] = int(json_data['pets']) + 1

		discord_user = str(message.author)

		found = False

		# Search for member in list of members
		for member in json_data['members']:
			if member['name'] == discord_user:
				found = True
				break

		if not found:
			# Add user to list of members who have done a pet if not there
			json_data['members'].append({'name': str(discord_user)})

		# Write new json data to json file
		with open('montystats.json', 'w') as f:
			json.dump(json_data, f)

		await message.channel.send(message.author.mention + ' just pet Monty')

	async def stop(self, message):
		self.looping = False
