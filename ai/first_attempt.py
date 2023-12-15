import random
from risktools import *
# For interacting with interactive GUI
from gui.aihelper import *
from gui.turbohelper import *

WEIGHTS = {
    "border_territories": 100,
    "num_armies": 2,
    "num_territories": 1,
    "mismatched_armies": 1
}


### HEURISTIC AI ####
# 
#  This is the beginning of an AI that will simulate all allowed actions, evaluate each possible resulting state 
#  with a heuristic function, and select the action that leads to the highest expected heuristic value. 
#  
#  To complete this AI, simply implement the "heuristic" function below, returning a real number for a given state

def getAction(state, time_left=None):
    """Main AI function.  It should return a valid AI action for this state."""

    # Get the possible actions in this state
    actions = getAllowedActions(state)

    # Execute each action and get expected heuristic value of resulting state 

    # To keep track of the best action we find
    best_action = None
    best_action_value = None

    # Evaluate each action
    for a in actions:

        a.print_action()

        # Simulate the action, get all possible successor states
        successors, probabilities = simulateAction(state, a)

        # Compute the expected heuristic value of the successors
        current_action_value = 0.0

        for i in range(len(successors)):
            # Each successor contributes its heuristic value * its probability to this action's value
            current_action_value += (heuristic(successors[i]) * probabilities[i])

        # Store this as the best action if it is the first or better than what we have found
        if best_action_value is None or current_action_value > best_action_value:
            best_action = a
            best_action_value = current_action_value

        print("Action: ")
        a.print_action()
        print(" has value " + str(current_action_value))

    print("Current player: " + str(state.current_player))

    # Return the best action
    return best_action


def heuristic(state: RiskState):
    """Returns a number telling how good this state is. 
       Implement this function to have a heuristic ai. """

    # state.board: RiskBoard
    # state.board.continents: list[RiskContinent]
    #
    #
    #
    # for key in state.board.continents:
    #     state.board.continents[key]: RiskContinent
    #     for i in state.board.continents[key].territories:
    #         territory = state.board.territories[i]
    #         if territory.name == "Alaska":
    #             print(territory.print_territory(state.board))
    #     # print(state.board.continents[key].name, end="; ")
    # # print()
    # for i in range(len(state.board.territories)):
    #     state.board.territories[i]: RiskTerritory
    #     territory = state.board.territories[i]
    #     # if the territory borders another country, append 1 to the array, otherwise append 0
    #     for neighbor in territory.neighbors:
    #         if state.board.territories[neighbor]
    #     # print(state.board.territories[i].name, end=", ")
    # # print()

    border_countries_heuristic = [1, 0, 1, 0, 0, 0, 0, 0, 1,  # North America
                                  1, 1, 0, 0,  # South America
                                  0, 0, 1, 1, 1, 0,  # Africa
                                  1, 0, 1, 0, 0, 1, 1,  # Europe
                                  1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1,  # Asia
                                  1, 0, 0, 0]  # Australia

    for i in range(len(border_countries_heuristic)):
        value = border_countries_heuristic[i]
        print(state.owners[i], state.current_player)
        if state.owners[i] != state.current_player:
            value *= -1
        border_countries_heuristic[i] = value * WEIGHTS["border_territories"]

    num_armies_heuristic = get_blank_heuristic_array()
    for i in range(len(state.owners)):
        if state.owners[i] == state.current_player:
            num_armies_heuristic[i] = state.armies[i]
        else:
            num_armies_heuristic[i] = -1 * state.armies[i]
        num_armies_heuristic[i] *= WEIGHTS["num_armies"]

    num_territories_heuristic = get_blank_heuristic_array()
    for i in range(len(state.owners)):
        if state.owners[i] == state.current_player:
            num_territories_heuristic[i] = 1
        else:
            num_territories_heuristic[i] = -1
        num_territories_heuristic[i] *= WEIGHTS["num_territories"]

    mismatched_armies_heuristic = get_blank_heuristic_array()
    for i in range(len(state.owners)):
        evil_enemies = 0
        if state.owners[i] == state.current_player:
            for neighbor in state.board.territories[i].neighbors:
                if state.owners[neighbor] != state.current_player:
                    evil_enemies += 1
        if state.armies[i] > evil_enemies:
            mismatched_armies_heuristic[i] = 1
        else:
            mismatched_armies_heuristic[i] = evil_enemies * -1
        mismatched_armies_heuristic[i] *= WEIGHTS["mismatched_armies"]

    print("border_countries_heuristic:", border_countries_heuristic)
    print("num_armies_heuristic:", num_armies_heuristic)
    print("num_territories_heuristic:", num_territories_heuristic)
    print("mismatched_armies_heuristic:", mismatched_armies_heuristic)

    value_of_state = sum(border_countries_heuristic) + \
                     sum(num_armies_heuristic) + \
                     sum(num_territories_heuristic) + \
                     sum(mismatched_armies_heuristic)
    return value_of_state


def get_blank_heuristic_array():
    return [0 for i in range(42)]


# def find_border_territories(state: RiskState):
#     array = []
#     continents = {}
#
#     for key in state.board.continents:
#         state.board.continents[key]: RiskContinent
#         continents[key] = []
#         for i in state.board.continents[key].territories:
#             state.board.territories[i]: RiskTerritory
#             curr_territory = state.board.territories[i]
#             continents[key].append(curr_territory)
#
#     for curr_continent_name in continents:
#         curr_continent_territory_list = continents[curr_continent_name]
#         # print(curr_continent_territory_list)
#
#         for curr_territory in curr_continent_territory_list:
#             found = False
#             for neighbor in curr_territory.neighbors:
#                 # print(neighbor, end=" ")
#                 print("neighbor: ", neighbor)
#                 if state.board.territories[neighbor] not in curr_continent_territory_list:
#                     array.append(1)
#                     found = True
#                     break
#             if not found:
#                 array.append(0)
#
#     return array


# Code below this is the interface with Risk.pyw GUI version
# DO NOT MODIFY

def aiWrapper(function_name, occupying=None):
    game_board = createRiskBoard()
    game_state = createRiskState(game_board, function_name, occupying)
    print('AI Wrapper created state. . . ')
    game_state.print_state()
    action = getAction(game_state)
    return translateAction(game_state, action)


def Assignment(player):
    # Need to Return the name of the chosen territory
    return aiWrapper('Assignment')


def Placement(player):
    # Need to return the name of the chosen territory
    return aiWrapper('Placement')


def Attack(player):
    # Need to return the name of the attacking territory, then the name of the defender territory
    return aiWrapper('Attack')


def Occupation(player, t1, t2):
    # Need to return the number of armies moving into new territory
    occupying = [t1.name, t2.name]
    return aiWrapper('Occupation', occupying)


def Fortification(player):
    return aiWrapper('Fortification')
