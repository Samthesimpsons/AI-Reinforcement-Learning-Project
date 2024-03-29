'''References:
https://github.com/Nk-Kyle/Wordle (this one)
https://www.mattefay.com/wordle
https://towardsdatascience.com/automatic-wordle-solving-a305954b746e
https://www.linkedin.com/pulse/solving-wordle-kohsuke-kawaguchi/?trk=articles_directory'''

import string
import random
import time
import numpy as np
from tqdm import tqdm

#Edited function from interface.py
def evalGuess(guess, target):
    res = ["w" for i in range(5)]
    checkedTarget = [False for i in range(5)]
    checked = [False for i in range(5)]
    #Check for right letter and position
    for i in range(5):
        if (guess[i] == target[i]):
            res[i] = "g"
            checked[i] = True
            checkedTarget[i] = True

    #Checked for right letter but wrong position
    for i in range(5):
        if (not(checked[i])):
            for j in range(5):
                if (guess[i] == target[j] and not(checkedTarget[j])):
                    res[i] = "y"
                    checkedTarget[j] = True
                    break
    return res

#Gets number of occurence of letter in word from wordlist
def calcAlphabetScorebyOccurence(wordlist):
    alphabetVal = {}
    for word in wordlist:
        for letter in set(word):
            alphabetVal[letter] = alphabetVal.get(letter, 0) + 1
    alphabetVal = sorted(alphabetVal.items(), key=lambda x: x[1], reverse=True)
    return dict(alphabetVal)

#Calculate score of each words from given wordlist and alphabet score
def calcWordScorebyOccurence(wordlist):
    alphabetVal= calcAlphabetScorebyOccurence(wordlist)
    wordScore = {}
    for word in wordlist:
        for letter in set(word):
            wordScore[word] = wordScore.get(word, 0) + alphabetVal.get(letter, 0)
    wordScore = sorted(wordScore.items(), key=lambda x: x[1], reverse=True)
    return dict(wordScore)

#Gets matrix of letters an occurence in position
def calcAlphabetScorebyPosition(wordlist):
    alphabetVal = {}
    for alphabet in string.ascii_uppercase:
        alphabetVal[alphabet] = [0 for _ in range (5)]
    for word in wordlist:
        for i in range(len(word)):
            alphabetVal[word[i]][i] += 1
    return alphabetVal

#Gets dictionary of word and its score using position occurence
def calcWordScorebyPosition(wordlist):
    alphabetScore = calcAlphabetScorebyPosition(wordlist)
    wordScore = {}
    for word in wordlist:
        for i in range(5):
            wordScore[word] = wordScore.get(word, 0) + alphabetScore[word[i]][i]
    wordScore = sorted(wordScore.items(), key=lambda x: x[1], reverse=True)
    return dict(wordScore)

#Get words from wordlist
def getGoalWords():
    words = []
    with open('models/goal_words.txt', 'r') as f:
        for lines in f:
            words.append(lines.strip().upper())
    return words

def getGuessWords():
    words = []
    with open('models/accepted_words.txt', 'r') as f:
        for lines in f:
            words.append(lines.strip().upper())
    return words

def getRandomTarget(keys):
    return random.choice(keys)

def buildTree(wordlist):
    tree = {}
    for word in wordlist:
        tree[word] = {}
        for referWord in wordlist:
            if(word != referWord):
                eval = str(evalGuess(word, referWord))
                tree[word].setdefault(eval, [])
                tree[word][eval].append(referWord)
    return tree

#Decrease words from wordscores given information green (correct place)
def solveGreen(wordscores, guessWord, toEvaluate, guessResult):
    wordscores.pop(guessWord,None)
    key_list= list(wordscores)
    indices = []
    for i in range(5):
        if(guessResult[i] == "g"):
            toEvaluate[i] = guessWord[i]
            indices.append(i)
    for wordsLeft in key_list:
        for i in indices:
            if (wordsLeft[i] not in toEvaluate[i]):
                wordscores.pop(wordsLeft,None)
                break
    return wordscores, toEvaluate

