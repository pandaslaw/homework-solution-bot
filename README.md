# Homework Solution LINE Bot

A LINE bot that provides step-by-step solutions for homework problems using GPT-4.

## Setup Instructions

1. Create a LINE Developer account:
   - Go to https://developers.line.biz/console/
   - Create a new provider
   - Create a new channel (Messaging API)
   - Get your Channel Secret and Channel Access Token

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your LINE credentials and OpenAI API key

4. Run the bot:
```bash
python main.py
```

5. Set up webhook URL in LINE Developer Console:
   - Use ngrok or similar tool to create a public URL, in terminal run command `ngrok http 5000`
   - At https://developers.line.biz/console/channel/2007297944/messaging-api set webhook URL to: `https://your-domain/callback`. Make sure URL ends with `/callback` 

## Usage

Simply send a text message with your homework problem to the bot, and it will respond with a detailed solution.

## Features

- Text-based problem solving
- Step-by-step solutions
- Supports various academic subjects

## Future Enhancements

- Photo input support
- Voice message support
- Japanese language support
