import collections
from collections import defaultdict
import os
import re

class CountSpecificPassesFeature():
	def __init__(self, count_file_name):
		self.counts = defaultdict(lambda: defaultdict(int))
		count_file = open(count_file_name, "r")
		for line in count_file:
			team, players, weight = line.strip().split(", ")
			self.counts[team][players] = weight

	# TODO: return smoothed count? return smoothed probability?
	def getCount(team, player1, player2):
		p_key = player1 + "-" + player2
		return self.counts[team][p_key]

class CountAvgPassesFeature():
	def __init__(self, count_file_name):
		self.avgCounts = defaultdict(lambda: defaultdict(float))
		count_file = open(count_file_name, "r")
		for line in count_file:
			team, players, weight = line.strip().split(", ")
			self.avgCounts[team][players] = weight

	def getCount(self, team, player1, player2):
		p_key = player1 + "-" + player2
		return self.avgCounts[team][p_key]

class PlayerPositionFeature():
	def __init__(self, squad_dir):

		def getTeamNameFromFile(teamFile):
			teamName = re.sub("-squad.*", "", teamFile)
			teamName = re.sub("_", " ", teamName)
			return teamName

		self.teamNumName = defaultdict(lambda: defaultdict(str))
		self.teamNumPos = defaultdict(lambda: defaultdict(str))

		for team in os.listdir(squad_dir):
			if re.search("-squad", team):
				path = squad_dir + team
				teamFile = open(squad_dir + team, "r")
				teamName = getTeamNameFromFile(team)
				for player in teamFile:
					num, name, pos = player.rstrip().split(", ")
					self.teamNumName[teamName][num] = name
					self.teamNumPos[teamName][num] = pos

	def getPos(self, teamName, num):
		return self.teamNumPos[teamName][num]

	def getName(self, teamName, num):
		return self.teamNumName[teamName][num]

	def isSamePos(self, teamName, num1, num2):
		ret = 1
		if self.getPos(teamName, num1) != self.getPos(teamName, num2):
			ret = 0
		return ret

class RankingFeature():
	def __init__(self, rankFileName):
		self.rankings = defaultdict(int)
		rank_file = open(rankFileName, "r")
		for rank in rank_file:
			rank, team = rank.rstrip().split(", ")
			self.rankings[team] = int(rank)

	def getRank(self, team):
		return self.rankings[team]

	def isHigherInRank(self, team1, team2):
		return self.getRank(team1) > self.getRank(team2)

	def getDiffInRank(self, team1, team2):
		return self.getRank(team1) - self.getRank(team2)

class MeanDegreeFeature():
	# count edges for players
	# take average 
	# store per game

	def getMatchIDFromFile(self, network):
		matchID = re.sub("_.*", "", network)
		return matchID

	def getTeamNameFromNetwork(self, network):
		teamName = re.sub("[^-]*-", "", network, count=1)
		teamName = re.sub("-edges", "", teamName)
		teamName = re.sub("_", " ", teamName)
		return teamName

	def __init__(self):
		folder = "passing_distributions/2014-15/"
		allGames = ["matchday" + str(i) for i in xrange(1, 7)]
		allGames.append("r-16")
		allGames.append("q-finals")
		allGames.append("s-finals")

		self.meanDegree = defaultdict(lambda: defaultdict(float))

		

		for matchday in allGames:
			path = folder + matchday + "/networks/"
			for network in os.listdir(path):
				if re.search("-edges", network):
					edgeFile = open(path + network, "r")

					degreePerPlayer = defaultdict(int)
					teamName = self.getTeamNameFromNetwork(network)
					matchID = self.getMatchIDFromFile(network)
					print "team: %s" % teamName
					totalDegree = 0

					for players in edgeFile:
						p1, p2, weight = players.rstrip().split("\t")
						print "p1: %s, p2: %s, weight: %f" % (p1, p2, float(weight))
						degreePerPlayer[p1] += 1

					# count number of nodes to take average over team
					nodeFile = open(path + matchID + "_tpd-" + re.sub(" ", "_", teamName) + "-nodes", "r")
					players = [line.rstrip() for line in nodeFile]
					numPlayers = len(players)
					totalDegree = 0
					for player in degreePerPlayer:
						totalDegree += degreePerPlayer[player]

					avgDegree = totalDegree / numPlayers
					# print "Avg degree for %s is %f" % (teamName, avgDegree)
					self.meanDegree[matchID][teamName] = avgDegree
	
	def getMeanDegree(self, matchID, teamName):
		return self.meanDegree[matchID][teamName]

