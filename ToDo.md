You grabbed the OAuth 2.0 Client ID and Secret, but the tweepy library in the growth engine script actually uses the OAuth 1.0a Keys and the Bearer Token.

Looking at your second screenshot, you are in exactly the right place. Here is what you need to do:

Under App-Only Authentication, click "Generate" for the Bearer Token.
Under OAuth 1.0 Keys, click "Regenerate" for the Consumer Key (which gives you the API Key and API Secret) and click "Generate" for the Access Token (which gives you the Access Token and Access Secret).