def solveYellow(wordscores, guessWord, toEvaluate, guessResult):
    wordscores.pop(guessWord,None)
    key_list= list(wordscores)
    indices = []
    for i in range(5):
        if(guessResult[i] == "y"):
            toEvaluate[i]= toEvaluate[i].replace(guessWord[i], '')
            indices.append(i)
    for wordsLeft in key_list:
        for i in indices:
            if (guessWord[i] not in wordsLeft or wordsLeft[i] not in toEvaluate[i]):
                wordscores.pop(wordsLeft,None)
                break
    return wordscores, toEvaluate

def solveGray(wordscores, guessWord, toEvaluate, guessResult):
    wordscores.pop(guessWord,None)
    key_list= list(wordscores)
    indices = []
    for i in range(5):
        if(guessResult[i] == "w"):
            indices.append(i)
    
    for i in indices:
        toEvaluate[i] = toEvaluate[i].replace(guessWord[i], '')

    for wordsLeft in key_list:
        for i in indices:
            if(wordsLeft[i] not in toEvaluate[i]):
                wordscores.pop(wordsLeft,None)
                break
    return wordscores, toEvaluate

def solveWithAll(wordscores,guessWord, toEvaluate, guessResult):
    wordscores,toEvaluate = solveGreen(wordscores,guessWord, toEvaluate, guessResult)
    wordscores,toEvaluate = solveYellow(wordscores,guessWord, toEvaluate, guessResult)
    wordscores,toEvaluate = solveGray(wordscores,guessWord, toEvaluate, guessResult)
    return wordscores, toEvaluate

def solveTree(wordscores,guessWord,tree, guessResult):
    filter = tree[guessWord][str(guessResult)]
    for word in list(wordscores):
        if word not in filter:
            wordscores.pop(word,None)
    return wordscores

#Edited function from interface.py
def printGuess(guess, target):
    res = evalGuess(guess, target)
    #Print Top box lines
    top = ""
    for color in res:
        top += f" |{color}| "
    print(top)

    #Print middle box lines with letter
    mid = ""
    for i in range(5):
        mid += f" |{guess[i]}| "
    print(mid)
    print()

    return res

def checkGuess(evaluations):
    for eval in evaluations:
        if (eval != "g"):
            return False
    return True

def run_simulations(num_simulations:int):
    toc = time.time()
    guesses = np.zeros(num_simulations)
    goalwords = getGoalWords()
    guesswords = getGuessWords()

    for epoch in tqdm(range(num_simulations)):
        attempt = 1

        ''' Line 8 and 9 interchangable for scoring words with different methods'''
        wordScore2k = calcWordScorebyOccurence(goalwords)
        wordscore13k = calcWordScorebyOccurence(guesswords)
        # print(wordScore)
        # wordScore = calcWordScorebyPosition(words)

        '''Get a random word to use as a target to guess'''
        targetWord = getRandomTarget(list(wordScore2k))

        '''Preprocess'''
        toEvaluate = [string.ascii_uppercase for _ in range(5)]

        '''Start guessing'''
        guess = "CRANE"
        # printGuess(guess,targetWord)
        evaluation = evalGuess(guess,targetWord)
        while(not(checkGuess(evaluation))):
            wordScore13k,toEvaluate = solveWithAll(wordscore13k, guess, toEvaluate, evaluation)
            guess = list(wordScore13k)[0]
            evaluation = evalGuess(guess,targetWord)
            # printGuess(guess,targetWord)
            attempt+=1
        # print("*************************")
        # print()

        guesses[epoch] = attempt
    tic = time.time()

    time_taken = tic - toc
    average_guesses = np.mean(guesses)
    win_rate = (num_simulations-np.sum(guesses>6))/num_simulations*100

    # print(f'Time taken: {time_taken}')
    # print(f'Average guesses: {average_guesses}')
    # print(f'Total game losses out of {num_simulations}: {np.sum(guesses>6)}')
    # print(f'Overall win rate: {win_rate}%')

    return time_taken, average_guesses, win_rate, guesses

if __name__ == '__main__':
    run_simulations(1000)