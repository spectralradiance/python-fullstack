#
import random

#  generic class for entities. inherit to child classes.
class Entity:
    def __init__(self, location_i, location_j, character):
        self.location_i = location_i
        self.location_j = location_j
        self.character = character


class Enemy(Entity):
    def __init__(self, location_i, location_j):
        super().__init__(location_i, location_j, '§')


class Player(Entity):
    def __init__(self, location_i, location_j):
        super().__init__(location_i, location_j, '☺')


class Board:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def random_location(self):
        return random.randint(0, self.width - 1), random.randint(0, self.height - 1)

    def print(self, entities):
        for i in range(self.height):
            for j in range(self.width):
                for k in range(len(entities)):
                    if entities[k].location_i == i and entities[k].location_j == j:
                        print(entities[k].character, end='')
                        break
                else:
                    print(' ', end='')
            print()

def victory():
    print('\n'
          '      ,:\      /:.\n'
          '    //  \_()_/     |\n'
          '    ||   |    |   ||\n'
          '    ||   |    |   ||\n'
          '    ||   |____|   ||\n'
          '     \\  / || \  // \n'
          '      `:/  ||  \;    \n'
          '           ||         \n'
          '           ||         \n'
          '           XX         \n'
          '           XX         \n'
          '           XX         \n'
          '           XX         \n'
          '           OO         \n'
          '           `''        \n')
    exit()

board = Board(10, 10)

pi, pj = board.random_location()
player = Player(pi, pj)

entities = [player]
enemies = []

for i in range(3):
    ei, ej = board.random_location()
    enemy = Enemy(ei, ej)
    entities.append(enemy)
    enemies.append(enemy)

while True:

    board.print(entities)

    command = input('what is your command? ')  # get the command from the user

    if command == 'done':
        break  # exit the game
    elif command in ['l', 'left', 'w', 'west']:
        player.location_j -= 1  # move left
    elif command in ['r', 'right', 'e', 'east']:
        player.location_j += 1  # move right
    elif command in ['u', 'up', 'n', 'north']:
        player.location_i -= 1  # move up
    elif command in ['d', 'down', 's', 'south']:
        player.location_i += 1  # move down

    for enemy in enemies:

        # randomly pick horizontal or vertical
        # randomly pick a new position to move to
        # check if that new position is still on the board
        # if it is, move them, if it's not, goto the start again

        while True:
            if random.randint(0, 1) == 0:
                new_i = enemy.location_i + random.randint(-1, 1)
                new_j = enemy.location_j + random.randint(-1, 1)
                if new_i >= 0 and new_i < board.height and new_j >= 0 and new_j < board.width:
                    enemy.location_i = new_i
                    enemy.location_j = new_j
                    break

        # if random.randint(0, 1) == 0:
        #     enemy.location_i += random.randint(-1, 1)
        # else:
        #     enemy.location_j += random.randint(-1, 1)


    for enemy in enemies:
        if enemy.location_i == player.location_i and enemy.location_j == player.location_j:
            print('you\'ve encountered an enemy!')
            action = input('what will you do? ')
            if action == 'attack':
                attack_results = ['hit', 'hit', 'hit', 'hit', 'ouch', 'ouch']

                hit_count = 0
                ouch_count = 0

                while hit_count < 3 and ouch_count < 3:
                    result = random.choice(attack_results)
                    if result == 'hit':
                        hit_count += 1
                        input('Nice hit! Attack again.')
                    elif result == 'ouch':
                        ouch_count += 1
                        input('Ouch. You ok? Attack again!')
                    if hit_count == 3:
                        print('you\'ve slain the enemy')
                        entities.remove(enemy)
                        enemies.remove(enemy)
                        break
                    elif ouch_count == 3:
                        print('you died. But it was glorious!')
                        exit()
                if len(enemies) == 0:
                    print('Conan, what is best in life?\n To crush your enemies, see them driven before you, and to hear the lamentations of their women!')
                    victory()



    # for enemy in enemies:
    #     if random.randint(0, 1) == 0:
    #         enemy.location_i += random.randint(-1, 1)
    #     else:
    #         enemy.location_j += random.randint(-1, 1)
    #idea: to display something if all enemies killed. conan quote.
    #1. check that all enemies are dead/gone.
