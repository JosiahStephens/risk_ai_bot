import random
from risktools import *
# For interacting with interactive GUI
from gui.aihelper import *
from gui.turbohelper import *
import copy


### ATILLA AI ####
# 
#

def test():
    return True
def getAction(state, time_left=None):
    """Main AI function.  It should return a valid AI action for this state."""

    # Get the possible actions in this state
    actions = getAllowedActions(state)

    # Select a Random Action (to use for unspecified turn types)
    selected_action = random.choice(actions)

    print(f"State.turn_type: {state.turn_type}")

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

    if state.turn_type == 'Place' or state.turn_type == 'Fortify' or state.turn_type == 'PrePlace':
        selected_action = decide_place(state, actions, continents_name_to_territory_name)

    # Return the chosen action
    return selected_action


def decide_presign(state: RiskState, actions, continents):
    best_action = actions[0]
    best_value = 0
    for action in actions:
        print(f"Territory: {action.to_territory}")
        # priority 1: if territory is in South America, assign it

        if action.to_territory in continents['South America']:
            value = 9
            if value > best_value:
                best_value = value
                best_action = action
        # priority 2: if territory is in North America, assign it
        elif action.to_territory in continents['North America']:
            value = 8
            if value > best_value:
                best_value = value
                best_action = action
        # priority 3: if territory is in Australia, assign it
        elif action.to_territory in continents['Australia']:
            value = 7
            if value > best_value:
                best_value = value
                best_action = action
        elif action.to_territory in continents['Africa']:
            value = 6
            if value > best_value:
                best_value = value
                best_action = action
        # priority 4: if another player has a majority of a continent, and this territory is in that continent,
        # assign it

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
                if owner_map[owner] > len(continents[key]) / 2 and owner != state.current_player:
                    if action.to_territory in continents[key]:
                        value = 10
                        if value > best_value:
                            best_value = value
                            best_action = action
        print(f"Best action: {best_action.to_territory} with value {best_value}")
    return best_action


def decide_place(state: RiskState, actions, continents):
    # priority 1: are the continents we own safe?
    for key in continents:
        # If we own the continent
        if get_ownership_percentage_of_continent(state, continents[key]) == 1:
            # get the border territories
            border_territories = get_frontier_territories(state, continents[key])
            print(f"Border territories: {border_territories}")
            for territory_name in border_territories:
                territory = state.board.territories[state.board.territory_to_id[territory_name]]
                enemies_nearby = 0
                for neighbor_id in territory.neighbors:
                    if state.owners[neighbor_id] != state.current_player:
                        # There is a conflict on the border of this continent
                        # We may need to place troops here
                        enemies_nearby += state.armies[neighbor_id]
                print(f"Enemies near {territory_name}: {enemies_nearby}")
                if enemies_nearby > state.armies[territory.id] - 4:
                    # We need to place troops here
                    for action in actions:
                        if action.to_territory == territory_name:
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
    print(f"The easiest continent to take over would be: {easiest_continent}")

    best_territory_to_place = get_path_to_take_over_continent(state, continents[easiest_continent])
    if best_territory_to_place:
        print(f"Best territory to place in {easiest_continent}: {best_territory_to_place.name}")
        for action in actions:
            if action.to_territory == best_territory_to_place.name:
                print(f"I'm placing on {action.to_territory}.")
                return action

    # priority 2: is there a continent border territory that we can take over?
    # print(get_border_territories(state, continents))

    print("I am so confused, so I just placed wherever.")
    return actions[0]


def decide_attack(state: RiskState, actions):
    if len(actions) == 1:
        return actions[0]

    continents = state.board.continents

    # priority 1: is there a continent that we can take over?
    for key in continents:
        troops_required = get_number_of_troops_required_to_take_over_continent(state, continents[key])
        print(f"Continent: {key} will require {troops_required} troops to take over.")

        # army_difference = get_army_difference_in_continent(state, continents[key])
        # territory_difference = get_territory_difference_in_continent(state, continents[key])


        # if army_difference > 5:
        #     # we can take over this continent
        #     for territory in continents[key]:
        #         if state.owners[state.board.territory_to_id[territory]] != state.current_player:
        #             # we can attack this territory
        #             for action in actions:
        #                 if action.to_territory == territory:
        #                     return action

    # priority 2: is there a continent border territory that we can take over?
    for action in actions:
        if get_continent(state, action.to_territory) != get_continent(state, action.from_territory):
            army_difference = state.armies[state.board.territory_to_id[action.to_territory]] - \
                              state.armies[state.board.territory_to_id[action.from_territory]]
            if army_difference > 2:
                return action

    return actions[0]


"""
Given a RiskTerritory object, returns the RiskContinent that it belongs to
"""
def get_continent(state, territory_id):
    for continent_name in state.board.continents:
        continent = state.board.continents[continent_name]
        if territory_id in continent.territories:
            return continent


