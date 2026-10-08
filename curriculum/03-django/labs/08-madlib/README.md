


# MadLib


## Views

- index
  - render the index template
  - show a list of madlib titles, clicking one takes you to the detail page
- detail
  - show input fields for the words for a given madlib
- result
  - receive the form submission
  - show the result of the madlib

## Models

- MadLib
  - title (CharField)
  - template (TextField)
- MadLibWord
  - madlib (ForeignKey)
  - variable name (CharField)
  - part of speech (CharField)

## Check your work

Try the lab on your own first, then compare your approach:

- [Reference solution](solution/)
- Student solutions: [student 1](student-solutions/student-1/). These were written by learners taking the course and are shown as they wrote them, so expect a few bugs. Spotting them is good practice.
