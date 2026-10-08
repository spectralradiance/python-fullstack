# Blackjack Advice


Let's write a python program to give basic blackjack playing advice during a game by asking the player for cards. First, ask the user for three playing cards (A, 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, or K). Then, figure out the point value of each card individually. Number cards are worth their number, all face cards are worth 10. At this point, assume aces are worth 1. Use the following rules to determine the advice:

* Less than 17, advise to "Hit"
* Greater than or equal to 17, but less than 21, advise to "Stay"
* Exactly 21, advise "Blackjack!"
* Over 21, advise "Already Busted"

Print out the current total point value and the advice.

```
What's your first card? Q
What's your second card? 2
What's your third card? 3
15 Hit

What's your first card? K
What's your second card? 5
What's your third card? 5
20 Stay

What's your first card? Q
What's your second card? J
What's your third card? A
21 Blackjack!
```

## Version 2 (optional)

Aces can be worth 11 if they won't put the total point value of both cards over 21. Remember that you can have multiple aces in a hand. Try generating a list of all possible hand values by doubling the number of values in the output whenever you encounter an ace. For one half, add 1, for the other, add 11. This ensures if you have multiple aces that you account for the full range of possible values.

## Check your work

Try the lab on your own first, then compare your approach:

- [Reference solution](solution/lab09_blackjack_advice.py)
- Student solutions: [student 1](student-solutions/student-1/), [student 2](student-solutions/student-2/). These were written by learners taking the course and are shown as they wrote them, so expect a few bugs. Spotting them is good practice.
