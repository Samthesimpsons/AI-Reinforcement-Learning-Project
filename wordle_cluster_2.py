import re
import time
import random
import numpy as np
from tqdm import tqdm
from leven import levenshtein
from sklearn.cluster import AgglomerativeClustering
import matplotlib.pyplot as plt

''' List of feasible words that our reinforcement learning model will be trained on, 
5-letter words from Wordle. Source: https://www.nytimes.com/games/wordle/index.html
Extracted the 2309 goal words from the source code javascript file and then sorted accordingly. 
https://www.pcmag.com/how-to/want-to-up-your-wordle-game-the-winning-word-is-right-on-the-page'''
words = []
with open('goal_words.txt', 'r') as file:
    for word in file:
        words.append(word.strip('\n').upper())

''' Instead of the words themselves being the state of the game, and also to further reduce the search space,
the idea of clustering comes into mind. The motivation also came from https://github.com/danschauder/wordlebot/blob/main/Wordle_Bot.ipynb.
However, we will do doing our own version and not referencing the above repository. Best way to learn is to do it yourself!

In order to measure the similarity between two words without the sentiment value, we can make use of the levenshtein distance or better
known as the edit distance, which is really the minimum number of single-character edits required to change from one word to another.
For clustering wise, instead of viewing the space of words as a vector space, since we are comparing words between each other, an hierarchical
tree structure seems the most appropriate. Next consideration, is whether a top-down or bottom-up clustering approach is more feasible. Since the 
nodes of the tree are the words themselves and we want to group similar words together, a bottom-up approach is more suited.

Hence the choice of clustering would be to use agglomerative hierarchical clustering based on levenshtein distance measure.'''

''' Custom Clustering class that does the clustering based on the similarities of the words'''
class Clustering():
    def __init__(self, number_of_clusters):
        self.number_of_clusters = number_of_clusters

    def get_dist_matrix(self, corpus):
        n = len(corpus)
        distance_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i, n):
                distance_matrix[i, j] = levenshtein(corpus[i], corpus[j])
                distance_matrix[j, i] = distance_matrix[i, j]
        return distance_matrix

    def get_indexes_of_cluster(self, cluster_number: int, clusters):
        indexes = []
        for index, number in enumerate(clusters):
            if cluster_number == number:
                indexes.append(index)
        return indexes

    def get_chosen_word(self, indexes, corpus):
        chosen_word_index = random.choice(indexes)
        return corpus[chosen_word_index]

    def get_clusters(self, corpus):
        distance_matrix = self.get_dist_matrix(corpus)
        # Can do simulation analysis to test the parameters
        clusters = AgglomerativeClustering(
            n_clusters=self.number_of_clusters, affinity='precomputed', linkage='average').fit_predict(distance_matrix)
        return clusters


'''The new idea now shall be, for each simulation run of the RL algorithm:
1. Do clustering on the whole corpus
then for each iteration 
2. Use Q-leaning to select the a cluster from which to draw our word from
3. The word drawn will be a random word from the chosen cluster
4. Evaluate the word, calculate the reward, to fliter the cluster
5. Either explore other clusters or exploit the Q-table argmax'''

''' Custom Wordle class that defines the state of the wordle and the actions (and reward) that can be taken 
also includes getter methods for the state and the goal word '''
class Wordle():
    def __init__(self):
        self.current_word = None
        self.current_state = 1
        self.goal_word = random.choice(words)
        self.reached_goal = False

    def get_state(self):
        return self.current_state

    def get_curr_word(self):
        return self.current_word

    def get_goal(self):
        return self.goal_word

    def make_action(self, action, state):
        # scoring based on yellow, green & black letters
        if self.current_word == None:
            current_score = {'green': 0, 'yellow': 0, 'black': 0}
        else:
            current_score = eval.get_score(self.current_word, self.goal_word)

        # select next word and get a new scoring
        self.current_word = action
        self.current_state = state
        new_score = eval.get_score(self.current_word, self.goal_word)

        # calculate reward of previous word to new word
        reward = eval.get_reward(current_score, new_score)

        # if ever the case the goal state is reached, True is returned
        if self.current_word == self.goal_word:
            return reward, True
        return reward, False

