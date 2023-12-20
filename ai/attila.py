from risktools import *
# For interacting with interactive GUI
from gui.aihelper import *
from gui.turbohelper import *
import copy



### ATILLA AI ####
#
#
class Singleton:
    _instance = None
    HAS_GOTTEN_RISK_CARD = False  # Member variable to track if the instance has gotten a risk card
    CONTINENT_TAKE_OVER_MODE = False  # Member variable to track if the instance is in continent take over mode
    PLAYERS_LEFT = 0
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def has_gotten_risk_card(self):
        return self.HAS_GOTTEN_RISK_CARD

    def set_has_gotten_risk_card(self, value):
        self.HAS_GOTTEN_RISK_CARD = value


singleton_instance = Singleton()

def getAction(state, time_left=None):
    """Main AI function.  It should return a valid AI action for this state."""

    players_left = set()
    for territory in state.board.territories:
        if state.owners[territory.id] is not None:
            players_left.add(state.owners[territory.id])

    singleton_instance.PLAYERS_LEFT = len(players_left)

    # Get the possible actions in this state
    actions = getAllowedActions(state)

    # Select a Random Action (to use for who knows why)
    selected_action = random.choice(actions)

    continents_name_to_territory_name = {}
    for key in state.board.continents:
        state.board.continents[key]: RiskContinent
        continents_name_to_territory_name[key] = []
        for i in state.board.continents[key].territories:
            state.board.territories[i]: RiskTerritory
            curr_territory = state.board.territories[i]
            continents_name_to_territory_name[key].append(curr_territory.name)

    if state.turn_type == 'PreAssign':
        selected_action = decide_presign(state, actions, continents_name_to_territory_name)

    if state.turn_type == 'Attack':
        selected_action = decide_attack(state, actions)

    if state.turn_type == 'Place' or state.turn_type == 'PrePlace':
        singleton_instance.HAS_GOTTEN_RISK_CARD = False  # reset when starting turn
        singleton_instance.CONTINENT_TAKE_OVER_MODE = False  # reset when starting turn
        selected_action = decide_place(state, actions)

    if state.turn_type == 'TurnInCards':
        # Turn in cards whenever possible
        for action in actions:
            if action.troops is not None:
                selected_action = action

    if state.turn_type == 'Occupy':
        selected_action = decide_occupy(state, actions)
        singleton_instance.HAS_GOTTEN_RISK_CARD = True # set to true when occupying

    if state.turn_type == 'Fortify':
        selected_action = decide_fortify(state, actions)



    # Return the chosen action
    return selected_action


def decide_presign(state: RiskState, actions, continents):
    # priority 1: if another player is about to take a continent, try to stop them;
    for action in actions:
        # Only do this if there are 3 or fewer players playing the game
        if singleton_instance.PLAYERS_LEFT <= 3:
            # if you are taking the continent, then take it.
            for key in continents:
                owner_map = {}
                for territory in continents[key]:
                    if state.owners[state.board.territory_to_id[territory]] is None:
                        continue
                    elif state.owners[state.board.territory_to_id[territory]] not in owner_map:
                        owner_map[state.owners[state.board.territory_to_id[territory]]] = 1
                    else:
                        owner_map[state.owners[state.board.territory_to_id[territory]]] += 1
                for owner in owner_map:
                    if owner_map[owner] == len(continents[key]) - 1:
                        # This will make you take the continent. It could be your continent or someone else's.
                        if action.to_territory in continents[key]:
                            return action

    # Reverse the list of actions because most other will play at the beginning of the list.
    # This may help me stay separate from the other AIs.
    actions.reverse()

    best_action = actions[0]
    best_value = 0
    for action in actions:
        value = 0
        # priority 2: if territory is in South America, add 9
        if action.to_territory in continents['South America']:
            value += 4
        # priority 3: if territory is in North America, add 8
        elif action.to_territory in continents['North America']:
            value += 3
        # priority 4: if territory is in Australia, add 7
        elif action.to_territory in continents['Australia']:
            value += 2
        # priority 5: if territory is in Africa, add 6
        elif action.to_territory in continents['Africa']:
            value += 1

        # priority 6: stay away from popular continents
        to_territory = get_territory_from_name(state, action.to_territory)
        continent = get_continent(state, to_territory.id)
        # We want to avoid continents that are already owned by someone since their ai is likely to want to
        # take over that continent and we will lose more armies. Instead, we want to take over continents that
        # are not popular.
        for territory_id in continent.territories:
            if state.owners[territory_id] is not None:
                if state.owners[territory_id] != state.current_player:
                    # an enemy owns this territory
                    value -= 1
                else:
                    # we own this territory
                    value += 2

        if value > best_value:
            best_value = value
            best_action = action

    return best_action


