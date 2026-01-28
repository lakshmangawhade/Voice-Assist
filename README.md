# Dental AI Assistant - Krish

A voice-activated AI assistant for dental practices powered by Groq's Llama 3.1 8B Instant model and Deepgram for high-accuracy speech recognition.

## Features

- 🎤 **Wake Word Detection**: Say "krish" to activate voice commands
- 🎯 **Deepgram Voice Recognition**: High-accuracy speech-to-text using Deepgram
- 💬 **Text & Voice Chat**: Interact via text input or voice commands
- 🤖 **AI-Powered**: Powered by Groq's Llama 3.1 8B Instant model
- 🔊 **Text-to-Speech**: AI responses are spoken aloud
- ⏱️ **Continuous Listening**: Mic stays open for 5 seconds after AI response
- 🔒 **Secure**: API keys stored in environment variables

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure API Keys

1. Get your API keys:
   - **Groq API Key**: [Groq Console](https://console.groq.com/)
   - **Deepgram API Key**: [Deepgram Console](https://console.deepgram.com/)

2. Create a `.env` file in the root directory (same level as `package.json`)

3. Add your API keys:

```env
REACT_APP_GROQ_API_KEY=your_groq_api_key_here
REACT_APP_DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

**Important**: Replace the placeholder values with your actual API keys.

### 3. Start the Application

```bash
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000)

## Usage

### Wake Word Activation

1. **Say "krish"** - The microphone will automatically activate and start listening
2. Speak your command or question
3. The AI will respond both in text and voice
4. Mic stays open for 5 seconds for continuous conversation

### Manual Activation

- Click the microphone button to manually activate voice input
- Or type your message in the text input field

### Browser Requirements

- **Chrome/Edge**: Full support for wake word detection
- **Firefox/Safari**: May have limited speech recognition support
- **Microphone Access**: Grant microphone permissions when prompted

## Security Notes

- The `.env` file is already added to `.gitignore` to prevent committing your API key
- Never commit your API key to version control
- API calls are made directly from the browser (client-side)

---

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