''' Custom Evaluation class that contains the getter methods for the scoring and reward of the wordle.
The scoring is based on the number of yellow, green and black letters in the wordle.
The reward is based on the number of yellow (=/-5), green (+/-10) and black letters (-/+1) in the wordle.
Includes filter function to help reduce the search space of the wordle. '''
class eval():
    def __init__(self):
        pass

    def get_score(word_1, word_2):
        scoring = {'green': 0, 'yellow': 0, 'black': 0}

        for i in range(5):
            if word_1[i] == word_2[i]:
                scoring['green'] += 1
            elif word_1[i] in word_2:
                scoring['yellow'] += 1
            else:
                scoring['black'] += 1
        return scoring

    def get_reward(scoring_1, scoring_2):
        reward = 0
        reward += (scoring_1['green'] - scoring_2['green'])*10
        reward += (scoring_1['yellow'] - scoring_2['yellow'])*5
        reward -= (scoring_1['black'] - scoring_2['black'])*1
        return reward

    def filter(word_1, word_2, words):
        '''
        Cases: to cover all possible cases
        SOULS vs APPLE, all no match
        TRAIN vs APPLE, A match wrong position
        ALOUD vs APPLE, L match wrong posiiton, A match correct position
        ABOVE vs APPLE, A/E match correct position
        '''
        black_letters = []  # list of black letters
        yellow_letters = {}  # key-val pair of yellow letters and their positions
        green_letters = {}  # key-val pair of green letters and their positions
        for i in range(5):
            if word_1[i] != word_2[i] and word_1[i] not in word_2:
                black_letters.append(word_1[i])
            elif word_1[i] == word_2[i]:
                green_letters[word_1[i]] = i
            elif word_1[i] != word_2[i] and word_1[i] in word_2:
                yellow_letters[word_1[i]] = i

        # Remove any words with the black letters
        if len(black_letters) != 0:
            strings_to_remove = "[{}]".format("".join(black_letters))
            words = [word for word in words if (
                re.sub(strings_to_remove, '', word) == word)]

        # Keep only words with correct green position 
        if len(green_letters) != 0:
            for key, value in green_letters.items():
                words = [word for word in words if word[value] == key]

        # Do not keep words with yellow letters in current position
        if len(yellow_letters) != 0:
            for key, value in yellow_letters.items():
                words = [word for word in words if word[value] != key]

        # Do not keep words without yellow letters in other positions
        if len(yellow_letters) != 0:
            for yellow_letter in yellow_letters.keys():
                words = [word for word in words if yellow_letter in word]

        if word_1 in words:
            words.remove(word_1)
        # return filtered corpus
        return words