def decide_place(state: RiskState, actions):
    continents = state.board.continents

    # priority 1: are the continents we own safe?
    for key in continents:
        # If we own the continent
        if get_ownership_percentage_of_continent(state, continents[key]) == 1:
            # get the border territories
            border_territories = get_frontier_territories(state, continents[key])
            territory_most_in_danger = None
            territory_most_in_danger_army_difference = 1000
            for territory in border_territories:
                enemies_nearby = 0
                for neighbor_id in territory.neighbors:
                    if state.owners[neighbor_id] != state.current_player:
                        # There is a conflict on the border of this continent
                        # We may need to place troops here
                        enemies_nearby += state.armies[neighbor_id]
                if enemies_nearby > state.armies[territory.id] - 4:
                    # This territory is in danger
                    army_difference = state.armies[territory.id] - enemies_nearby
                    if army_difference < territory_most_in_danger_army_difference:
                        territory_most_in_danger = territory

            # We need to place troops here
            if territory_most_in_danger is not None:
                for action in actions:
                    if action.to_territory == territory_most_in_danger.name:
                        return action

    # priority 2: which continent is the easiest take over?
    continents_available_to_take_over = {}
    for key in continents:
        # Make sure that we don't already own this continent
        if get_ownership_percentage_of_continent(state, continents[key]) != 1:
            army_difference = get_army_difference_in_continent(state, continents[key])
            territory_difference = get_territory_difference_in_continent(state, continents[key])
            difficulty = army_difference + territory_difference

            continents_available_to_take_over[key] = difficulty

    if 'Asia' in continents_available_to_take_over:
        continents_available_to_take_over['Asia'] -= 7  # we don't want to take over asia unless we have to
    if 'Europe' in continents_available_to_take_over:
        continents_available_to_take_over['Europe'] -= 5  # we don't want to take over europe unless we have to
    if 'Africa' in continents_available_to_take_over:
        continents_available_to_take_over['Africa'] -= 2  # africa is hard to defend
    if 'North America' in continents_available_to_take_over:
        continents_available_to_take_over['North America'] -= 1  # north america is big, but not too bad

    # get the easiest continent to take over
    easiest_continent = None
    easiest_continent_difficulty = -1000

    for key in continents_available_to_take_over:
        if continents_available_to_take_over[key] > easiest_continent_difficulty:
            easiest_continent = key
            easiest_continent_difficulty = continents_available_to_take_over[key]


    starting_point, path = get_path_to_take_over_continent(state, continents[easiest_continent])

    if len(path) > 0:
        best_territory_to_place = starting_point
        for action in actions:
            if action.to_territory == best_territory_to_place.name:
                return action

    # priority 2: which frontier is most at risk?
    most_at_risk_frontier_territory = None
    most_at_risk_frontier_territory_army_difference = 1000

    for action in actions:
        if action.to_territory is not None:
            to_territory = get_territory_from_name(state, action.to_territory)
            for neighbor_id in to_territory.neighbors:
                if state.owners[neighbor_id] != state.current_player:
                    # There is a conflict on the border of this continent
                    # We may need to place troops here
                    army_difference = state.armies[to_territory.id] - state.armies[neighbor_id]
                    if army_difference < most_at_risk_frontier_territory_army_difference:
                        most_at_risk_frontier_territory = to_territory
                        most_at_risk_frontier_territory_army_difference = army_difference

    if most_at_risk_frontier_territory is not None:
        for action in actions:
            if action.to_territory == most_at_risk_frontier_territory.name:
                return action

    return actions[0]


