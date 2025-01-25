# YouTube Music Player for Alexa

This repository contains the source code for an Alexa skill that allows users to play YouTube music directly on Alexa-enabled devices. The skill supports syncing YouTube playlists and favorites, providing a seamless music experience.

---

## Features

- **Play YouTube Music:** Stream your favorite tracks directly from YouTube.
- **Playlist Integration:** Sync YouTube playlists and favorites with Alexa.
- **Player Options:** Shuffle, repeat, startover, songs by artists, albums.
- **Flask Server:** The skill leverages a Flask-based backend server for handling YouTube data.
- **NGROK Setup:** Easily set up the server using NGROK.
- **Android Termux Support:** Run the Flask server on Android devices using Termux.

---

## Repository Contents

1. **`server.py`**: Flask server code for handling backend operations.
2. **`templates/index.html`**: Web interface for setting up and managing the skill.
3. **`lambda_function.py`**: Python code for the Alexa Lambda function.
4. **Interaction Models**: Prebuilt interaction models for deploying the skill on Alexa.

---

## Setup Guide

### Prerequisites

- **Python 3.8 or higher**
- **Flask** (install using `pip install flask`)
- **NGROK** (download from [ngrok.com](https://ngrok.com/))
- **AWS Lambda Account**
- **Alexa Developer Account**

### Step 1: Clone the Repository

```bash
git clone https://github.com/itsjnz007/YouTube-Music-Alexa/
cd alexa-youtube-music
```

### Step 2: Set Up the Flask Server

Follow the NGROK setup instructions here: [NGROK Setup](https://ngrok.com/docs). For setting up NGROK on Termux, refer to this guide: [Termux NGROK Setup](https://github.com/Yisus7u7/termux-ngrok) (credits to Yisus7u7). Copy the provided NGROK URL.

### Step 3: Update the Alexa Skill

1. Navigate to the Alexa Developer Console and create a new skill.
2. Upload the provided interaction model.

### Step 4: Deploy the Lambda Function

Follow the AWS Lambda setup guide here: [AWS Lambda Setup](https://docs.aws.amazon.com/lambda/latest/dg/getting-started.html).

### Step 5: Test the Skill

- Use the Alexa simulator or your Alexa-enabled device to test the skill.
- Set the endpoint by saying, "Alexa ask DJ to set api url." Use the NGROK URL from the previous step.
- Instructions to set up playlists and API URL are provided below.

---

## Setting Up API URL and Playlists
Visit the api url's **`<api_url>/setup/`** page for encoders.
### Setting up API URL for Alexa Music

1. Set up an API URL using NGROK (free) and host the Flask app.
2. Copy the generated API URL and encode it using the field provided in the Flask app's main page.
3. Copy the encoded URL and use the Alexa app (mobile) to enter the command:
   ```
   Alexa, ask DJ to set api url <replace_with_encoded_url>.
   ```

### Adding YouTube Music/Playlists to Alexa Music

1. Create a public playlist on YouTube Music/YouTube.
2. Copy the playlist URL and encode it using the field provided in the Flask app's main page.
3. Copy the encoded URL and use the Alexa app (mobile) to enter the command:
   ```
   Alexa, ask DJ to add playlist <replace_with_encoded_url>.
   ```

---

## Example Phrases to Operate DJ

- "Alexa, ask DJ to play [song name]."
- "Alexa, ask DJ to set API URL."
- "Alexa, ask DJ to play my [playlist name] / Alexa, ask DJ to play playlist [playlist name]"
- "Alexa, ask DJ to play songs by [artist name]"
- "Alexa, ask DJ to play album [album name]."
- "Alexa, next song", "...pause ...play ...shuffle on/off ...repeat on/off ...start over ..."

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## Contributions

Contributions are welcome! Feel free to fork this repository and submit pull requests.

---

## Acknowledgments

Special thanks to the open-source community for providing tools and inspiration for this project.

