import os
import sys
import json
import discord
import pytz
from pytz import utc
from pytz import timezone
from datetime import datetime
from dotenv import load_dotenv
from discord.ext.tasks import loop
from requests import get

sys.path.append(os.path.abspath('utils'))

from utils.config_utils import ConfigUtils

class Poll():
	# Required for all plugins
	conf_path = os.path.join(os.path.dirname(__file__), 'configs')

	guild_confs = []

	configutils = None

	name = '!poll'

	desc = 'Start a poll and start the poll service'

	synt = '!poll [<description>]|[start]|[stop][config|get <config>|set <config> <value>|add/remove <config> <value>]'

	default_config = {}
	default_config['protected'] = {}
	default_config['protected']['name'] = __file__
	default_config['protected']['guild'] = None
	default_config['standard_groups'] = {}
	default_config['standard_groups']['value'] = []
	default_config['standard_groups']['description'] = "Authorized groups to use this command"
	default_config['admin_groups'] = {}
	default_config['admin_groups']['value'] = []
	default_config['admin_groups']['description'] = "Authorized groups to use admin functions of this command"
	default_config['blacklisted'] = {}
	default_config['blacklisted']['value'] = []
	default_config['blacklisted']['description'] = "Groups explicitly denied access to this command"
	default_config['post_channel'] = {}
	default_config['post_channel']['value'] = ""
	default_config['post_channel']['description'] = "Desitination channel to post messages from this plugin"
	default_config['tag_role'] = {}
	default_config['tag_role']['value'] = ""
	default_config['tag_role']['description'] = "The role that is mentioned when new polls are posted"
	default_config['yes_vote'] = {}
	default_config['yes_vote']['value'] = ""
	default_config['yes_vote']['description'] = "The emote to signify 'yes'"
	default_config['no_vote'] = {}
	default_config['no_vote']['value'] = ""
	default_config['no_vote']['description'] = "The emote to signify 'no'"
	default_config['time_lim'] = {}
	default_config['time_lim']['value'] = 0
	default_config['time_lim']['description'] = "Duration of a poll in seconds"

	running_guilds = []

	looping = False

	group = '@everyone'

	admin = False
	
	cheer = -1
	
	cat = 'admin'
	
	is_service = True

	client = None

	poll_desc = None

	poll_win_percent = 0.01

#	poll_time_limit = 604800 #one week seconds
	poll_time_limit = 345600
