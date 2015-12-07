import collections, util, math, random
import classes, scoring
import copy
import os
import glob
import re
from collections import defaultdict
import unicodedata
import random

class PredictPD():

	def __init__(self):

		# each team has its own set of weights
		self.weights = defaultdict(lambda: defaultdict(int))

		self.stepSize = 0.01

		self.matchdays = ["matchday" + str(i) for i in xrange(1, 7)]
		# uncomment if want to add round of 16 games to matchdays
		# self.matchdays.append("r-16")

		# # uncomment if want to add quarter final games to matchdays
		# self.matchdays.append("q-finals")

		self.folder = "passing_distributions/2014-15/"

		# init feature classes
		countAvgFile = "avg_passes_count.txt"
		self.countAvgPassesFeature = classes.CountAvgPassesFeature(countAvgFile)

		squad_dir = "squads/2014-15/squad_list/"
		self.playerPosFeature = classes.PlayerPositionFeature(squad_dir)

		rankFile = "rankings/2013_14_rankings.txt"
		self.rankFeature = classes.RankingFeature(rankFile)

		# init data structures
		self.matches = defaultdict(str)

		self.totalPassesBetweenPos = defaultdict(lambda: defaultdict(int))
		self.totalPassesBetweenPlayers = defaultdict(lambda: defaultdict(int))
		self.totalPasses = defaultdict(int)

		self.teamNumToPos = defaultdict(lambda: defaultdict(str))
		self.initTeamNumToPos(squad_dir)

		self.passVolPerTeam = defaultdict(int)
		self.passPercPerTeam = defaultdict(float)

		self.teamStatsByMatch = defaultdict(lambda: defaultdict(list))

	# Average pairwise error over all players in a team
	# given prediction and gold
	def evaluate(self, features, weight, teamName):
		score = self.computeScore(features, self.weights[teamName])
		loss = self.computeLoss(features, self.weights[teamName], float(weight))
		return (score, loss)

	def computeLoss(self, features, weights, label):
		return (self.computeScore(features, weights) - label)**2

	# score is dot product of features & weights
	def computeScore(self, features, weights):
		score = 0.0
		for v in features:
			score += float(features[v]) * float(weights[v])
		return score

	# returns a vector
	# 2 * (phi(x) dot w - y) * phi(x)
	def computeGradientLoss(self, features, weights, label):
		scalar =  2 * self.computeScore(features, weights) - label
		mult = copy.deepcopy(features)
		for f in mult:
			mult[f] = float(mult[f])
			mult[f] *= scalar
		return mult

	# use SGD to update weights
	def updateWeights(self, features, weights, label, teamName):
		grad = self.computeGradientLoss(features, weights, label)
		for w in self.weights[teamName]:
			self.weights[teamName][w] -= self.stepSize * grad[w]

	def getTeamNameFromNetwork(self, network):
		teamName = re.sub("[^-]*-", "", network, count=1)
		teamName = re.sub("-edges", "", teamName)
		teamName = re.sub("_", " ", teamName)
		return teamName

	def getTeamNameFromFile(self, teamFile):
		teamName = re.sub("-squad.*", "", teamFile)
		teamName = re.sub("_", " ", teamName)
		return teamName

	def initTeamNumToPos(self, squad_dir):
		for team in os.listdir(squad_dir):
			if re.search("-squad", team):
				path = squad_dir + team
				teamFile = open(squad_dir + team, "r")
				teamName = self.getTeamNameFromFile(team)
				for player in teamFile:
					num, name, pos = player.rstrip().split(", ")
					self.teamNumToPos[teamName][num] = pos

	def getMatchIDFromFile(self, network):
		matchID = re.sub("_.*", "", network)
		return matchID

	def getOppTeam(self, matchID, teamName):
		team1, team2 = self.matches[matchID].split("/")
		if team1 == teamName:
			return team2
		else: return team1

	# returns the index of where to look for the scores
	def getMatchday(self, matchID):
		matchID = int(matchID)
		if matchID <= 2014322:
			return 0
		elif matchID >=2014323 and matchID <= 2014338:
			return 1
		elif matchID >= 2014339 and matchID <= 2014354:
			return 2
		elif matchID >= 2014354 and matchID <= 2014370:
			return 3
		elif matchID >= 2014371 and matchID <= 2014386:
			return 4
		elif matchID >= 2014387 and matchID <= 2014402:
			return 5
		elif matchID >= 2014403 and matchID <= 2014418:
			return 6
		elif matchID >= 2014419 and matchID <= 2014426:
			return 7
		elif matchID >= 2014427 and matchID <= 2014430:
			return 8

	def featureExtractor(self, teamName, p1, p2, matchID, matchNum, weight):

		avgPasses = self.countAvgPassesFeature.getCount(teamName, p1, p2)
		p_key = p1 + "-" + p2
		self.totalPassesBetweenPlayers[teamName][p_key] += float(weight)
		totalPasses = self.totalPassesBetweenPlayers[teamName][p_key]
		avgPasses = totalPasses / (matchNum + 1)

		isSamePos = self.playerPosFeature.isSamePos(teamName, p1, p2)
		isDiffPos = abs(1 - isSamePos)

		oppTeam = self.getOppTeam(matchID, teamName)
		diffInRank = self.rankFeature.isHigherInRank(teamName, oppTeam)

		features = defaultdict(float)
		features["avgPasses"] = avgPasses
		features["isSamePos"] = isSamePos
		features["isDiffPos"] = isDiffPos
		features["diffInRank"] = diffInRank

		pos1 = self.teamNumToPos[teamName][p1]
		pos2 = self.teamNumToPos[teamName][p2]

		# keep a running total of past passes between positions
		# how about a running average...
		p_key = pos1 + "-" + pos2
		self.totalPassesBetweenPos[teamName][p_key] += int(weight)
		self.totalPasses[teamName] += int(weight)
		avgPassesPerPos = self.totalPassesBetweenPos[teamName][p_key] / float(self.totalPasses[teamName])
		features["avgPassesPerPos"] = avgPassesPerPos

		avgPassVol = self.passVolPerTeam[teamName] / (matchNum + 1.0)
		avgPassPerc = self.passPercPerTeam[teamName] / (matchNum + 1.0)

		oppAvgPassVol = self.passVolPerTeam[oppTeam] / (matchNum + 1.0)
		oppAvgPassPerc = self.passPercPerTeam[oppTeam] / (matchNum + 1.0)
        
		features["avgPassVol"] = 1 if avgPassVol > oppAvgPassVol else 0
		features["avgPassPerc"] = 1 if avgPassPerc > oppAvgPassPerc else 0

		# for feature: won against a similar ranking team
		# 1. define history that we are able to use, i.e. previous games
		matchday = self.getMatchday(matchID)
		history = self.teamPlayedWith[teamName][:matchday]

		if len(history) > 0:
			def computeSim(rank1, rank2):
				return (rank1**2 + rank2**2)**0.5

			# 2. find most similar opponent in terms of rank
			# TODO: similarity could be defined better?
			oppTeamRank = self.rankFeature.getRank(oppTeam)
			simTeam = ""
			simTeamDistance = float('inf')
			rank1 = oppTeamRank
			for team in history:
				rank2 = self.rankFeature.getRank(team)
				sim = computeSim(rank1, rank2)
				if sim < simTeamDistance:
					simTeamDistance = sim
					simTeam = sim
			print "matchID is %s" % matchID
			print "Matchday is %d" % matchday
			# 3. find out whether the game was won or lost
			features["wonAgainstSimTeam"] = self.teamWonAgainst[teamName][matchday]

		return features

	def initMatches(self):
		# store match data for all games
		# match data including team + opponent team
		for matchday in self.matchdays:
			path = self.folder + matchday + "/networks/"
			for network in os.listdir(path):
				if re.search("-edges", network):
					edgeFile = open(path + network, "r")
					teamName = self.getTeamNameFromNetwork(network)
					matchID = self.getMatchIDFromFile(network)

					m = self.matches[matchID]
					if m == "":
						self.matches[matchID] = teamName
					else:
						self.matches[matchID] += "/" + teamName

		allScoresFilename = "allScores.txt"
		allScores = open(allScoresFilename, "r")
		self.matchesWithScores = [line.rstrip() for line in allScores]
		self.teamPlayedWith = defaultdict(list)
		self.teamWonAgainst = defaultdict(list)

		# for every team, store opponents in order by matchday
		for match in self.matchesWithScores:
			team1, score1, score2, team2 = match.split(", ")
			team1Won = 0
			if score1 > score2:
				team1Won = 1

			self.teamPlayedWith[team1].append(team2)
			self.teamPlayedWith[team2].append(team1)
			self.teamWonAgainst[team1].append(team1Won)
			self.teamWonAgainst[team2].append(abs(1 - team1Won))

	def initTeamStats(self):
		for matchday in self.matchdays:
			path = self.folder + matchday + "/networks/"
			# iterate over games
			for network in os.listdir(path):
				if re.search("-team", network):
					# store per match
					# or store per team?
					teamName = self.getTeamNameFromNetwork(network)
					teamName = re.sub("-team", "", teamName)
					matchID = self.getMatchIDFromFile(network)

					stats_file = open(path + network, "r")
					for line in stats_file:
						stats = line.rstrip().split(", ")
					
					self.teamStatsByMatch[teamName][matchID] = stats

	# Training
	# 	have features calculate numbers based on data
	# 	learn weights for features via supervised data (group stage games) and SGD/EM
	def train(self):
		# iterate over matchdays, predicting passes, performing SGD, etc.

		num_iter = 5
		self.initMatches()
		self.initTeamStats()
		
		pos = ["GK", "STR", "DEF", "MID"]
		allPosCombos = [pos1 + "-" + pos2 for pos1 in pos for pos2 in pos]

		for i in xrange(num_iter):
			avgLoss = 0
			totalEx = 0
			print "Iteration %s" % i
			print "------------"
			# for w in self.weights:
			# 	print "weights[%s] = %f" % (w, float(self.weights[w]))
			# iterate over matchdays -- hold out on some matchdays
			matchNum = 0

			# # try shuffling matchdays
			# random.shuffle(self.matchdays)

			allGames = []

			for matchday in self.matchdays:
				# print "On " + matchday
				path = self.folder + matchday + "/networks/"
				# iterate over games
				for network in os.listdir(path):
					if re.search("-edges", network):
						# passesBetweenPos = defaultdict(lambda: defaultdict(int))
						allGames.append((path, network))


			# try shuffling games
			# random.shuffle(allGames)

			for i, game in enumerate(allGames):
				if i % 32 == 0:
					print "On matchday %d" % (i / 32 + 1)
				path, network = game
				edgeFile = open(path + network, "r")

				teamName = self.getTeamNameFromNetwork(network)
				matchID = self.getMatchIDFromFile(network)
				# print "team: %s" % teamName
				for players in edgeFile:
					p1, p2, weight = players.rstrip().split("\t")
					# print "p1: %s, p2: %s, weight: %f" % (p1, p2, float(weight))

					teamFile = open(path + matchID + "_tpd-" + re.sub(" ", "_", teamName) + "-team", "r")
					for line in teamFile:
						stats = line.rstrip().split(", ")
					self.passVolPerTeam[teamName] += float(stats[0])
					self.passPercPerTeam[teamName] += float(stats[1])

					features = self.featureExtractor(teamName, p1, p2, matchID, matchNum, weight)

					# for f in features:
					# 	print "features[%s] = %f" % (f, float(features[f]))
					# for w in self.weights[teamName]:
					# 	print "weights[%s][%s] = %f" % (teamName, w, float(self.weights[teamName][w]))

					score, loss = self.evaluate(features, weight, teamName)
 					self.updateWeights(features, self.weights[teamName], int(weight), teamName)
 					# for w in self.weights[teamName]:
						# print "weights[%s][%s] = %f" % (teamName, w, float(self.weights[teamName][w]))
 					avgLoss += loss
					totalEx += 1
 				matchNum += 1
			print "Average loss: %f" % (avgLoss / totalEx)	

	# Testing
	#	Predict, then compare with dev/test set (r-16 games)
	def test(self):
		# sum up average error

		print "Testing"
		print "-------"
		avgLoss = 0
		totalEx = 0
		matchNum = 0
		# for matchday in self.matchdays[4:]:
		matchday = "r-16"
		print "On " + matchday
		path = self.folder + matchday + "/networks/"
		# iterate over games
		for network in os.listdir(path):
			if re.search("-edges", network):
				edgeFile = open(path + network, "r")

				predEdgeFile = open("predicted/pred-" + network, "w+")

				teamName = self.getTeamNameFromNetwork(network)
				matchID = self.getMatchIDFromFile(network)
				print "team: %s" % teamName
				for players in edgeFile:
					p1, p2, weight = players.rstrip().split("\t")
					print "p1: %s, p2: %s, weight: %f" % (p1, p2, float(weight))

					features = self.featureExtractor(teamName, p1, p2, matchID, matchNum, weight)

					for f in features:
						print "features[%s] = %f" % (f, float(features[f]))
					for w in self.weights[teamName]:
						print "weights[%s][%s] = %f" % (teamName, w, float(self.weights[teamName][w]))

					score, loss = self.evaluate(features, weight, teamName)

					# print out predicted so can visually compare to actual
					predEdgeFile.write(p1 + "\t" + p2 + "\t" + str(score) + "\n")

					avgLoss += loss
					totalEx += 1
				matchNum += 1
		print "Average loss: %f" % (avgLoss / totalEx)

pred = PredictPD()
pred.train()
pred.test()
