# Lab 13: Number to Phrase

Convert a given number into its English representation. For example: 67 becomes 'sixty-seven'. Handle numbers from 0-99.

Hint: you can use modulus to extract the ones and tens digit.

```python
x = 67
tens_digit = x//10
ones_digit = x%10
```
Hint 2: use the digit as an index for a list of strings or the key in a dictionary.

## Version 2

Handle numbers from 100-999.

## Version 3 (optional)

Convert a number to roman numerals.

## Version 4 (optional)

Convert a time given in hours and minutes to a phrase.

## Check your work

Try the lab on your own first, then compare your approach:

- [Reference solution](solution/mob05_number_to_phrase.py)
- Student solutions: [student 1](student-solutions/student-1/), [student 2](student-solutions/student-2/). These were written by learners taking the course and are shown as they wrote them, so expect a few bugs. Spotting them is good practice.
