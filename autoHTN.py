import pyhop
import json

def check_enough(state, ID, item, num):
	if getattr(state,item)[ID] >= num: return []
	return False

def produce_enough(state, ID, item, num):
	return [('produce', ID, item), ('have_enough', ID, item, num)]

pyhop.declare_methods('have_enough', check_enough, produce_enough)

def produce(state, ID, item):
	return [('produce_{}'.format(item), ID)]

pyhop.declare_methods('produce', produce)

def make_method(name, rule):
    time_cost = rule.get("Time", 0)
    requires = rule.get("Requires", {})
    consumes = rule.get("Consumes", {})
    def method(state, ID):
        subtasks = []
        for item, qty in requires.items():
            subtasks.append(('have_enough', ID, item, qty))

        for item, qty in consumes.items():
            subtasks.append(('have_enough', ID, item, qty))

        subtasks.append(('op_' + name.replace(" ", "_"), ID))
        return subtasks
    method.time_cost = time_cost
    method.__name__ = "method_" + name.replace(" ", "_")
    return method

def declare_methods(data):
    recipes = data["Recipes"]
    methods_by_product = {}  
    for recipe_name, rule in recipes.items():
        produces = rule.get("Produces", {})
        method = make_method(recipe_name, rule)
        for item in produces:
            if item not in methods_by_product:
                methods_by_product[item] = []  
            methods_by_product[item].append(method)
    #register methods with pyhop
    for item, methods in methods_by_product.items():
        task_name = "produce_" + item
        pyhop.declare_methods(task_name, *methods)

def make_operator(rule):
    produces = rule.get("Produces", {})
    consumes = rule.get("Consumes", {})
    requires = rule.get("Requires", {})
    time_cost = rule.get("Time", 0)

    def operator(state, ID):
        if state.time[ID] < time_cost: 
            return False

        for item, qty in requires.items(): 
            if getattr(state, item)[ID] < qty:
                return False

        for item, qty in consumes.items():
            if getattr(state, item)[ID] < qty:
                return False

        for item, qty in consumes.items():
            getattr(state, item)[ID] -= qty

        for item, qty in produces.items():
            getattr(state, item)[ID] += qty

        state.time[ID] -= time_cost

        return state

    return operator


def declare_operators(data):
    recipes = data["Recipes"]
    operators = []
    for name in recipes:
        rule = recipes[name]
        op = make_operator(rule)
        op.__name__ = "op_" + name.replace(" ", "_")
        operators.append(op)
    pyhop.declare_operators(*operators)

def add_heuristic(data, ID):
	# prune search branch if heuristic() returns True
	# do not change parameters to heuristic(), but can add more heuristic functions with the same parameters: 
	# e.g. def heuristic2(...); pyhop.add_check(heuristic2)
	def heuristic(state, curr_task, tasks, plan, depth, calling_stack):
		if calling_stack.count(curr_task) > 2: #dont allow more than 2 of the same task in the call stack
			return True
		return False # if True, prune this branch

	pyhop.add_check(heuristic)

def define_ordering(data, ID):
	# if needed, use the function below to return a different ordering for the methods
	# note that this should always return the same methods, in a new order, and should not add/remove any new ones
	def reorder_methods(state, curr_task, tasks, plan, depth, calling_stack, methods):
		return sorted(methods, key=lambda m: getattr(m, 'time_cost', 0))
	
	pyhop.define_ordering(reorder_methods)

def set_up_state(data, ID):
	state = pyhop.State('state')
	setattr(state, 'time', {ID: data['Problem']['Time']})

	for item in data['Items']:
		setattr(state, item, {ID: 0})

	for item in data['Tools']:
		setattr(state, item, {ID: 0})

	for item, num in data['Problem']['Initial'].items():
		setattr(state, item, {ID: num})

	return state

def set_up_goals(data, ID):
	goals = []
	for item, num in data['Problem']['Goal'].items():
		goals.append(('have_enough', ID, item, num))

	return goals

if __name__ == '__main__':
	import sys
	rules_filename = 'crafting.json'
	if len(sys.argv) > 1:
		rules_filename = sys.argv[1]

	with open(rules_filename) as f:
		data = json.load(f)

	state = set_up_state(data, 'agent')
	goals = set_up_goals(data, 'agent')

	declare_operators(data)
	declare_methods(data)
	add_heuristic(data, 'agent')
	define_ordering(data, 'agent')

	# pyhop.print_operators()
	# pyhop.print_methods()

	# Hint: verbose output can take a long time even if the solution is correct; 
	# try verbose=1 if it is taking too long
	pyhop.pyhop(state, goals, verbose=1)
	#pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 20)], verbose=3)
	#pyhop.print_operators()
