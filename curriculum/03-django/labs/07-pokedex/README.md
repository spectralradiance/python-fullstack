

# Lab 5: Pokedex

Let's build a searchable pokedex! First we'll load the data from a `json` file into our own database. Then we'll list those pokemon in the page and add search and pagination.

## Part 1

Create an app `pokedex` and add two models to store our pokemon, `Pokemon`.

`Pokemon` should have the following fields:
- `number` (IntegerField)
- `name` (CharField)
- `height` (FloatField)
- `weight` (FloatField)
- `image_front` (CharField)
- `image_back` (CharField)
- `types` (CharField, just list out types separated by commas)

## Part 2

Write a [custom management command](../../docs/02-django-overview.md#custom-management-commands) `load_pokemon.py` to load the data from [pokemon.json](./pokemon.json) into your database. You can do this by saving the file next to your `.py` file and using [opening the file](../../../01-python/docs/20-file-io.md). In the first line of your management command, you may want to delete all the records in the table so each time you run it you start with a clean slate. To verify that the data was loaded, open your admin panel and check that the pokemon are there.

## Part 3

Write a `view`, `route` and `template` to show a list of pokemon on the front page. You can either show all the information as a table, or show only their name and icon and link to a detail page with all their information. Use `<img src="...">` to display their front and back image.

## Part 3

Use the django [paginator](https://docs.djangoproject.com/en/3.0/topics/pagination/) to only show 20 pokemon at a time, allow the user to switch between pages.

## Part 4

Add a form at the top of your list of pokemon with a text input to search for pokemon. Only show pokemon that match that text input ([search](https://docs.djangoproject.com/en/3.0/topics/db/search/), [icontains](https://docs.djangoproject.com/en/3.0/ref/models/querysets/#std:fieldlookup-icontains), [stack overflow answer](https://stackoverflow.com/questions/38478635/search-using-multiple-fields-django-building-the-object-list)).

## Part 5 (optional)

Check out the [script](./pokedex.py) that creates the json file, you can use it to load even more pokemon into your database!

## Check your work

Try the lab on your own first, then compare your approach:

- Student solutions: [student 1](student-solutions/student-1/), [student 2](student-solutions/student-2/). These were written by learners taking the course and are shown as they wrote them, so expect a few bugs. Spotting them is good practice.