def decide_attack(state: RiskState, actions):
    if len(actions) == 1:
        return actions[0]

    continents = state.board.continents
    singleton_instance.CONTINENT_TAKE_OVER_MODE = True
    # priority 1: is there a continent that we can take over?
    for key in continents:
        troops_required = get_number_of_troops_required_to_take_over_continent(state, continents[key])
        army_difference = get_army_difference_in_continent(state, continents[key])

        starting_territory, best_path = get_path_to_take_over_continent(state, continents[key])
        if len(best_path) >= 1 and army_difference > troops_required:
            # if there are troops at best path, use them
            if state.armies[starting_territory.id] > 1:
                for action in actions:
                    if action.to_territory is not None and action.from_territory is not None:
                        if action.from_territory == starting_territory.name:
                            if action.to_territory == best_path[0].name:
                                return action
            else:
                # attempt to attack randomly in continent
                for action in actions:
                    if action.to_territory is not None and action.from_territory is not None:
                        if state.board.territory_to_id[action.to_territory] in continents[key].territories:
                            return action

    singleton_instance.CONTINENT_TAKE_OVER_MODE = False
    # priority 2: is there a continent border territory that we can take over?
    for action in actions:
        if action.to_territory is not None and action.from_territory is not None:
            to_territory = get_territory_from_name(state, action.to_territory)
            from_territory = get_territory_from_name(state, action.from_territory)
            if get_continent(state, to_territory.id).name != get_continent(state, from_territory.id).name:
                army_difference = state.armies[from_territory.id] - state.armies[to_territory.id]
                if army_difference > 2:
                    return action

    # priority 3: get a risk card if we don't already have one
    if not singleton_instance.has_gotten_risk_card():
        easiest_attack = None
        easiest_attack_army_difference = -1000
        for action in actions:
            if action.to_territory is not None and action.from_territory is not None:
                # find easiest territory to attack
                to_territory = get_territory_from_name(state, action.to_territory)
                from_territory = get_territory_from_name(state, action.from_territory)
                army_difference = state.armies[from_territory.id] - state.armies[to_territory.id]
                if army_difference > easiest_attack_army_difference:
                    easiest_attack = action
                    easiest_attack_army_difference = army_difference
        return easiest_attack

    if len(actions) > 1:
        return actions[-1] # pass turn action
    else:
        return actions[0]

def decide_occupy(state: RiskState, actions):
    # all occupy actions have the same from_territory and to_territory
    from_territory = get_territory_from_name(state, actions[0].from_territory)
    to_territory = get_territory_from_name(state, actions[0].to_territory)

    # Get the maximum number of troops we can move
    max_troops = 0
    max_action = actions[0]
    min_troops = 100000
    min_action = actions[0]
    for action in actions:
        if action.troops > max_troops:
            max_troops = action.troops
            max_action = action
        if action.troops < min_troops:
            min_troops = action.troops
            min_action = action


    if singleton_instance.CONTINENT_TAKE_OVER_MODE:
        return max_action
    else:
        for neighbor_id in from_territory.neighbors:
            if state.owners[neighbor_id] != state.current_player:
                return min_action
        return max_action

def decide_fortify(state: RiskState, actions):
    # find the territory with the most troops
    max_troops = 0

    if len(actions) == 1:
        return actions[0]

    max_action = actions[-1]
    for action in actions:
        if action.troops is not None:
            if action.troops > max_troops:
                # check if the territory is a frontier
                from_territory = get_territory_from_name(state, action.from_territory)
                is_frontier = False
                for neighbor_id in from_territory.neighbors:
                    if state.owners[neighbor_id] != state.current_player:
                        # is a frontier
                        is_frontier = True
                if not is_frontier:
                    max_troops = action.troops
                    max_action = action

    if max_action.from_territory is not None:
        from_territory = get_territory_from_name(state, max_action.from_territory)
        currently_considered_actions = []
        for action in actions:
            if action.from_territory is not None:
                if action.from_territory == from_territory.name:
                    currently_considered_actions.append(action)

        for action in currently_considered_actions:
            to_territory = get_territory_from_name(state, action.to_territory)
            is_frontier = False
            for neighbor_id in to_territory.neighbors:
                if state.owners[neighbor_id] != state.current_player:
                    # is a frontier
                    is_frontier = True
            if is_frontier:
                # only move all troops
                if action.troops == max_troops:
                    return action

        # we need to find the path to the nearest border territory
        path = get_path_to_border(state, from_territory)
        best_to_territory = None
        if len(path) >= 1:
            best_to_territory = path[0]

        if best_to_territory is not None:
            for action in currently_considered_actions:
                if action.to_territory == best_to_territory.name:
                    return action

        return max_action # just to do something

    else:
        for action in actions:
            # don't fortify
            if action.from_territory is None:
                return action
        return actions[0]

"""
Given a RiskTerritory id, returns the RiskContinent that it belongs to
"""
def get_continent(state, territory_id):
    for continent_name in state.board.continents:
        continent = state.board.continents[continent_name]
        if territory_id in continent.territories:
            return continent


"""
Takes in a RiskState and a RiskContinent and returns the difference in armies between the current player and the other
players in that continent.
"""
def get_army_difference_in_continent(state, continent):
    army_difference = 0
    for territory_id in continent.territories:
        if state.owners[territory_id] == state.current_player:
            army_difference += state.armies[territory_id]
        if state.owners[territory_id] != state.current_player:
            army_difference -= state.armies[territory_id]
    return army_difference