def get_army_difference_in_continent(state, continent):
    army_difference = 0
    for territory in continent:
        if state.owners[state.board.territory_to_id[territory]] == state.current_player:
            army_difference += state.armies[state.board.territory_to_id[territory]]
        if state.owners[state.board.territory_to_id[territory]] != state.current_player:
            army_difference -= state.armies[state.board.territory_to_id[territory]]
    return army_difference


def get_territory_difference_in_continent(state, continent):
    territory_difference = 0
    for territory in continent:
        if state.owners[state.board.territory_to_id[territory]] == state.current_player:
            territory_difference += 1
        if state.owners[state.board.territory_to_id[territory]] != state.current_player:
            territory_difference -= 1
    return territory_difference

# Assuming you have a function get_border_territories_of_continent defined
# and a function calculate_distance_between_territories defined

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

    print(continent)

    for territory_id in continent.territories:
        if state.owners[territory_id] == state.current_player:
            we_have_army_in_continent = True
        else:
            troops += state.armies[territory_id]

    if we_have_army_in_continent:
        return troops
    else:
        print(f"We don't have any army in {continent.name}")
        territories_explored = get_border_territories_of_continent(state, continent)
        min_troops_required = 10000
        explored_territories = set()

        for territory in territories_explored:
            distance = 0
            troops_required = find_nearest_owned_territory(state, territory.id, distance, explored_territories) + troops
            min_troops_required = min(min_troops_required, troops_required)

        print("It will take", min_troops_required, "troops to take over", continent.name)

        if min_troops_required > 1000:
            return -1  # No territories found, return a default value or handle accordingly
        else:
            return min_troops_required

def get_ownership_percentage_of_continent(state, continent):
    territory_difference = 0
    for territory in continent:
        if state.owners[state.board.territory_to_id[territory]] == state.current_player:
            territory_difference += 1
    return territory_difference / len(continent)

"""
Returns a list of RiskTerritory objects that border a continent
"""
def get_border_territories_of_continent(state, continent: RiskContinent):
    border_territories: [RiskTerritory] = []
    for territory_id in continent.territories:
        territory = state.board.territories[territory_id]

        for neighbor_id in territory.neighbors:
            if neighbor_id not in continent.territories:
                border_territories.append(territory)

    return border_territories

def get_frontier_territories(state, continent):
    border_territories = []
    for territory in continent:
        for neighbor_id in state.board.territories[state.board.territory_to_id[territory]].neighbors:
            if state.owners[neighbor_id] != state.current_player:
                border_territories.append(territory)
                break
    return border_territories


def get_path_to_take_over_continent(state, continent):
    starting_points = []
    for territory_name in continent:
        if state.owners[state.board.territory_to_id[territory_name]] == state.current_player:
            is_frontier = False
            for neighbor_id in state.board.territories[state.board.territory_to_id[territory_name]].neighbors:
                if state.owners[neighbor_id] != state.current_player:
                    # territory is a frontier
                    is_frontier = True
                    break
            if is_frontier:
                starting_points.append(territory_name)

    # find territories that border that continent
    for territory in state.board.territories:
        if territory.name not in continent:
            if state.owners[territory.id] == state.current_player:
                for neighbor_id in territory.neighbors:
                    if state.board.territories[neighbor_id] in continent:
                        if territory not in starting_points:
                            starting_points.append(territory.name)

    print(f"Starting points: {starting_points}")

    max_length = 0
    max_starting_point_territory = None
    best_path = []
    for starting_point_string in starting_points:
        path = []
        starting_point_territory = state.board.territories[state.board.territory_to_id[starting_point_string]]
        best_path_from_starting_point = get_path_to_take_over_continent_helper(state, continent, starting_point_territory, path)
        if len(best_path_from_starting_point) > max_length:
            max_length = len(best_path_from_starting_point)
            max_starting_point_territory = state.board.territories[state.board.territory_to_id[starting_point_string]]
            best_path = best_path_from_starting_point

    if len(best_path) > 0:
        print(f"Best path: {max_starting_point_territory.name} -> ", end="")
        for index, territory in enumerate(best_path):
            if index == len(best_path) - 1:
                print(f"{territory.name}")
            else:
                print(f"{territory.name} -> ", end="")
    else:
        print("No path found.")

    return max_starting_point_territory


def get_path_to_take_over_continent_helper(state, continent, front_line, path_so_far):
    best_path = copy.deepcopy(path_so_far)
    for neighbor_id in state.board.territories[front_line.id].neighbors:
        neighbor = state.board.territories[neighbor_id]

        if neighbor.name in continent and neighbor not in path_so_far:
            if state.owners[neighbor.id] != state.current_player:
                # neighbor is a frontier
                path_so_far.append(neighbor)
                if len(path_so_far) == len(continent):
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

                    if len(best_path) == len(continent):
                        return best_path

    return best_path


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
