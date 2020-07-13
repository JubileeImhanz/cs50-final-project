# cs50-final-project
## FTrade - Forex trading app

## Description
FTrade is a web app for foreign exchange trading. You can purchase, sell and get live exchange rates. In this current version, the OpenRates API was used. The OpenRates API delivers accurate and up-to-date exchange rate data for 32 world currencies in JSON format. All currency data is sourced from the European Central Bank. The downside of this API is the 32 currency limitation and also exchange rates are updated only once daily but it is still an excellent choice for developing and testing as it has limitless API calls. The default currency is US dollars and you can deposit money into your financial portfolio. All transactions are recorded in a database and users can view their transaction history.

## Requirements
This application was developed using Flask and to run this application, you need to have python3 installed. You also need to install the following libraries using pip or conda.

1. cs50 (contains SQL library used for database query)
2. flask (library for building web apps depends on jinja and werkzeug)
3. werkzeug (comprehensive web app library)
4. requests (for making HTTP requests)
5. urllib.parse (library for parsing URL)
6. re (special library for string or expression mathcing)

If running this app on the Cloud9 IDE or the CS50 specific IDE. However, you do not have to install these libraries as they are already installed and should work properly. 

## Running the app
1. Open your terminal window and change the directory to that where the files are stored

2. Next you have to set the FLASK_APP environment variable.

Unix Bash (Linux, Mac, etc.):

```export FLASK_APP=application```

For Windows

```set FLASK_APP=application```

For Powershell

```$env:FLASK_APP = "application"```

3. Now the development server can be started tou run the application using

```flask run```

The application will be hosted on the link displayed and you can paste the link in your browser to use the app.

## Tech used
- Python
- SQLite3
- HTML
- CSS
- JavaScript