"""
Takes in a RiskState and a RiskContinent and returns the difference in territories between the current 
player and the other players in that continent.
"""
def get_territory_difference_in_continent(state, continent):
    territory_difference = 0
    for territory_id in continent.territories:
        if state.owners[territory_id] == state.current_player:
            territory_difference += 1
        if state.owners[territory_id] != state.current_player:
            territory_difference -= 1
    return territory_difference

"""
Returns the path to get to the border from inside your territory
"""
def get_path_to_border(state: RiskState, territory, max_depth=7):
    return path_to_border_helper(state, territory, set(), max_depth)

"""
Helper function for get_path_to_border
"""
def path_to_border_helper(state: RiskState, territory: RiskTerritory, visited, max_depth):
    visited.add(territory.id)

    if state.owners[territory.id] != state.current_player or max_depth == 0:
        return [territory]  # Return the current territory if it's a border territory or reached max depth

    shortest_path = None
    shortest_length = float('inf')

    for neighbor_id in territory.neighbors:
        if neighbor_id not in visited:
            neighbor = state.board.territories[neighbor_id]
            path = path_to_border_helper(state, neighbor, visited.copy(), max_depth - 1)
            if path and len(path) < shortest_length:
                shortest_path = path
                shortest_length = len(path)

    if shortest_path is not None:
        shortest_path.insert(0, territory)

    return shortest_path


"""
Returns the number of troops required to get to a continent
"""
def find_nearest_owned_territory(state: RiskState, territory_id, distance, explored):
    territory = state.board.territories[territory_id]

    if state.owners[territory_id] == state.current_player:
        # Our territory found, return the troops required to reach here
        return distance
    else:
        # Find adjacent territories
        adjacent_territory_ids = territory.neighbors
        min_troops = float('inf')  # Initialize with a large value

        for adjacent_id in adjacent_territory_ids:
            if adjacent_id not in explored:
                # Calculate distance between territories
                armies_on_territory = state.armies[territory_id]
                explored.add(adjacent_id)  # Mark territory as explored
                troops_required = find_nearest_owned_territory(state, adjacent_id, distance + armies_on_territory + 1, explored)

                # Update minimum troops required
                min_troops = min(min_troops, troops_required)

        return min_troops

def get_number_of_troops_required_to_take_over_continent(state, continent: RiskContinent):
    troops = 0
    we_have_army_in_continent = False


    for territory_id in continent.territories:
        if state.owners[territory_id] == state.current_player:
            we_have_army_in_continent = True
        else:
            troops += state.armies[territory_id]

    if we_have_army_in_continent:
        return troops
    else:
        territories_explored = get_border_territories_of_continent(state, continent)
        min_troops_required = 10000
        explored_territories = set()

        for territory in territories_explored:
            distance = 0
            troops_required = find_nearest_owned_territory(state, territory.id, distance, explored_territories) + troops
            min_troops_required = min(min_troops_required, troops_required)


        if min_troops_required > 1000:
            return -1  # No territories found, return a default value or handle accordingly
        else:
            return min_troops_required

"""
Takes in a RiskState and a RiskContinent and returns the percentage of territories owned by the current player.
"""
def get_ownership_percentage_of_continent(state, continent):
    territory_difference = 0
    for territory_id in continent.territories:
        if state.owners[territory_id] == state.current_player:
            territory_difference += 1
    return territory_difference / len(continent.territories)

"""
Take in a RiskState and a RiskContinent and returns a list of RiskTerritory objects that form the border of 
a continent
"""
def get_border_territories_of_continent(state, continent: RiskContinent):
    border_territories: [RiskTerritory] = []
    for territory_id in continent.territories:
        territory = state.board.territories[territory_id]

        for neighbor_id in territory.neighbors:
            if neighbor_id not in continent.territories:
                border_territories.append(territory)

    return border_territories

"""
Take in a RiskState and a RiskContinent and returns a list of RiskTerritory objects that are your borders
"""
def get_frontier_territories(state, continent):
    border_territories = []
    for territory_id in continent.territories:
        territory = state.board.territories[territory_id]
        for neighbor_id in territory.neighbors:
            if state.owners[neighbor_id] != state.current_player:
                border_territories.append(territory)
                break
    return border_territories