#	poll_time_limit = 20

	time_zone = 'US/Eastern'

	message_history_limit = 100

	def __init__(self, client = None):
		self.client = client
		self.configutils = ConfigUtils()

		# Load configuration if it exists
		self.guild_confs = self.configutils.loadConfig(self.conf_path, self.default_config, __file__)


		print('\n\nConfigs Loaded:')
		for config in self.guild_confs:
			print('\t' + config['protected']['name'] + ': ' + config['protected']['guild'])

	def getArgs(self, message):
		cmd = str(message.content)
		seg = str(message.content).split(' ')

		if len(seg) > 1:
			return seg
		else:
			return None

	# Required method for services (content may vary)
	async def getStatus(self, message):
		# Return True if there is a giveaway running in the source message's server
		for index in self.running_guilds:
			if str(message.guild.name) + str(message.guild.id) == index:
				return True

		return False

	async def startService(self):
		if not self.looping:
			self.looping = True
			self.loop_func.start()
			return True
		return False

	def checkCat(self, check_cat):
		if self.cat == check_cat:
			return True
		else:
			return False
	
	def checkBits(self, bits):
		return False
	
	async def runCheer(self, user, amount):
		return True

	async def update_poll_embed(self, msg, embed, seconds_diff):
		# Convert seconds to datetime
		day = seconds_diff // (24 * 3600)
		seconds_diff = seconds_diff % (24 * 3600)
		hour = seconds_diff // 3600
		seconds_diff %= 3600
		minutes = seconds_diff // 60
		seconds_diff %= 60
		seconds = seconds_diff
		time_left = "%d(days) %d(hours) %d(minutes) %d(seconds)" % (day, hour, minutes, seconds)

		poll_desc = ''
		for field in embed.fields:
			if field.name == 'Poll Description':
				poll_desc = field.value

		field_found = False
		for i in range(0, len(embed.fields)):
			if embed.fields[i].name=='Time Left':
				embed.set_field_at(i, name=embed.fields[i].name, value='```' + str(time_left) + '```', inline=False)
				field_found = True

		if not field_found:
			embed.add_field(name='Time Left', value='```' + str(time_left) + '```', inline=False)
		
		total_members = msg.guild.member_count
		required_limit = round(total_members * self.poll_win_percent)

		field_found = False
		for i in range(0, len(embed.fields)):
			if embed.fields[i].name=='Minimum required "yes" votes':
				embed.set_field_at(i, name=embed.fields[i].name, value='```' + str(required_limit) + '```', inline=False)
				field_found = True
		if not field_found:
			embed.add_field(name='Minimum required "yes" votes', value='```' + str(required_limit) + '```', inline=False)

		await msg.edit(embed=embed)

		return True

	async def close_poll_embed(self, msg, embed):
		for i in range(0, len(embed.fields)):
			if embed.fields[i].name=='Status':
				embed.set_field_at(i, name=embed.fields[i].name, value='```CLOSED```', inline=False)

				# Check votes
				yes_count = 0
				no_count = 0

				guild_conf = self.configutils.getGuildConfig(msg, self.guild_confs)
				try:
					yes_vote = guild_conf['yes_vote']['value']
				except:
					yes_vote = 0
				try:
					no_vote = guild_conf['no_vote']['value']
				except:
					no_vote = 0

				for reaction in msg.reactions:
					print(str(reaction) + ': ' + str(reaction.count))
					if str(reaction.emoji) == yes_vote:
						yes_count = reaction.count
					elif str(reaction.emoji) == no_vote:
						no_count = reaction.count

				print(str(yes_count) + ' | ' + str(no_count))

				total_members = msg.guild.member_count
				required_limit = round(total_members * self.poll_win_percent)

				if (yes_count > no_count) and (yes_count > int(required_limit)):
					embed.add_field(name='Result', value='```APPROVED```', inline=False)
					embed.add_field(name='Reason', value='```"Yes" greater than "no" and server minimum```', inline=False)
				elif yes_count < no_count:
					embed.add_field(name='Result', value='```DENIED```', inline=False)
					embed.add_field(name='Reason', value='```"no" greater than "yes"```', inline=False)
				elif (yes_count > no_count) and (yes_count < int(required_limit)):
					embed.add_field(name='Result', value='```DENIED```', inline=False)
					embed.add_field(name='Reason', value='```"Yes" votes did not surpass server minimum```', inline=False)
				else:
					embed.add_field(name='Result', value='```TIE```', inline=False)

		await msg.edit(embed=embed)

		return True

	async def check_poll_embed(self, msg, embed):
		for field in embed.fields:
			if (field.name == 'Status') and (field.value == '```OPEN```'):

				usest = pytz.timezone(self.time_zone)
				msg_time = utc.localize(msg.created_at)

				now = datetime.now()
				now = usest.localize(now)

				message_hist_sec = (now - msg_time).total_seconds()

				guild_conf = self.configutils.getGuildConfig(msg, self.guild_confs)

				try:
					poll_time_limit = int(guild_conf['time_lim']['value'])
				except:
					poll_time_limit = 0

				await self.update_poll_embed(msg, embed, poll_time_limit - message_hist_sec)

				if message_hist_sec > poll_time_limit:
					print(str(now) + ' - ' + str(msg_time))
					print('Found open Poll that needs to be closed: ' + str(message_hist_sec))
					await self.close_poll_embed(msg, embed)
		return True

	@loop(seconds = 3)
	async def loop_func(self):
		if self.looping:
			for guild in self.client.guilds:
				# Only run on guilds that have the service enabled
				if str(guild.name) + str(guild.id) not in self.running_guilds:
					continue

				guild_conf = self.configutils.getGuildConfigByGuild(guild, self.guild_confs)
				post_channel = None
				# Find where the bot will be posting its announcements
				for channel in guild.channels:
					if str(channel.mention) == guild_conf['post_channel']['value']:
						post_channel = channel

				if post_channel == None:
					continue

				# Get the messages
				messages = await post_channel.history(limit=self.message_history_limit).flatten()
				for msg in messages:
					embeds = msg.embeds
					# Check for message Poll embeds
					for embed in embeds:
						if embed.title == 'Poll':
							await self.check_poll_embed(msg, embed)
			return

	async def run(self, message, obj_list):
		# Permissions check
		if not self.configutils.hasPerms(message, False, self.guild_confs):
			await message.channel.send(message.author.mention + ' Permission denied')
			return False

		# Parse args
		arg = self.getArgs(message)

		# Config set/get check
		if arg != None:
			if await self.configutils.runConfig(message, arg, self.guild_confs, self.conf_path):
				return True

		# Do Specific Plugin Stuff

		cmd = str(message.content)
		seg = str(message.content).split(' ')
		if len(seg) < 1:
			await message.channel.send(message.author.mention + '`' + str(message.content) + '` is not the proper syntax')
			return False


		# Do service stuff
		if len(seg) == 2:
			# Check if user has admin permissions to run the service
			if not self.configutils.hasPerms(message, True, self.guild_confs):
				await message.channel.send(message.author.mention + ' Permission denied')
				return False

			the_guild = str(message.guild.name) + str(message.guild.id)

			if str(seg[1]) == 'start':
				if the_guild not in self.running_guilds:
					self.running_guilds.append(the_guild)
					print('Guilds running ' + str(self.name) + ':')
					for gu in self.running_guilds:
						print('\t' + gu)
					await message.channel.send(message.author.mention + ' Starting ' + str(self.name))
					return True

			if str(seg[1]) == 'stop':
				if the_guild in self.running_guilds:
					self.running_guilds.remove(the_guild)
					await message.channel.send(message.author.mention + ' Stopping ' + str(self.name))
					print('Guilds running ' + str(self.name) + ':')
					for gu in self.running_guilds:
						print('\t' + gu)
					return True

			return False

		# User wants status of service
		elif len(seg) == 1:
			if self.looping:
				await message.channel.send(message.author.mention + ' ' + str(self.name) + ' is running')
			else:
				await message.channel.send(message.author.mention + ' ' + str(self.name) + ' is not running')
			return True

		# Start the pole here
		test_name = ''
		for i in range(1, len(seg)):
			test_name = test_name + seg[i] + ' '
		self.poll_desc = test_name[:-1]

		embed = discord.Embed(title="Poll",
				color=discord.Color.blue())

		embed.add_field(name='Poll Description', value=str(self.poll_desc), inline=False)
		embed.add_field(name='Creator', value=str(message.author.mention), inline=False)

		embed.add_field(name='Status', value='```OPEN```', inline = False)

		post_channel = None

		the_role = None

		guild_conf = self.configutils.getGuildConfig(message, self.guild_confs)

		for role in message.guild.roles:
			if role.mention == guild_conf['tag_role']['value']:
				the_role = role

		if the_role == None:
			the_role = '@everyone'

		# Find where the bot will be posting its announcements
		for channel in message.guild.channels:
			try:
				if str(channel.mention) == str(guild_conf['post_channel']['value']):
					post_channel = channel
			except:
				try:
					if str(channel.name) == str(guild_conf['post_channel']['value']):
						post_channel = channel
				except:
					continue

		if (post_channel != None) and (the_role != None):
			msg = await post_channel.send(the_role.mention, embed=embed)

			await msg.add_reaction(guild_conf['yes_vote']['value'])

			await msg.add_reaction(guild_conf['no_vote']['value'])
		else:
			print('Could not find post channel. Not posting poll')

		return True

	async def stop(self, message):
		self.looping = False