def reinforcement_learning(learning_rate: int,
                           exploration_rate: int, 
                           shrinkage_factor: int, 
                           number_of_cluster: int,
                           pairwise_distance_matrix: np.ndarray,
                           cluster_assignment: np.ndarray, 
                           Q_table: np.ndarray,
                           custom_goal: bool, 
                           custom_goal_word = None):
    epsilon = exploration_rate  # probability of random action, exploration
    alpha = learning_rate  # learning rate
    gamma = shrinkage_factor  # discounting factor

    wordle = Wordle()
    done = False
    steps = 1

    # initialize Q-table, goal word and the current corpus
    if custom_goal:
        goal_word = custom_goal_word
    else:
        goal_word = wordle.get_goal()
    curr_corpus = words.copy()
    
    if goal_word == 'CRANE':
        return 1, ['CRANE']

    # q_table = np.zeros((number_of_cluster, number_of_cluster))
    q_table = Q_table

    # initialize distance matrix (similarities) and the clustering results
    distance_matrix = pairwise_distance_matrix
    cluster_results = cluster_assignment

    # Initialize the first word
    wordle.current_word = 'CRANE'
    wordle.current_state = cluster_results[curr_corpus.index(
        wordle.get_curr_word())]

    visited_words = []
    while not done:
        # get the cluster number and the word to filter on
        state = wordle.get_state()
        word_to_filter_on = wordle.get_curr_word()
        visited_words.append(word_to_filter_on)

        # keep track of the corpus before and after filtering (cutting search space)
        prev_corpus = curr_corpus.copy()
        curr_corpus = eval.filter(word_to_filter_on, goal_word, curr_corpus)

        # Similarly, reduce the search space of the matrices
        indices_removed = []
        for i, word in enumerate(prev_corpus):
            if word not in curr_corpus:
                indices_removed.append(i)

        distance_matrix = np.delete(distance_matrix, indices_removed, axis=0)
        distance_matrix = np.delete(distance_matrix, indices_removed, axis=1)
        cluster_results = np.delete(cluster_results, indices_removed, axis=0)
        
        # exploration
        epsilon = epsilon / (steps ** 2)
        if random.uniform(0, 1) < epsilon:
            list_of_states_to_explore = list(set(cluster_results))
            if len(list_of_states_to_explore) != 1:
                if state in list_of_states_to_explore:
                    list_of_states_to_explore.remove(state)
            action_index = random.choice(list_of_states_to_explore)

        # exploitation
        else:
            # Q-table is very sparse in beginning, hence if the row of Q-table all similar still (0), do exploration still
            if np.all(q_table[state][i] == q_table[state][0] for i in range(len(curr_corpus))):
                list_of_states_to_explore = list(set(cluster_results))
                if len(list_of_states_to_explore) != 1:
                    if state in list_of_states_to_explore:
                        list_of_states_to_explore.remove(state)
                action_index = random.choice(list_of_states_to_explore)
            # else exploit as usual
            else:
                action_index = np.argmax(q_table[state])

        c = Clustering(number_of_cluster)
        action = c.get_chosen_word(c.get_indexes_of_cluster(action_index, cluster_results), curr_corpus)

        # get reward and update Q-table
        reward, done = wordle.make_action(action, action_index)
        new_state_max = np.max(q_table[action_index])

        q_table[state, action_index] = (1 - alpha)*q_table[state, action_index] + alpha*(
            reward + gamma*new_state_max - q_table[state, action_index])

        # Increment the steps
        steps = steps + 1

        # exit condition in case search too long, set currently to total length of initial corpus
        if steps >= len(words):
            break

    visited_words.append(goal_word)
    return steps, visited_words


if __name__ == '__main__':

    training_epochs = 1000
    epochs = np.arange(training_epochs)
    guesses = np.zeros(training_epochs)

    number_of_cluster = 10

    toc_1 = time.time()
    clust = Clustering(number_of_cluster)
    distance_matrix = clust.get_dist_matrix(words)
    cluster_results = clust.get_clusters(words)
    tic_1 = time.time()

    Q_table = np.zeros((number_of_cluster, number_of_cluster))

    toc_2 = time.time()
    for epoch in range(training_epochs):
        steps, visited_words = reinforcement_learning(
            learning_rate=0.1, 
            exploration_rate=0.9, 
            shrinkage_factor=0.9, 
            number_of_cluster=number_of_cluster, 
            pairwise_distance_matrix=distance_matrix, 
            cluster_assignment=cluster_results,
            Q_table=Q_table,
            custom_goal=False, custom_goal_word=None)
        print(visited_words)
        guesses[epoch] = steps
    tic_2 = time.time()

    print(f'Time for clustering: {tic_1 - toc_1}')
    print(f'Time for learning: {tic_2 - toc_2}')
    print(f'Average guesses: {np.mean(guesses)}')
    print(f'Total game losses out of {training_epochs}: {np.sum(guesses>6)}')
    print(f'Overall win rate: {(training_epochs-np.sum(guesses>6))/training_epochs*100}%')

    # Plot results as a bar or histogram
    plt.bar(epochs, guesses)
    # # plt.hist(guesses)
    plt.show()