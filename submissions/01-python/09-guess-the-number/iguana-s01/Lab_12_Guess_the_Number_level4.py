#Guess_the_Number level 4
import random

# This can be done by  maintaining a variable containing the last guess outside the loop, then comparing
# the last guess to the current guess, and check if it's closer. Hint: you're interested in comparing the two absolute differences:
# abs(current_guess-target) and abs(last_guess-target).
x = random.randint(1, 20)

count = 0
last_guess = None #this could really be any irrelavent value. We just need a placeholder outside the loop. The value will be updated and become relevant at the end of the first pass of the loop
#before Student helped me I was trying to intially account for this within the loop. Was getting stuck in circles.
while True:
    current_guess = input("Guess a number between 1 and 20.")  # initial input variable. This is the way to do it, inside the while loop. Previously I have been putting a second input in side the loop.
                                                                #but there is no need to ask for input a second time if it is just another guess.
    current_guess = int(current_guess)
    count += 1
    if current_guess == x:                # I had the conditions reversed, with this affirmative one coming last. No need. This can go first with a 'break' set
        print(f'Good guess. {x} is correct. That took you {count} attempts!')
        break

    if last_guess is not None:                         # this was the new trick I learned on this one (along with setting conditionals in the right order.
        last_proximity = abs(last_guess - x)            #Because last_guess is originally set to None before the loop ever starts, this step is skipped the first time through
        new_proximity = abs(current_guess - x)
        if new_proximity < last_proximity:
            print('You are getting warmer.')            #none of this is done the first time through the loop because last_guess still is set to None
        elif new_proximity > last_proximity:
            print('Uh oh, you are getting colder.')
        else:
            print('You\'re the same distance')
    last_guess = current_guess               #at the end of the first time through the loop, last_guess is changed to current_guess. And that is all that happens the first time through.
#The fist time through, the value of last_guess is updated from None to the value of current_guess (the fist guess), and that is all that happens. Then the loop is started again, a second guess is acquired
# and now we have two guesses to compare. And because the value of last_guess is no longer None, this section of the code is activated and the comparison is made.

# if user_input > x:  # just an if within the broader if statement
#     user_input = int(input('Nope. That was too high. Try again.'))  # convert to int in same input
# elif user_input < x:
#     user_input = int(input('Nope. That was too low. Try again.'))
#
