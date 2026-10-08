# Make Change

Let's convert a dollar amount into a number of coins. The input will be the total amount, the output will be the number of quarters, dimes, nickles, and pennies. Always break the total into the highest coin value first, resulting in the fewest amount of coins. First convert the dollar amount (1.36) into the total number of pennies (136), then use floor division `//`, which throws away the remainder. `10/3` is `3.333333`, `10//3` is `3`. 

```
Enter a dollar amount: 1.36
5 quarters, 1 dime, and 1 penny
```
```
Enter a dollar amount: 0.67
2 quarters, 1 dime, 1 nickel, 2 pennies
```

## Version 2 (optional)

Instead of hard-coding the coins, store them in a list of tuples. This way you can make custom coins.

```python
coins = [
    ('half-dollar', 50),
    ('quarter', 25),
    ('dime', 10),
    ('nickel', 5),
    ('penny', 1)
]
```

## Check your work

Try the lab on your own first, then compare your approach:

- [Reference solution](solution/lab04_make_change.py)
- Student solutions: [student 1](student-solutions/student-1/), [student 2](student-solutions/student-2/). These were written by learners taking the course and are shown as they wrote them, so expect a few bugs. Spotting them is good practice.