"""
Take in a RiskState and a RiskContinent and gets the path to take over the continent

The starting point is a territory object owned by the current player, and the path is a list of territory objects
"""
def get_path_to_take_over_continent(state: RiskState, continent: RiskContinent):
    starting_points = []
    for territory_id in continent.territories:
        territory = state.board.territories[territory_id]
        if state.owners[territory_id] == state.current_player:
            is_frontier = False
            for neighbor_id in territory.neighbors:
                if state.owners[neighbor_id] != state.current_player:
                    # territory is a frontier
                    is_frontier = True
                    break
            if is_frontier:
                starting_points.append(territory.name)

    # find territories that border that continent
    for territory in state.board.territories:
        if territory.id not in continent.territories:
            if state.owners[territory.id] == state.current_player:
                for neighbor_id in territory.neighbors:
                    if neighbor_id in continent.territories:
                        if state.owners[neighbor_id] != state.current_player:
                            starting_points.append(territory.name)


    max_length = 0
    max_starting_point_territory = None
    troops_already_on_territory = 0
    max_path = []
    for starting_point_string in starting_points:
        path = []
        starting_point_territory = state.board.territories[state.board.territory_to_id[starting_point_string]]
        best_path_from_starting_point = get_path_to_take_over_continent_helper(state, continent,
                                                                               starting_point_territory, path)

        if len(best_path_from_starting_point) > max_length:
            max_length = len(best_path_from_starting_point)
            max_starting_point_territory = starting_point_territory
            max_path = best_path_from_starting_point
            troops_already_on_territory = state.armies[max_starting_point_territory.id]

        # check if another path of the same length is better
        if len(best_path_from_starting_point) == max_length and len(best_path_from_starting_point) > 0:
            best_path_ends_in_frontier = False
            if state.armies[starting_point_territory.id] > troops_already_on_territory:

                max_starting_point_territory = starting_point_territory
                max_path = best_path_from_starting_point
                troops_already_on_territory = state.armies[max_starting_point_territory.id]

            if state.armies[starting_point_territory.id] == troops_already_on_territory:
                last_in_best_path = max_path[0]
                if len(max_path) > 1:
                    last_in_best_path = max_path[-1]
                for best_path_end_neighbor_id in last_in_best_path.neighbors:
                    if best_path_end_neighbor_id not in continent.territories:
                        if state.owners[best_path_end_neighbor_id] != state.current_player:
                            best_path_ends_in_frontier = True

                if not best_path_ends_in_frontier:
                    last_in_best_path_from_starting_point = best_path_from_starting_point[0]
                    if len(best_path_from_starting_point) > 1:
                        last_in_best_path_from_starting_point = best_path_from_starting_point[-1]
                    # check if the last territory is a frontier territory
                    for path_end_neighbor_id in last_in_best_path_from_starting_point.neighbors:
                        # see if the neighbor is out of the continent
                        if path_end_neighbor_id not in continent.territories:
                            if state.owners[path_end_neighbor_id] != state.current_player:
                                # neighbor is a frontier
                                max_starting_point_territory = state.board.territories[
                                    state.board.territory_to_id[starting_point_string]]
                                max_path = best_path_from_starting_point
                                break

    return max_starting_point_territory, max_path


def get_path_to_take_over_continent_helper(state, continent, front_line, path_so_far):
    best_path = copy.deepcopy(path_so_far)
    for neighbor_id in state.board.territories[front_line.id].neighbors:
        neighbor = state.board.territories[neighbor_id]

        if neighbor_id in continent.territories and neighbor not in path_so_far:
            if state.owners[neighbor.id] != state.current_player:
                # neighbor is a frontier
                path_so_far.append(neighbor)
                if len(path_so_far) == len(continent.territories):
                    return path_so_far
                else:
                    temp_path = get_path_to_take_over_continent_helper(state, continent, neighbor, path_so_far)
                    if len(temp_path) > len(best_path):
                        best_path = temp_path
                    if len(best_path) == len(best_path):
                        # check if the last territory is a border territory
                        for path_end_neighbor_id in best_path[-1].neighbors:
                            if state.owners[path_end_neighbor_id] != state.current_player:
                                # neighbor is a frontier
                                best_path = temp_path

                    if len(best_path) == len(continent.territories):
                        return best_path

    return best_path


def get_territory_from_name(state, territory_name):
    return state.board.territories[state.board.territory_to_id[territory_name]]


# Code below this is the interface with Risk.pyw GUI version
# DO NOT MODIFY

def aiWrapper(function_name, occupying=None):
    game_board = createRiskBoard()
    game_state = createRiskState(game_board, function_name, occupying)
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
