import random

def get_computer_choice():
    choices = ['rock', 'paper', 'scissors']
    c_choice = random.choice(choices)
    print("Hmm... I choose... " + c_choice + "!\n" )
    return c_choice

def get_player_choice():
    while True: 
        print('-' * 50)
        p_choice = input('Choose "rock", "paper", or "scissors": ')

        if p_choice == 'rock' or p_choice == 'paper' or p_choice == 'scissors':
            return p_choice
            break
        else:
            print('Not a valid choice. Try again')

def get_winner():
    player = get_player_choice()
    computer = get_computer_choice()
    win = False

    if player == computer:
        print('We tied! Lets go again.')
        get_winner()
    elif player == 'rock':
        if computer == 'paper':
            print('Beat ya. Too easy')
        else:
            print('You win. Lucky guess')
            win = True
    elif player == 'paper':
        if computer == 'scissors':
            print('Sucks to suck. Should have gone with rock.')
        else:
            print('I let you win. Try and do it twice')
            win = True
    else:
        if computer == 'rock':
            print('Rock strong like ox. You cannot beat it')
        else:
            print('Wow. How did you win? Scissors? Nobody picks that. You\'re bad kid.')
            win = True

    return win

# get_winner()

# while True:
#     cont = input("\n\nAgain? y/n\t")

#     if cont == "y":
#         get_winner() 
#     elif cont == "n":
#         break
#     else:
#         print("Not a valid response. Type 'y' or 'n' ")


