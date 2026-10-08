

# Vue Redo

Let's redo one of the following Python labs in [Vue](../../docs/15-vue.md)!

- [Rock, Paper, Scissors](../../../01-python/labs/07-rock-paper-scissors/README.md)
  - Have the user choose rock, paper, or scissors, and show the user who won.
- [Rot Cipher](../../../01-python/labs/15-rot13/README.md)
  - Simple version: the user could just input the word to encode.
  - Complex version: the user could also input the amount to rotate by.
- [Unit Converter](../../../01-python/labs/16-unit-converter/README.md)
  - Simple version: the user enters the distance and units and the app shows them the converted distance in meters
  - Complex version: the user also enters output units
- [Random Password Generator](../../../01-python/labs/06-random-password/README.md)
  - Simple version: the user just enters in the number of characters in the password
  - Complex version: the user enters the number of uppercase letters, lowercase letters, numbers, and special characters
- [Number to Phrase](../../../01-python/labs/17-number-to-phrase/README.md)
  - Have the user enter the number (5) and get back the corresponding word in english (five)


**Vue starter template**
```html
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title></title>
    </head>
    <body>
        <div id="app">
            {{ message }}
        </div>
        <script src="https://cdn.jsdelivr.net/npm/vue@2/dist/vue.js"></script>
        <script>
            var app = new Vue({
                el: '#app',
                data: {
                    message: 'Hello Vue!'
                },
                methods: {

                },
                created: function() {

                }
            })
        </script>
    </body>
</html>
```