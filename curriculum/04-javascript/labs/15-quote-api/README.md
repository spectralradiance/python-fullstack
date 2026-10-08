
# Lab 6: Random Quote

Before starting, check out the doc on [APIs and AJAX](../../docs/16-apis-ajax.md).

Use the [favqs.com](https://favqs.com/api/) api to show a random quote. Send a `GET` request to `https://favqs.com/api/qotd`, extract the relevant information, and display it on the page.

## Version 2

The API also supports browsing quotes. Add an `input type="text"` and a `search button`, then use the `filter` query parameter to get a bunch of quotes. Then you can show those quotes in a list. In order to get authorization for this request, we need to add a request header with the authorization token.

```javascript
let headers = {'Authorization': 'Token token="YOUR_API_KEY"'}
```

## Version 3 (optional)

Add next page / previous page buttons, and the `page` query parameter to move between pages.

## Check your work

Try the lab on your own first, then compare your approach:

- Student solutions: [student 1](student-solutions/student-1/), [student 2](student-solutions/student-2/). These were written by learners taking the course and are shown as they wrote them, so expect a few bugs. Spotting them is good practice.
